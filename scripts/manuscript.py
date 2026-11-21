"""Shared manuscript text accounting for the audit and quick checker."""

from __future__ import annotations

import re


FOOTNOTE_DEFINITION = re.compile(r"^ {0,3}\[\^([^\]\s]+)\]:")
FOOTNOTE_REFERENCE = re.compile(r"\[\^([^\]\s]+)\]")
INLINE_CODE = re.compile(r"(?<!`)(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)")


def chinese_character_count(text: str) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", text))


def parse_manuscript(text: str) -> tuple[str, str, list[str], set[str]]:
    """Return body, footnote text, definition IDs (including repeats), reference IDs.

    Handle top-level Markdown footnotes (numeric or named, 0–3 leading spaces)
    and continuations indented by a tab or at least four spaces, across blank
    lines. Unindented text after a definition resumes the body. HTML comments
    and actual footnote reference markers are excluded from body accounting.

    Backtick spans and backtick/tilde fences remain literal body text, not
    footnotes; indented code outside a footnote is also literal. This is not a
    general Markdown renderer: nested list/blockquote footnotes and HTML
    footnotes are outside this accounting convention.
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    lines = text.splitlines(keepends=True)
    masked_lines: list[str] = []
    fence = ""
    for line in lines:
        if fence:
            masked_lines.append(re.sub(r"[^\r\n]", " ", line))
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*[\r\n]*", line):
                fence = ""
            continue
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)", line)
        if opening and not (opening[1][0] == "`" and "`" in opening[2]):
            fence = opening[1]
            masked_lines.append(re.sub(r"[^\r\n]", " ", line))
        else:
            masked_lines.append(line)
    # A same-length mask lets us recognize syntax outside code while retaining
    # literal code examples in the returned body, without altering their text.
    masked = INLINE_CODE.sub(lambda m: re.sub(r"[^\r\n]", " ", m[0]), "".join(masked_lines))
    body: list[str] = []
    footnotes: list[str] = []
    definitions: list[str] = []
    references: set[str] = set()
    in_footnote = False
    for line, syntax in zip(lines, masked.splitlines(keepends=True)):
        definition = FOOTNOTE_DEFINITION.match(syntax)
        if definition:
            definitions.append(definition[1])
            footnotes.append(line)
            in_footnote = True
            continue
        indented = bool(re.match(r"^(?: {4}| {0,3}\t)", line))
        if in_footnote and (not line.strip() or indented):
            footnotes.append(line)
            continue
        in_footnote = False
        if indented:
            body.append(line)
            continue
        end = 0
        for reference in FOOTNOTE_REFERENCE.finditer(syntax):
            references.add(reference[1])
            body.append(line[end:reference.start()])
            end = reference.end()
        body.append(line[end:])
    return "".join(body), "".join(footnotes), definitions, references
