#!/usr/bin/env python3
"""Inventory an authorized local research corpus without treating files as read."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json", ".jsonl", ".html", ".htm"}
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | {".docx", ".pdf"}
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    return "".join(node.text or "" for node in root.findall(f".//{{{W_NS}}}t"))


def preview(path: Path, limit: int) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        text = decode_text(path.read_bytes())
        return ("text_indexed" if text else "metadata_only", " ".join(text.split())[:limit])
    if suffix == ".docx":
        try:
            text = docx_text(path)
        except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError):
            return "metadata_only", ""
        return "text_indexed", " ".join(text.split())[:limit]
    return "metadata_only", ""


def scan(roots: list[Path], *, max_bytes: int, preview_chars: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for root_number, original in enumerate(roots, start=1):
        root = original.expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"corpus root not found: {root}")
        files = [root] if root.is_file() else root.rglob("*")
        for path in files:
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            try:
                stat = path.stat()
                digest = file_hash(path)
                if stat.st_size <= max_bytes:
                    text_status, snippet = preview(path, preview_chars)
                else:
                    text_status, snippet = "metadata_only", ""
                relative = path.name if root.is_file() else str(path.relative_to(root))
                rows.append(
                    {
                        "corpus_id": f"L{root_number:02d}-{digest[:12]}",
                        "root_alias": f"root-{root_number}",
                        "relative_path": relative,
                        "suffix": path.suffix.lower(),
                        "size_bytes": stat.st_size,
                        "modified_at": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                        "sha256": digest,
                        "index_status": text_status,
                        "preview": snippet,
                        "evidence_status": "candidate_only",
                    }
                )
            except OSError as exc:
                rows.append(
                    {
                        "root_alias": f"root-{root_number}",
                        "relative_path": str(path),
                        "index_status": "read_error",
                        "error": str(exc),
                        "evidence_status": "candidate_only",
                    }
                )
    return sorted(rows, key=lambda row: (str(row.get("root_alias")), str(row.get("relative_path"))))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a privacy-minimized local corpus inventory.")
    parser.add_argument("--root", action="append", required=True, type=Path, help="Authorized file/directory; repeatable")
    parser.add_argument("--output", required=True, type=Path, help="Destination JSONL index")
    parser.add_argument("--max-mb", type=int, default=25, help="Maximum file size for text preview")
    parser.add_argument("--preview-chars", type=int, default=300, help="Preview characters; use 0 to suppress")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_mb < 1 or args.preview_chars < 0:
        print("error: --max-mb must be positive and --preview-chars non-negative", file=sys.stderr)
        return 2
    try:
        rows = scan(args.root, max_bytes=args.max_mb * 1024 * 1024, preview_chars=args.preview_chars)
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    indexed = sum(row.get("index_status") == "text_indexed" for row in rows)
    unreadable = sum(row.get("index_status") == "read_error" for row in rows)
    print(f"Indexed {len(rows)} files ({indexed} text previews) -> {output}")
    if unreadable:
        print(
            f"error: {unreadable} of {len(rows)} files could not be read (index_status=read_error); "
            "the index is incomplete",
            file=sys.stderr,
        )
    print("NOTICE: corpus index entries remain candidate_only until a source is actually read and logged.")
    if not rows:
        return 0
    if unreadable == len(rows):
        return 2
    return 1 if unreadable else 0


if __name__ == "__main__":
    raise SystemExit(main())
