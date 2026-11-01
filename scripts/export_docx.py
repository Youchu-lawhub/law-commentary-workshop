#!/usr/bin/env python3
"""Export a Markdown manuscript to DOCX through a stable Pandoc contract."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from apply_format_profile import apply_profile
from format_profile import validate_profile
from render_check import render_pdf, resolve_soffice, validate_docx

SKILL_ROOT = Path(__file__).resolve().parent.parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Markdown to a validated journal-style DOCX.")
    parser.add_argument("input", type=Path, help="Markdown manuscript")
    parser.add_argument("output", type=Path, help="Destination .docx")
    parser.add_argument(
        "--template",
        type=Path,
        help="Pandoc reference DOCX; overrides the profile's reference_docx",
    )
    parser.add_argument(
        "--format-profile",
        type=Path,
        help="JSON format profile (fonts, sizes, spacing, margins); applied after conversion",
    )
    parser.add_argument("--pandoc", help="Explicit Pandoc executable")
    parser.add_argument("--purify", action="store_true",
                        help="移除脚注中的证据状态标记（投稿稿）；默认转为灰色斜体（工作稿）")
    parser.add_argument("--anonymous", action="store_true", help="Check blank author metadata")
    parser.add_argument("--render", action="store_true", help="Also render PDF for human review")
    parser.add_argument("--render-dir", type=Path)
    parser.add_argument("--soffice", help="Explicit LibreOffice soffice executable")
    parser.add_argument("--metadata-file", type=Path, help="Optional Pandoc YAML metadata file")
    return parser



EVIDENCE_TAG_PATTERN = re.compile(
    r"\[(?:原文核实|要点核实|题录核实|摘要参考|需用户核实|原文核实[^\]]{0,40}|摘要参考[^\]]{0,40}|要点核实[^\]]{0,40}|题录核实[^\]]{0,40}|需用户核实[^\]]{0,40})\]"
)
GRAY_ITALIC_RPR = '<w:rPr><w:i/><w:iCs/><w:color w:val="7F7F7F"/></w:rPr>'


def restyle_footnote_tags(docx_path: Path, purify: bool = False) -> int:
    """把脚注内的 [原文核实] 等证据状态标记转为灰色斜体 run（purify=True 时移除）。

    范本体例：此类标记属工作层信息，不入印刷体；工作稿保留为灰色斜体以存可溯性。
    """
    import zipfile

    tmp = docx_path.with_suffix(".restyle-tmp.docx")
    count = 0
    with zipfile.ZipFile(docx_path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/footnotes.xml":
                xml = data.decode("utf-8")

                def fix_run(match: "re.Match[str]") -> str:
                    nonlocal count
                    run = match.group(0)
                    tm = re.search(r"<w:t[^>]*>(.*?)</w:t>", run, re.S)
                    if not tm or not EVIDENCE_TAG_PATTERN.search(tm.group(1)):
                        return run
                    text = tm.group(1)
                    rpr = re.search(r"<w:rPr>.*?</w:rPr>", run, re.S)
                    rpr_xml = rpr.group(0) if rpr else ""
                    parts: list[str] = []
                    last = 0
                    for tag in EVIDENCE_TAG_PATTERN.finditer(text):
                        pre = text[last:tag.start()]
                        if pre:
                            parts.append(f'<w:r>{rpr_xml}<w:t xml:space="preserve">{pre}</w:t></w:r>')
                        if purify:
                            count += 1
                        else:
                            parts.append(
                                f'<w:r>{GRAY_ITALIC_RPR}<w:t xml:space="preserve">{tag.group(0)}</w:t></w:r>'
                            )
                            count += 1
                        last = tag.end()
                    tail = text[last:]
                    if tail:
                        parts.append(f'<w:r>{rpr_xml}<w:t xml:space="preserve">{tail}</w:t></w:r>')
                    return "".join(parts)

                xml = re.sub(r"<w:r>(?:(?!</?w:r>).)*</w:r>", fix_run, xml, flags=re.S)
                data = xml.encode("utf-8")
            zout.writestr(item, data)
    tmp.replace(docx_path)
    return count


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    profile = None
    if args.format_profile:
        profile_path = args.format_profile.expanduser().resolve()
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read format profile: {exc}", file=sys.stderr)
            return 2
        profile_errors = validate_profile(profile)
        if profile_errors:
            for item in profile_errors:
                print(f"ERROR: {item}", file=sys.stderr)
            return 2
    if args.template:
        template = args.template.expanduser().resolve()
    elif profile and profile.get("reference_docx"):
        template = (SKILL_ROOT / str(profile["reference_docx"])).expanduser().resolve()
    else:
        template = SKILL_ROOT / "assets" / "templates" / "journal-cn.docx"
    if not input_path.is_file():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 2
    if output_path.suffix.lower() != ".docx":
        print("error: output must end in .docx", file=sys.stderr)
        return 2
    if not template.is_file():
        print(f"error: reference DOCX not found: {template}", file=sys.stderr)
        return 2

    pandoc = args.pandoc or shutil.which("pandoc")
    if not pandoc:
        print("EXPORT_UNAVAILABLE: 未找到 Pandoc；不要用脆弱的手工 DOCX 伪装最终稿", file=sys.stderr)
        return 3
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(pandoc),
        str(input_path),
        "--from=markdown+footnotes+smart",
        "--to=docx",
        f"--reference-doc={template}",
        "--standalone",
        f"--output={output_path}",
    ]
    if args.metadata_file:
        metadata = args.metadata_file.expanduser().resolve()
        if not metadata.is_file():
            print(f"error: metadata file not found: {metadata}", file=sys.stderr)
            return 2
        cmd.append(f"--metadata-file={metadata}")
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except OSError as exc:
        print(f"EXPORT_FAILED: {exc}", file=sys.stderr)
        return 2
    if proc.returncode != 0 or not output_path.is_file():
        detail = "\n".join(part for part in (proc.stdout.strip(), proc.stderr.strip()) if part)
        print(f"EXPORT_FAILED: {detail or proc.returncode}", file=sys.stderr)
        return 2

    if profile:
        try:
            apply_profile(profile, output_path)
        except Exception as exc:  # noqa: BLE001 - surface a stable failure message
            print(f"FORMAT_APPLY_FAILED: {exc}", file=sys.stderr)
            return 2
        print(f"FORMAT_APPLIED: {args.format_profile}")

    # 发表体例：脚注内的证据状态标记转灰色斜体（工作稿）或移除（--purify 投稿稿）
    try:
        restyled = restyle_footnote_tags(output_path, purify=args.purify)
        if restyled:
            print(f"TAG_RESTYLED: {restyled} 处证据标记已{'移除' if args.purify else '转为灰色斜体'}")
    except Exception as exc:  # noqa: BLE001
        print(f"TAG_RESTYLE_FAILED: {exc}", file=sys.stderr)
        return 2

    errors = validate_docx(output_path, anonymous=args.anonymous)
    if errors:
        for item in errors:
            print(f"ERROR: {item}", file=sys.stderr)
        return 2
    print(f"DOCX_OK: {output_path}")

    if args.render:
        soffice = resolve_soffice(args.soffice)
        if soffice is None:
            print("RENDER_UNAVAILABLE: 未找到 LibreOffice；不得签署 layout_rendered", file=sys.stderr)
            return 3
        render_dir = (args.render_dir or output_path.parent / "rendered").expanduser().resolve()
        pdf, log = render_pdf(output_path, render_dir, soffice)
        if pdf is None:
            print(f"RENDER_FAILED: {log}", file=sys.stderr)
            return 2
        print(f"RENDER_CREATED: {pdf}")
        print("HUMAN_REVIEW_REQUIRED: 必须逐页目检后才能签署 layout_rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
