#!/usr/bin/env python3
"""把项目内的交付文件整理为统一命名的交付包。

命名规则：`{slug}-{type}.{ext}`，slug 只含小写字母、数字与连字符。
默认交付 Word；PDF、支撑材料仅在存在或显式要求时纳入。

用法：
  python3 package_delivery.py --project <项目目录> --slug art1165
  python3 package_delivery.py --project <项目目录> --slug art1165 --include-support
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
import tempfile
import uuid
from audit_commentary import audit_project
from pathlib import Path

SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,59}$")

# source -> (type suffix, category)
DELIVERABLES = {
    "07-paper.docx": ("commentary", "core"),
    "07-paper.md": ("commentary", "core"),
    "07-paper.pdf": ("commentary", "optional"),
    "format-profile.json": ("format-profile", "core"),
    "09-quality-report.md": ("quality-report", "core"),
    "quality-signoff.json": ("quality-signoff", "core"),
    "ai-usage-declaration.md": ("ai-usage", "ethics"),
    "ethics-checklist.md": ("ethics-checklist", "ethics"),
    "03-source-ledger.jsonl": ("source-ledger", "support"),
    "04-case-matrix.csv": ("case-matrix", "support"),
    "08-citation-audit.csv": ("citation-audit", "support"),
    "11-comparative-memo.md": ("comparative-memo", "support"),
    "10-decision-log.md": ("decision-log", "support"),
    "channel-probe.json": ("channel-probe", "support"),
    "translation-manifest.json": ("translation-manifest", "support"),
    "terminology-ledger.jsonl": ("terminology-ledger", "support"),
    "translation-quality-report.md": ("translation-quality-report", "support"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def derive_slug(project: Path) -> str | None:
    """从 research-profile.yaml 取条文号生成 slug。

    只认单个“第N条”的阿拉伯数字；含多款、多条或中文数字时不猜测，交由 --slug 指定。
    """
    profile = project / "research-profile.yaml"
    if not profile.is_file():
        return None
    text = profile.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^\s*article\s*:\s*[\"']?([^\"'\n]+)", text, re.MULTILINE)
    if not match:
        return None
    articles = re.findall(r"第\s*([0-9]+)\s*条", match.group(1))
    if len(articles) != 1:
        return None
    return "art" + articles[0]


# 绝对路径与本机路径前缀：POSIX “/x”、Windows “C:\x”/“C:/x”、UNC “\\server\share”。
# 只匹配单个前导分隔符（旧写法要求两个分隔符，导致 /Users/… 与 C:\Users\… 都不脱敏）。
ABSOLUTE_PATH = re.compile(r"^(?:[A-Za-z]:)?[\\/].*")


def redact_local_paths(value):
    """把绝对路径替换为末级名称并标记已脱敏，供对外交付使用。

    交付包会随稿件发给期刊或合作方，`channel-probe.json` 与清单里的本机绝对路径
    会暴露使用者身份与工作目录，与匿名投稿要求冲突。
    """
    if isinstance(value, dict):
        return {key: redact_local_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_local_paths(item) for item in value]
    if isinstance(value, str) and ABSOLUTE_PATH.match(value):
        parts = [part for part in value.replace("\\", "/").split("/") if part]
        tail = parts[-1] if parts else ""
        return f"{tail}[已脱敏]" if tail else "[已脱敏]"
    return value


def redacted_probe(source: Path) -> bytes:
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"channel-probe.json 无法解析，未脱敏故不打包：{exc}")
    return (json.dumps(redact_local_paths(data), ensure_ascii=False, indent=2) + "\n").encode("utf-8")



SYSTEM_ALIAS_LINKS = {"/tmp", "/var", "/etc"}


def _system_alias_realpath(p: Path) -> bool:
    """判断路径是否为操作系统创建的系统级别名链接本体。

    仅豁免 /tmp、/var、/etc 这三个根级符号链接本身（macOS 布局，
    指向 /private/ 同名目录）；深层符号链接不在豁免之列。
    """
    ap = str(Path(p).absolute()).rstrip("/") or "/"
    if ap not in SYSTEM_ALIAS_LINKS:
        return False
    try:
        real = str(p.resolve(strict=True)).rstrip("/") or "/"
    except OSError:
        return False
    return real == f"/private{ap}"


def _symlink_escape(p: Path) -> bool:
    """路径任一组件为符号链接且非系统级别名时，视为交付边界逃逸。"""
    for comp in [p, *p.parents]:
        try:
            if comp.is_symlink() and not _system_alias_realpath(comp):
                return True
        except OSError:
            continue
    return False


def package(project: Path, slug: str, out_dir: Path, include_support: bool, force: bool, draft: bool = False) -> dict:
    """Build in a private staging directory and publish only after every check passes.

    This is intentionally conservative: existing output is never silently replaced,
    even with --force. The flag only permits overwriting an existing *directory*
    following a successful stage, with rollback attempted if final rename fails.
    """
    project = project.expanduser().resolve()
    requested_out = out_dir.expanduser()
    if not project.is_dir() or project.is_symlink():
        raise ValueError("project not found or unsafe project path")
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError("slug 必须为 3–60 位小写字母、数字或连字符")
    # Inspect the submitted path before resolving it; otherwise a symlink parent
    # could be silently followed and bypass the intended destination boundary.
    # 系统级别名（如 macOS 的 /var、/tmp）予以豁免，避免跨平台误报。
    if _symlink_escape(requested_out):
        raise ValueError("交付路径不能包含符号链接")
    out_dir = requested_out.resolve()
    if out_dir == project or out_dir == project.parent or out_dir.is_relative_to(project) and out_dir != project / 'delivery':
        raise ValueError("交付目录必须独立，或使用默认 project/delivery；不允许其他项目内部目录")
    if out_dir.exists() and (not out_dir.is_dir() or (any(out_dir.iterdir()) and not force)):
        raise ValueError("目标交付目录非空或不是目录；请更换路径或显式使用 --force")
    if out_dir.is_symlink():
        raise ValueError("交付路径包含符号链接")
    audit = audit_project(project)
    if not draft and audit['verdict'] != 'READY_FOR_SUBMISSION':
        raise ValueError("正式交付被质量闸门阻止：" + audit['verdict'] + "；仅可显式 --draft 输出工作稿")
    # Reject all unsafe sources up-front. A failed package leaves no partial delivery.
    sources=[]; skipped=[]
    for source_name, (suffix, category) in DELIVERABLES.items():
        if category == 'support' and not include_support:
            continue
        source = project / source_name
        if source.is_symlink():
            raise ValueError(f"拒绝符号链接交付件: {source_name}")
        if not source.exists():
            skipped.append({'source':source_name,'reason':'missing','category':category})
            continue
        if not source.is_file() or not source.resolve().is_relative_to(project):
            raise ValueError(f"拒绝项目外或非普通文件: {source_name}")
        sources.append((source_name, source, suffix, category))
    if not draft and not {'07-paper.md','07-paper.docx'}.issubset({r[0] for r in sources}):
        raise ValueError('正式交付必须同时具有 Markdown 原稿和 DOCX 成稿')
    paper = project / '07-paper.md'
    if paper.is_file():
        body = paper.read_text(encoding='utf-8', errors='ignore')
        if re.search(r"\{\{[^{}\n]+\}\}", body):
            raise ValueError('07-paper.md 仍含未填充的模板占位符；请先写入正文再打包（含 --draft）')
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.delivery-stage-',dir=out_dir.parent))
    copied=[]
    try:
        for source_name, source, suffix, category in sources:
            target=staging / f'{slug}-{suffix}{source.suffix}'
            payload = redacted_probe(source) if source_name == 'channel-probe.json' else None
            # Exclusive copy guards against accidental duplicate output names.
            with source.open('rb') as input_file, target.open('xb') as output_file:
                if payload is None:
                    shutil.copyfileobj(input_file,output_file)
                    expected=sha256(source)
                else:
                    output_file.write(payload)
                    expected=hashlib.sha256(payload).hexdigest()
            if sha256(target) != expected:
                raise ValueError(f'源文件在复制期间发生变更: {source_name}')
            copied.append({'source':source_name,'target':target.name,'category':category,'bytes':target.stat().st_size,'sha256':sha256(target)})
        manifest={
            'schema_version':3,
            'delivery_mode':'draft_not_for_submission' if draft else 'submission_candidate',
            'quality_verdict_at_packaging':audit['verdict'],
            'quality_errors':len(audit['errors']),
            'quality_warnings':len(audit['warnings']),
            'paper_source_sha256':sha256(project/'07-paper.md') if (project/'07-paper.md').is_file() else None,
            'generated_at':dt.datetime.now().astimezone().isoformat(timespec='seconds'),
            'project': project.name, 'project_path_redacted': True,
            'slug':slug,'include_support':include_support,
            'copied':copied,'skipped':skipped,'naming':'{slug}-{type}.{ext}',
            'disclaimer':'Technical gate only: not independent confirmation of scholarly merit or publication eligibility.'
        }
        if draft:
            (staging/'DRAFT-NOT-FOR-SUBMISSION.txt').write_text('未完成学术和技术放行，不得作为已核验投稿终稿。\n',encoding='utf-8')
        (staging/f'{slug}-delivery-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        # Rename is atomic when staging and target share a filesystem.
        backup=None
        if out_dir.exists():
            backup=out_dir.parent / ('.delivery-backup-'+uuid.uuid4().hex)
            out_dir.rename(backup)
        try:
            staging.rename(out_dir)
        except Exception:
            if backup is not None and backup.exists() and not out_dir.exists():
                backup.rename(out_dir)
            raise
        if backup is not None:
            shutil.rmtree(backup)
        manifest['manifest']=str(out_dir/f'{slug}-delivery-manifest.json')
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Package deliverables with standardized names.")
    p.add_argument("--project", required=True, type=Path)
    p.add_argument("--slug", help="Lowercase slug, e.g. art1165; derived from research-profile.yaml when omitted")
    p.add_argument("--out", type=Path, help="Output directory; defaults to <project>/delivery")
    p.add_argument("--include-support", action="store_true", help="Also copy ledgers and working records")
    p.add_argument("--force", action="store_true", help="Replace an existing delivery directory (it is renamed to a backup first, never overwritten file-by-file)")
    p.add_argument("--json", action="store_true", help="Print the manifest as JSON")
    p.add_argument("--draft", action="store_true", help="Explicitly export an unverified working draft")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = args.project.expanduser().resolve()
    slug = args.slug or derive_slug(project)
    if not slug:
        print("error: 无法从 research-profile.yaml 推导 slug；请用 --slug 指定，如 art1165", file=sys.stderr)
        return 2
    out_dir = args.out or (project / "delivery")
    try:
        manifest = package(project, slug, out_dir, args.include_support, args.force, args.draft)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"DELIVERY_PACKAGED: {out_dir}")
        for item in manifest["copied"]:
            print(f"  {item['source']} -> {item['target']}")
        for item in manifest["skipped"]:
            print(f"  SKIP {item['source']}: {item['reason']}")
        print(f"  manifest -> {Path(manifest['manifest']).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
