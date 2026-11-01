#!/usr/bin/env python3
"""把格式配置写入 DOCX 的样式与页面设置。

用法：
  python3 apply_format_profile.py --profile format-profile.json --docx paper.docx
  python3 apply_format_profile.py --profile p.json --docx in.docx --out out.docx

只修改样式与页面参数，不改正文内容、脚注关系与文档元数据。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"

PPR_ORDER = [
    "pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl",
    "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens",
    "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN",
    "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing",
    "mirrorIndents", "suppressOverlap", "jc", "textDirection", "textAlignment",
    "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange",
]
RPR_ORDER = [
    "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike",
    "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish",
    "webHidden", "color", "spacing", "w", "kern", "position", "sz", "szCs", "highlight",
    "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang",
    "eastAsianLayout", "specVanish", "oMath",
]


def q(tag: str) -> str:
    return f"{W}{tag}"


def ensure(parent: ET.Element, tag: str) -> ET.Element:
    el = parent.find(q(tag))
    if el is None:
        el = ET.SubElement(parent, q(tag))
    return el


def replace(parent: ET.Element, tag: str) -> ET.Element:
    for old in parent.findall(q(tag)):
        parent.remove(old)
    return ET.SubElement(parent, q(tag))


def sort_children(parent: ET.Element, order: list[str]) -> None:
    index = {name: i for i, name in enumerate(order)}
    children = list(parent)
    children.sort(key=lambda el: index.get(el.tag.split('}')[-1], 999))
    for el in children:
        parent.remove(el)
    for el in children:
        parent.append(el)


def set_fonts(el: ET.Element, latin: str, east_asia: str) -> None:
    fonts = ensure(el, "rFonts")
    for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        fonts.attrib.pop(q(attr), None)
    fonts.set(q("ascii"), latin)
    fonts.set(q("hAnsi"), latin)
    fonts.set(q("cs"), latin)
    fonts.set(q("eastAsia"), east_asia)


def set_size(el: ET.Element, size_pt: float) -> None:
    half = str(int(round(float(size_pt) * 2)))
    ensure(el, "sz").set(q("val"), half)
    ensure(el, "szCs").set(q("val"), half)


def set_bold(el: ET.Element | None, bold: bool) -> None:
    if el is None:
        return
    for tag in ("b", "bCs"):
        existing = el.find(q(tag))
        if bold:
            if existing is None:
                ET.SubElement(el, q(tag))
            else:
                existing.attrib.pop(q("val"), None)
        elif existing is not None:
            el.remove(existing)


def mm_to_twips(value: float) -> str:
    return str(int(round(float(value) / 25.4 * 1440)))


def cm_to_twips(value: float) -> str:
    return str(int(round(float(value) * 567)))


def style_map(styles_root: ET.Element) -> dict[str, ET.Element]:
    return {st.get(q("styleId")): st for st in styles_root.findall(q("style"))}


def style_ppr_rpr(style: ET.Element) -> tuple[ET.Element, ET.Element]:
    return ensure(style, "pPr"), ensure(style, "rPr")


def apply_body(profile: dict, styles: dict[str, ET.Element], styles_root: ET.Element) -> None:
    fonts = profile.get("fonts", {})
    latin = fonts.get("latin", "Times New Roman")
    east = fonts.get("east_asia", "宋体")
    body = profile.get("body", {})

    defaults = styles_root.find(q("docDefaults"))
    if defaults is not None:
        rpr_default = defaults.find(f"{q('rPrDefault')}/{q('rPr')}")
        if rpr_default is not None:
            set_fonts(rpr_default, latin, east)
            set_size(rpr_default, body.get("size_pt", 10.5))

    normal = styles.get("Normal")
    if normal is not None:
        ppr, rpr = style_ppr_rpr(normal)
        set_fonts(rpr, latin, east)
        set_size(rpr, body.get("size_pt", 10.5))
        spacing = replace(ppr, "spacing")
        spacing.set(q("line"), str(int(round(float(body.get("line_spacing", 1.25)) * 240))))
        spacing.set(q("lineRule"), "auto")
        spacing.set(q("before"), str(int(round(float(body.get("space_before_pt", 0)) * 20))))
        spacing.set(q("after"), str(int(round(float(body.get("space_after_pt", 0)) * 20))))
        ind = replace(ppr, "ind")
        ind.set(q("firstLineChars"), str(int(round(float(body.get("first_line_indent_chars", 2)) * 100))))
        jc = replace(ppr, "jc")
        jc.set(q("val"), body.get("alignment", "justify"))
        sort_children(ppr, PPR_ORDER)
        sort_children(rpr, RPR_ORDER)


def apply_title_and_headings(profile: dict, styles: dict[str, ET.Element]) -> None:
    fonts = profile.get("fonts", {})
    latin = fonts.get("latin", "Times New Roman")
    east = fonts.get("east_asia", "宋体")
    title = profile.get("title", {})
    title_style = styles.get("Title")
    if title_style is not None:
        ppr, rpr = style_ppr_rpr(title_style)
        set_fonts(rpr, latin, title.get("font", "黑体"))
        set_size(rpr, title.get("size_pt", 22))
        set_bold(rpr, bool(title.get("bold", True)))
        replace(ppr, "jc").set(q("val"), title.get("alignment", "center"))
        sort_children(ppr, PPR_ORDER)
        sort_children(rpr, RPR_ORDER)

    for level, spec in (profile.get("headings") or {}).items():
        style = styles.get(f"Heading{level}")
        if style is None:
            continue
        ppr, rpr = style_ppr_rpr(style)
        set_fonts(rpr, latin, spec.get("font", east))
        set_size(rpr, spec.get("size_pt", 12))
        set_bold(rpr, bool(spec.get("bold", False)))
        replace(ppr, "jc").set(q("val"), spec.get("alignment", "left"))
        spacing = replace(ppr, "spacing")
        spacing.set(q("beforeLines"), str(int(round(float(spec.get("before_lines", 0.3)) * 100))))
        spacing.set(q("afterLines"), str(int(round(float(spec.get("after_lines", 0.3)) * 100))))
        sort_children(ppr, PPR_ORDER)
        sort_children(rpr, RPR_ORDER)


def apply_auxiliary(profile: dict, styles: dict[str, ET.Element]) -> None:
    fonts = profile.get("fonts", {})
    latin = fonts.get("latin", "Times New Roman")
    east = fonts.get("east_asia", "宋体")

    footnote = profile.get("footnote", {})
    fn_style = styles.get("FootnoteText")
    if fn_style is not None:
        ppr, rpr = style_ppr_rpr(fn_style)
        set_fonts(rpr, latin, footnote.get("font", east))
        set_size(rpr, footnote.get("size_pt", 9))
        spacing = replace(ppr, "spacing")
        spacing.set(q("line"), str(int(round(float(footnote.get("line_spacing", 1.0)) * 240))))
        spacing.set(q("lineRule"), "auto")
        sort_children(ppr, PPR_ORDER)
        sort_children(rpr, RPR_ORDER)

    for style_id, block in (("Abstract", profile.get("abstract", {})), ("Keywords", profile.get("keywords", {}))):
        style = styles.get(style_id)
        if style is None:
            continue
        ppr, rpr = style_ppr_rpr(style)
        set_fonts(rpr, latin, block.get("font", east))
        set_size(rpr, block.get("size_pt", 10.5))
        sort_children(ppr, PPR_ORDER)
        sort_children(rpr, RPR_ORDER)

    quote = profile.get("quote", {})
    for style_id in ("Quote", "QuoteBlock"):
        style = styles.get(style_id)
        if style is None:
            continue
        ppr, rpr = style_ppr_rpr(style)
        set_fonts(rpr, latin, quote.get("font", east))
        set_size(rpr, quote.get("size_pt", 10.5))
        ind = replace(ppr, "ind")
        ind.set(q("leftChars"), str(int(round(float(quote.get("left_indent_chars", 1)) * 100))))
        ind.set(q("rightChars"), str(int(round(float(quote.get("right_indent_chars", 1)) * 100))))
        spacing = replace(ppr, "spacing")
        spacing.set(q("line"), str(int(round(float(quote.get("line_spacing", 1.0)) * 240))))
        spacing.set(q("lineRule"), "auto")
        sort_children(ppr, PPR_ORDER)
        sort_children(rpr, RPR_ORDER)


def apply_page(profile: dict, document_root: ET.Element) -> None:
    page = profile.get("page", {})
    margins = page.get("margins_cm", {})
    for sect in document_root.iter(q("sectPr")):
        pgsz = sect.find(q("pgSz"))
        if pgsz is None:
            pgsz = ET.SubElement(sect, q("pgSz"))
        pgsz.set(q("w"), mm_to_twips(page.get("width_mm", 210)))
        pgsz.set(q("h"), mm_to_twips(page.get("height_mm", 297)))
        pgmar = sect.find(q("pgMar"))
        if pgmar is None:
            pgmar = ET.SubElement(sect, q("pgMar"))
        pgmar.set(q("top"), cm_to_twips(margins.get("top", 2.54)))
        pgmar.set(q("bottom"), cm_to_twips(margins.get("bottom", 2.54)))
        pgmar.set(q("left"), cm_to_twips(margins.get("left", 3.17)))
        pgmar.set(q("right"), cm_to_twips(margins.get("right", 3.17)))


def register_namespaces(xml: str) -> None:
    for prefix, uri in re.findall(r'xmlns:([A-Za-z0-9]+)="([^"]+)"', xml):
        try:
            ET.register_namespace(prefix, uri)
        except ValueError:
            pass
    ET.register_namespace("w", W_NS)


def serialize(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def apply_profile(profile: dict, docx: Path, out: Path | None = None) -> Path:
    docx = docx.expanduser().resolve()
    out_path = (out or docx).expanduser().resolve()
    targets = {"word/styles.xml", "word/document.xml"}
    replacements: dict[str, bytes] = {}

    with zipfile.ZipFile(docx) as zin:
        styles_xml = zin.read("word/styles.xml").decode("utf-8")
        register_namespaces(styles_xml)
        styles_root = ET.fromstring(styles_xml)
        styles = style_map(styles_root)
        apply_body(profile, styles, styles_root)
        apply_title_and_headings(profile, styles)
        apply_auxiliary(profile, styles)
        replacements["word/styles.xml"] = serialize(styles_root)

        doc_xml = zin.read("word/document.xml").decode("utf-8")
        register_namespaces(doc_xml)
        doc_root = ET.fromstring(doc_xml)
        apply_page(profile, doc_root)
        replacements["word/document.xml"] = serialize(doc_root)

        fd, tmp_name = tempfile.mkstemp(suffix=".docx", dir=str(out_path.parent))
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            with zipfile.ZipFile(tmp_path, "w") as zout:
                for item in zin.infolist():
                    data = replacements.get(item.filename)
                    if data is None:
                        data = zin.read(item.filename)
                    zout.writestr(item, data)
            os.replace(tmp_path, out_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    return out_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Apply a JSON format profile to a DOCX.")
    p.add_argument("--profile", required=True, type=Path)
    p.add_argument("--docx", required=True, type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    try:
        profile = json.loads(args.profile.expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not args.docx.expanduser().is_file():
        print(f"error: docx not found: {args.docx}", file=sys.stderr)
        return 2
    try:
        result = apply_profile(profile, args.docx, args.out)
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f"FORMAT_APPLY_FAILED: {exc}", file=sys.stderr)
        return 2
    print(f"FORMAT_APPLIED: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
