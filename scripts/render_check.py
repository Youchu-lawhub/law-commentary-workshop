#!/usr/bin/env python3
"""Check DOCX structure and optionally render a PDF for human page review.

This tool deliberately separates machine-verifiable OOXML invariants from the
human visual decision. A successful render is not itself a layout sign-off.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

REQUIRED_STYLE_NAMES = {
    "Normal",
    "Title",
    "heading 1",
    "heading 2",
    "heading 3",
    "Abstract",
    "Keywords",
    "QuoteBlock",
    "footnote text",
    "footnote reference",
    "caption",
}


def _xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        return ET.fromstring(zf.read(name))
    except KeyError as exc:
        raise ValueError(f"缺少 OOXML 部件：{name}") from exc
    except ET.ParseError as exc:
        raise ValueError(f"OOXML 部件无法解析：{name}: {exc}") from exc


def validate_docx(path: Path, *, anonymous: bool = False) -> list[str]:
    """Return structural validation errors; an empty list means pass."""
    errors: list[str] = []
    if not path.is_file():
        return [f"文件不存在：{path}"]
    if not zipfile.is_zipfile(path):
        return [f"不是有效的 DOCX/ZIP 文件：{path}"]

    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            for required in ("[Content_Types].xml", "word/document.xml", "word/styles.xml"):
                if required not in names:
                    errors.append(f"缺少 OOXML 部件：{required}")
            if errors:
                return errors

            document = _xml(zf, "word/document.xml")
            styles = _xml(zf, "word/styles.xml")
            style_names = {
                node.attrib.get(f"{{{W_NS}}}val", "").casefold()
                for node in styles.findall(f".//{{{W_NS}}}style/{{{W_NS}}}name")
            }
            required_styles = {name.casefold() for name in REQUIRED_STYLE_NAMES}
            missing_styles = sorted(required_styles - style_names, key=str.casefold)
            if missing_styles:
                errors.append("缺少版式契约样式：" + "、".join(missing_styles))

            footnote_refs = document.findall(f".//{{{W_NS}}}footnoteReference")
            if footnote_refs:
                if "word/footnotes.xml" not in names:
                    errors.append("正文含脚注引用，但缺少 word/footnotes.xml")
                rels = _xml(zf, "word/_rels/document.xml.rels")
                rel_types = {node.attrib.get("Type", "") for node in rels.findall(f".//{{{REL_NS}}}Relationship")}
                if not any(value.endswith("/footnotes") for value in rel_types):
                    errors.append("正文含脚注引用，但缺少 footnotes 关系")
                content_types = _xml(zf, "[Content_Types].xml")
                overrides = {
                    node.attrib.get("PartName", "")
                    for node in content_types.findall(f".//{{{CT_NS}}}Override")
                }
                if "/word/footnotes.xml" not in overrides:
                    errors.append("正文含脚注引用，但内容类型未声明 footnotes.xml")

            if anonymous:
                if "docProps/core.xml" not in names:
                    errors.append("匿名稿缺少 core properties，无法核验身份元数据")
                else:
                    core = _xml(zf, "docProps/core.xml")
                    creator = (core.findtext(f"{{{DC_NS}}}creator") or "").strip()
                    modified = (core.findtext(f"{{{CP_NS}}}lastModifiedBy") or "").strip()
                    if creator or modified:
                        errors.append("匿名稿仍含作者或最后修改者元数据")
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        errors.append(str(exc))
    return errors


def resolve_soffice(explicit: str | None) -> Path | None:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        return candidate if candidate.is_file() else None
    found = shutil.which("soffice")
    if found:
        return Path(found).resolve()
    mac_candidate = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    return mac_candidate if mac_candidate.is_file() else None


def render_pdf(docx: Path, output_dir: Path, soffice: Path) -> tuple[Path | None, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="law_commentary_lo_") as profile:
        cmd = [
            str(soffice),
            f"-env:UserInstallation={Path(profile).resolve().as_uri()}",
            "--headless",
            "--norestore",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(docx),
        ]
        try:
            proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        except OSError as exc:
            return None, str(exc)
    pdf = output_dir / f"{docx.stem}.pdf"
    log = "\n".join(part for part in (proc.stdout.strip(), proc.stderr.strip()) if part)
    if proc.returncode != 0 or not pdf.is_file() or pdf.stat().st_size == 0:
        return None, log or f"LibreOffice 退出码：{proc.returncode}"
    return pdf, log


def pdf_page_count(pdf: Path) -> int | None:
    binary = shutil.which("pdfinfo")
    if not binary:
        return None
    try:
        proc = subprocess.run([binary, str(pdf)], check=False, capture_output=True, text=True)
    except OSError:
        return None
    match = re.search(r"^Pages:\s+(\d+)\s*$", proc.stdout, re.MULTILINE)
    return int(match.group(1)) if proc.returncode == 0 and match else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a DOCX and optionally render it to PDF.")
    parser.add_argument("docx", type=Path)
    parser.add_argument("--anonymous", action="store_true", help="Require blank author metadata")
    parser.add_argument("--render", action="store_true", help="Create a PDF for human page review")
    parser.add_argument("--render-dir", type=Path, help="PDF output directory")
    parser.add_argument("--soffice", help="Explicit LibreOffice soffice executable")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    docx = args.docx.expanduser().resolve()
    errors = validate_docx(docx, anonymous=args.anonymous)
    if errors:
        for item in errors:
            print(f"ERROR: {item}", file=sys.stderr)
        return 2
    print(f"STRUCTURE_OK: {docx}")

    if not args.render:
        return 0
    soffice = resolve_soffice(args.soffice)
    if soffice is None:
        print("RENDER_UNAVAILABLE: 未找到 LibreOffice；不得签署 layout_rendered", file=sys.stderr)
        return 3
    render_dir = (args.render_dir or docx.parent / "rendered").expanduser().resolve()
    pdf, log = render_pdf(docx, render_dir, soffice)
    if pdf is None:
        print(f"RENDER_FAILED: {log}", file=sys.stderr)
        return 2
    pages = pdf_page_count(pdf)
    page_text = str(pages) if pages is not None else "unknown"
    print(f"RENDER_CREATED: {pdf} (pages={page_text})")
    print("HUMAN_REVIEW_REQUIRED: 必须逐页目检后才能签署 layout_rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
