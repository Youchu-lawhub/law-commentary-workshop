#!/usr/bin/env python3
"""格式配置文件的生成、校验与摘要。

用法：
  python3 format_profile.py list
  python3 format_profile.py init --preset journal-cn-default --output format-profile.json
  python3 format_profile.py validate format-profile.json
  python3 format_profile.py show format-profile.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRESET_DIR = ROOT / "assets" / "format-profiles"
ALIGNMENTS = {"left", "center", "right", "justify"}


def load_profile(path: Path) -> dict:
    data = json.loads(path.expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("profile must be a JSON object")
    return data


def _num(value, label: str, low: float, high: float, errors: list[str]) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        errors.append(f"{label} 必须是数字")
    elif not (low <= float(value) <= high):
        errors.append(f"{label} 应在 {low}–{high} 之间，当前 {value}")


def validate_profile(profile: dict) -> list[str]:
    errors: list[str] = []
    if profile.get("schema_version") != 1:
        errors.append("schema_version 必须为 1")
    if not str(profile.get("name", "")).strip():
        errors.append("name 不能为空")

    page = profile.get("page") or {}
    _num(page.get("width_mm"), "page.width_mm", 100, 500, errors)
    _num(page.get("height_mm"), "page.height_mm", 100, 500, errors)
    margins = page.get("margins_cm") or {}
    for side in ("top", "bottom", "left", "right"):
        _num(margins.get(side), f"page.margins_cm.{side}", 0, 10, errors)

    fonts = profile.get("fonts") or {}
    for key in ("east_asia", "latin"):
        if not str(fonts.get(key, "")).strip():
            errors.append(f"fonts.{key} 不能为空")

    body = profile.get("body") or {}
    _num(body.get("size_pt"), "body.size_pt", 6, 72, errors)
    _num(body.get("line_spacing"), "body.line_spacing", 0.5, 3, errors)
    _num(body.get("first_line_indent_chars"), "body.first_line_indent_chars", 0, 10, errors)
    if body.get("alignment") not in ALIGNMENTS:
        errors.append(f"body.alignment 必须为 {sorted(ALIGNMENTS)}")

    for key in ("title", "author", "abstract", "keywords", "footnote", "quote"):
        block = profile.get(key) or {}
        if not isinstance(block, dict):
            errors.append(f"{key} 必须是对象")
            continue
        _num(block.get("size_pt"), f"{key}.size_pt", 6, 72, errors)
        if "alignment" in block and block["alignment"] not in ALIGNMENTS:
            errors.append(f"{key}.alignment 必须为 {sorted(ALIGNMENTS)}")

    headings = profile.get("headings") or {}
    for level in ("1", "2", "3"):
        block = headings.get(level)
        if not isinstance(block, dict):
            errors.append(f"headings.{level} 缺失")
            continue
        _num(block.get("size_pt"), f"headings.{level}.size_pt", 6, 72, errors)
        if not isinstance(block.get("bold"), bool):
            errors.append(f"headings.{level}.bold 必须是布尔值")
        if block.get("alignment") not in ALIGNMENTS:
            errors.append(f"headings.{level}.alignment 必须为 {sorted(ALIGNMENTS)}")
        _num(block.get("before_lines"), f"headings.{level}.before_lines", 0, 5, errors)
        _num(block.get("after_lines"), f"headings.{level}.after_lines", 0, 5, errors)
    return errors


def summarize(profile: dict) -> str:
    page = profile.get("page", {})
    body = profile.get("body", {})
    foot = profile.get("footnote", {})
    h = profile.get("headings", {})
    lines = [
        f"名称：{profile.get('name', '')}",
        f"来源：{profile.get('source', {}).get('type', '')} / {profile.get('source', {}).get('reference', '')}",
        f"页面：{page.get('width_mm')}×{page.get('height_mm')} mm，边距 "
        f"{page.get('margins_cm', {}).get('top')} / {page.get('margins_cm', {}).get('bottom')} / "
        f"{page.get('margins_cm', {}).get('left')} / {page.get('margins_cm', {}).get('right')} cm",
        f"正文：{profile.get('fonts', {}).get('east_asia', '')} {body.get('size_pt')}pt，"
        f"{body.get('line_spacing')} 倍行距，首行缩进 {body.get('first_line_indent_chars')} 字符",
        f"标题：{profile.get('title', {}).get('font', '')} {profile.get('title', {}).get('size_pt')}pt",
        f"一级：{h.get('1', {}).get('size_pt')}pt；二级：{h.get('2', {}).get('size_pt')}pt；三级：{h.get('3', {}).get('size_pt')}pt",
        f"脚注：{foot.get('font', '')} {foot.get('size_pt')}pt，{foot.get('line_spacing')} 倍行距",
        f"参考模板：{profile.get('reference_docx', '') or '（未指定，使用默认）'}",
    ]
    return "\n".join(lines)


def cmd_list() -> int:
    if not PRESET_DIR.is_dir():
        print("no presets found", file=sys.stderr)
        return 2
    for path in sorted(PRESET_DIR.glob("*.json")):
        try:
            data = load_profile(path)
            print(f"{path.stem}\t{data.get('name', '')}")
        except (OSError, json.JSONDecodeError) as exc:
            print(f"{path.stem}\tERROR: {exc}")
    return 0


def cmd_init(preset: str, output: Path) -> int:
    source = PRESET_DIR / f"{preset}.json"
    if not source.is_file():
        print(f"error: preset not found: {preset}", file=sys.stderr)
        return 2
    data = load_profile(source)
    errors = validate_profile(data)
    if errors:
        for item in errors:
            print(f"ERROR: {item}", file=sys.stderr)
        return 2
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PROFILE_CREATED: {output}")
    return 0


def cmd_validate(path: Path) -> int:
    try:
        data = load_profile(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    errors = validate_profile(data)
    if errors:
        for item in errors:
            print(f"ERROR: {item}", file=sys.stderr)
        return 1
    print("PROFILE_OK")
    return 0


def cmd_show(path: Path) -> int:
    try:
        data = load_profile(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(summarize(data))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Manage DOCX format profiles.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="List bundled presets")
    pi = sub.add_parser("init", help="Copy a preset to a project profile")
    pi.add_argument("--preset", required=True)
    pi.add_argument("--output", required=True, type=Path)
    pv = sub.add_parser("validate", help="Validate a profile")
    pv.add_argument("path", type=Path)
    ps = sub.add_parser("show", help="Print a human-readable summary")
    ps.add_argument("path", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "init":
        return cmd_init(args.preset, args.output)
    if args.cmd == "validate":
        return cmd_validate(args.path)
    if args.cmd == "show":
        return cmd_show(args.path)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
