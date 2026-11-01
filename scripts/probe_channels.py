#!/usr/bin/env python3
"""Normalize capability probes and detect local export tools.

MCP calls must be performed by the Agent in its tool environment. Supply their
observed results through --inventory; this script never claims to call MCPs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any


CAPABILITIES = (
    "norm.exact_article",
    "norm.validity",
    "norm.history",
    "case.search",
    "case.authority",
    "case.fulltext",
    "case.subsequent",
    "scholarship.search",
    "scholarship.fulltext",
    "journal.metadata",
    "journal.recent_articles",
    "journal.submission_rules",
    "foreign.official_text",
    "foreign.case",
    "foreign.scholarship",
    "translation.assist",
    "local.corpus",
    "local.zotero",
    "local.obsidian",
    "local.notebook",
    "local.terms",
    "export.docx",
    "export.pdf_render",
    "format.profile",
    "format.journal_spec",
)
ALLOWED_STATUSES = {"available", "partial", "auth_required", "missing", "unknown"}

GUIDANCE = {
    "norm.exact_article": "未配置时用官方数据库网页逐字核验，或接入规范类 MCP。",
    "norm.validity": "必须能返回效力与施行/修订信息；否则规范不得标 primary_verified。",
    "norm.history": "用官方历次修正公告与草案页补齐；无法补齐时标注版本缺口。",
    "case.search": "用案例类 MCP 或官网检索；仅网页搜索时只作线索。",
    "case.authority": "核对人民法院案例库、指导性案例与公报案例层级；无法核层级时不得宣称。",
    "case.fulltext": "须读取裁判原文；仅摘要时不得归纳裁判理由。",
    "case.subsequent": "检查再审、改判、停参与后案处理；未核时明示。",
    "scholarship.search": "用 CNKI/开放学术源发现题录，再回期刊官网或 DOI 核验。",
    "scholarship.fulltext": "请用户提供合法全文或使用 OA 版本；不得用摘要冒充全文。",
    "journal.metadata": "请用户指定目标期刊；未定时用通行引注规范基线并标注待定。",
    "journal.recent_articles": "浏览目标期刊官网近几期目录，记录 3–5 篇代表篇目。",
    "journal.submission_rules": "打开投稿须知与 AI 政策页，记录字数、格式、匿名与披露要求。",
    "foreign.official_text": "按法域接官方源或开源通道；跑一条现行条文用例。",
    "foreign.case": "接判例类通道；记录法院层级与意见类型。",
    "foreign.scholarship": "先用开放源发现，再回原文或出版商页核验；无法取得原文时标注转引。",
    "translation.assist": "无专用工具时按翻译协议执行，并登记术语表与校验报告。",
    "local.corpus": "请用户授权只读目录后运行 scan_corpus.py。",
    "local.zotero": "安装 Zotero 并启用本机通信；提供库路径，只读扫描。",
    "local.obsidian": "让用户选择 vault；只索引 Markdown，跳过 .obsidian/。",
    "local.notebook": "在会话中连接知识库类 MCP，添加项目 Source。",
    "local.terms": "导入项目或个人术语表（CSV/JSON），登记来源与置信度。",
    "export.docx": "安装 Pandoc 或使用支持的 DOCX 导出路径。",
    "export.pdf_render": "仅 PDF 交付或需要转图目检时必需；缺失时可在 Word/Pages 中逐页目检。",
    "format.profile": "选择默认/通用预设或自定义字体字号，生成并校验 format-profile.json。",
    "format.journal_spec": "上传目标期刊投稿须知或样文；无法读取文本时请用户粘贴关键条目。",
}


def empty_result() -> dict[str, Any]:
    return {
        "status": "unknown",
        "source": "none",
        "tool": "",
        "probe_case": "",
        "probe_assert": "",
        "probe_ok": False,
        "auth_required": False,
        "guidance": "",
        "impact": "",
    }


def catalog_date(skill_root: Path) -> str:
    path = skill_root / "references" / "channel-catalog.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r"目录最近校核日：`(\d{4}-\d{2}-\d{2})`", text)
    return match.group(1) if match else ""


def load_inventory(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = json.loads(path.expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("inventory must be a JSON object")
    capabilities = data.get("capabilities", data)
    if not isinstance(capabilities, dict):
        raise ValueError("inventory capabilities must be a JSON object")
    return capabilities


def normalize_entry(capability: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"inventory entry must be an object: {capability}")
    result = empty_result()
    result.update({key: value[key] for key in result if key in value})
    status = str(result["status"]).strip()
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"invalid status for {capability}: {status}")
    result["status"] = status
    result["probe_ok"] = bool(result["probe_ok"])
    result["auth_required"] = bool(result["auth_required"])
    if status == "available" and not result["probe_ok"]:
        result["status"] = "partial"
        result["impact"] = (
            str(result.get("impact", "")) + "；工具存在但最小真实用例未通过"
        ).strip("；")
    return result


def find_zotero_db() -> Path | None:
    home = Path.home()
    candidates = [
        home / "Zotero" / "zotero.sqlite",
        home / ".zotero" / "zotero.sqlite",
        home / ".zotero" / "zotero" / "zotero.sqlite",
        home / "Library" / "Application Support" / "Zotero" / "zotero.sqlite",
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "Zotero" / "Zotero" / "zotero.sqlite")
    return next((p for p in candidates if p.is_file()), None)


def zotero_item_count(db: Path) -> int | None:
    """Read-only probe: count items without modifying the library."""
    try:
        import sqlite3

        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        try:
            row = conn.execute("select count(*) from items").fetchone()
            return int(row[0]) if row else None
        finally:
            conn.close()
    except Exception:
        return None


def find_obsidian_vaults() -> list[Path]:
    home = Path.home()
    configs = [
        home / "Library" / "Application Support" / "obsidian" / "obsidian.json",
        home / ".config" / "obsidian" / "obsidian.json",
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        configs.append(Path(appdata) / "obsidian" / "obsidian.json")
    for cfg in configs:
        if not cfg.is_file():
            continue
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        vaults = data.get("vaults", {})
        if not isinstance(vaults, dict):
            continue
        paths = []
        for entry in vaults.values():
            if isinstance(entry, dict) and entry.get("path"):
                p = Path(str(entry["path"])).expanduser()
                if p.is_dir():
                    paths.append(p)
        if paths:
            return paths
    return []


def count_markdown(vault: Path, limit: int = 500) -> int:
    count = 0
    for p in vault.rglob("*.md"):
        if ".obsidian" in p.parts:
            continue
        if p.is_file():
            count += 1
            if count >= limit:
                break
    return count


def detect_local(
    capabilities: dict[str, dict[str, Any]],
    corpus_roots: list[Path] | None = None,
    project: Path | None = None,
    obsidian_vaults: list[Path] | None = None,
) -> None:
    pandoc = shutil.which("pandoc")
    if pandoc:
        capabilities["export.docx"] = {
            "status": "available",
            "tool": pandoc,
            "probe_case": "pandoc --version",
            "probe_assert": "可执行文件存在；仍需用样张验证原生脚注与样式",
            "probe_ok": True,
            "auth_required": False,
            "impact": "",
        }
    elif capabilities["export.docx"]["status"] == "unknown":
        capabilities["export.docx"].update(
            {"status": "missing", "impact": "不得交付声称已完成最终版式的 DOCX"}
        )

    renderer = shutil.which("soffice") or shutil.which("libreoffice")
    if renderer:
        capabilities["export.pdf_render"] = {
            "status": "available",
            "tool": renderer,
            "probe_case": "headless office renderer found",
            "probe_assert": "仍需实际转换样张并逐页检查",
            "probe_ok": True,
            "auth_required": False,
            "impact": "",
        }
    elif capabilities["export.pdf_render"]["status"] == "unknown":
        capabilities["export.pdf_render"].update(
            {"status": "missing", "impact": "layout_rendered 不得签署，最高 REVIEW_REQUIRED"}
        )

    if corpus_roots:
        missing = [str(path) for path in corpus_roots if not path.expanduser().exists()]
        if missing:
            capabilities["local.corpus"].update(
                {
                    "status": "partial",
                    "tool": "scripts/scan_corpus.py",
                    "probe_case": f"{len(corpus_roots)} 个用户授权根目录",
                    "probe_assert": "存在无法访问的路径",
                    "probe_ok": False,
                    "impact": "先修复路径或读取授权；文件存在不等于已读",
                }
            )
        else:
            capabilities["local.corpus"] = {
                "status": "available",
                "tool": "scripts/scan_corpus.py",
                "probe_case": f"{len(corpus_roots)} 个用户授权根目录",
                "probe_assert": "路径存在且可建立候选资料索引",
                "probe_ok": True,
                "auth_required": False,
                "impact": "索引条目仍须实际阅读后才能进入可引用状态",
            }

    if project is not None and capabilities["format.profile"]["status"] == "unknown":
        profile_path = project / "format-profile.json"
        if profile_path.is_file():
            try:
                from format_profile import load_profile, validate_profile

                data = load_profile(profile_path)
                errors = validate_profile(data)
            except Exception as exc:  # noqa: BLE001 - report parse/validation failure as partial
                capabilities["format.profile"] = {
                    "status": "partial",
                    "source": "auto_detected",
                    "tool": str(profile_path),
                    "probe_case": "读取 format-profile.json",
                    "probe_assert": str(exc),
                    "probe_ok": False,
                    "auth_required": False,
                    "guidance": "修复 JSON 后运行 format_profile.py validate",
                    "impact": "无法确认版式，按默认预设导出并标注未确认",
                }
            else:
                capabilities["format.profile"] = {
                    "status": "available" if not errors else "partial",
                    "source": "auto_detected",
                    "tool": str(profile_path),
                    "probe_case": f"校验通过，名称={data.get('name','')}" if not errors else "；".join(errors[:3]),
                    "probe_assert": "格式配置字段完整且数值合法",
                    "probe_ok": not errors,
                    "auth_required": False,
                    "guidance": "向用户回显摘要并确认后再导出",
                    "impact": "" if not errors else "版式配置有误，不得声称按用户要求导出",
                }

    if capabilities["local.zotero"]["status"] == "unknown":
        db = find_zotero_db()
        if db:
            n = zotero_item_count(db)
            if n is not None:
                capabilities["local.zotero"] = {
                    "status": "available",
                    "source": "auto_detected",
                    "tool": str(db),
                    "probe_case": f"只读统计 items = {n}",
                    "probe_assert": "数据库可读且条目数>0；未修改库文件",
                    "probe_ok": n > 0,
                    "auth_required": False,
                    "guidance": "已发现 Zotero 库；确认只读扫描范围与附件目录",
                    "impact": "仅证明库藏可检索，不证明全文已读",
                }
                if n == 0:
                    capabilities["local.zotero"]["status"] = "partial"
            else:
                capabilities["local.zotero"] = {
                    "status": "partial",
                    "source": "auto_detected",
                    "tool": str(db),
                    "probe_case": "数据库存在但只读连接失败",
                    "probe_assert": "可能被占用或版本不兼容",
                    "probe_ok": False,
                    "auth_required": False,
                    "guidance": "关闭 Zotero 后重试，或改为导出 BibTeX/RIS",
                    "impact": "无法读取库内条目",
                }

    vaults = obsidian_vaults if obsidian_vaults is not None else find_obsidian_vaults()
    if capabilities["local.obsidian"]["status"] == "unknown" and vaults:
        scanned = [(v, count_markdown(v)) for v in vaults]
        readable = [(v, c) for v, c in scanned if c > 0]
        capabilities["local.obsidian"] = {
            "status": "available" if readable else "partial",
            "source": "auto_detected",
            "tool": "; ".join(str(v) for v, _ in readable) or "; ".join(str(v) for v, _ in scanned),
            "probe_case": "只读统计 Markdown 笔记数：" + ", ".join(f"{v.name}={c}" for v, c in scanned),
            "probe_assert": "至少一个库存在可读 Markdown；跳过 .obsidian/",
            "probe_ok": bool(readable),
            "auth_required": False,
            "guidance": "请用户确认只索引哪些库、排除哪些目录；不写回笔记",
            "impact": "仅证明笔记可检索，不证明内容已被阅读",
        }

    if project is not None and capabilities["local.terms"]["status"] == "unknown":
        terms_dir = project / "terms"
        if terms_dir.is_dir():
            files = [
                p
                for p in terms_dir.iterdir()
                if p.is_file() and p.suffix.lower() in {".csv", ".json", ".jsonl", ".tsv", ".yaml", ".yml"}
            ]
            if files:
                capabilities["local.terms"] = {
                    "status": "available",
                    "source": "auto_detected",
                    "tool": "terms/",
                    "probe_case": f"{len(files)} 个术语表文件",
                    "probe_assert": "文件可解析且含术语字段；仍需人工确认译名",
                    "probe_ok": True,
                    "auth_required": False,
                    "guidance": "校对术语来源与置信度后再用于翻译",
                    "impact": "未确认的术语不得直接作为标准译法",
                }


def probe(
    project: Path,
    inventory_path: Path | None = None,
    corpus_roots: list[Path] | None = None,
    obsidian_vaults: list[Path] | None = None,
) -> dict[str, Any]:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise FileNotFoundError(f"project directory not found: {project}")
    inventory = load_inventory(inventory_path)
    capabilities = {name: empty_result() for name in CAPABILITIES}
    for name, value in inventory.items():
        if name not in capabilities:
            continue
        entry = normalize_entry(name, value)
        if not entry.get("source") or entry["source"] == "none":
            entry["source"] = "agent_probe"
        capabilities[name] = entry
    detect_local(capabilities, corpus_roots, project, obsidian_vaults)
    for name, entry in capabilities.items():
        if not entry.get("guidance"):
            entry["guidance"] = GUIDANCE.get(name, "")

    skill_root = Path(__file__).resolve().parent.parent
    verified = catalog_date(skill_root)
    stale = True
    if verified:
        stale = (dt.date.today() - dt.date.fromisoformat(verified)).days > 90
    return {
        "schema_version": 1,
        "checked_at": dt.date.today().isoformat(),
        "catalog_last_verified": verified,
        "catalog_stale": stale,
        "capabilities": capabilities,
        "messages": [
            "MCP/API capability is available only after an Agent-run live probe passes.",
            "Credentials must remain in the client credential store or environment, never this file.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize channel capability probes.")
    parser.add_argument("project", help="Commentary project directory")
    parser.add_argument("--inventory", type=Path, help="JSON observations produced by Agent live probes")
    parser.add_argument("--corpus-root", action="append", type=Path, help="Authorized local corpus root; repeatable")
    parser.add_argument("--obsidian-vault", action="append", type=Path, help="Obsidian vault path; repeatable (auto-detected when omitted)")
    parser.add_argument("--output", type=Path, help="Output path; defaults to project/channel-probe.json")
    parser.add_argument("--json", action="store_true", help="Also print JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = probe(Path(args.project), args.inventory, args.corpus_root, args.obsidian_vault)
        output = (args.output or (Path(args.project) / "channel-probe.json")).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        caps = report["capabilities"]
        available = [n for n, i in caps.items() if i["status"] == "available"]
        need = [(n, i) for n, i in caps.items() if i["status"] in {"partial", "auth_required", "missing"}]
        unknown = [n for n, i in caps.items() if i["status"] == "unknown"]
        print(f"Probe written to {output}")
        print("Available: " + (", ".join(available) if available else "none"))
        if need:
            print("\nNeeds attention:")
            for n, i in need:
                print(f"  - {n} [{i['status']}]: {i.get('guidance', '')}")
        if unknown:
            print("\nUnknown (no auto-detection): " + ", ".join(unknown))
        if report["catalog_stale"]:
            print("Warning: channel catalog is older than 90 days; verify official sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
