#!/usr/bin/env python3
"""Create a fresh, evidence-traceable legal commentary project."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path


TOKEN_NAMES = {
    "PROJECT_TITLE",
    "LAW_TITLE",
    "ARTICLE",
    "AS_OF",
    "TARGET_JOURNAL",
    "CREATED_AT",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialize a Chinese legal-provision commentary research project."
    )
    parser.add_argument("--output", required=True, help="Destination project directory")
    parser.add_argument("--law", required=True, help="Official title of the norm")
    parser.add_argument("--article", required=True, help="Article, paragraph, or item")
    parser.add_argument(
        "--as-of",
        default=dt.date.today().isoformat(),
        help="Research cutoff date in YYYY-MM-DD form",
    )
    parser.add_argument("--journal", default="", help="Target journal, if already known")
    parser.add_argument("--title", default="", help="Working title; generated if omitted")
    return parser


def validate_iso_date(value: str) -> str:
    try:
        dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("--as-of must be a valid YYYY-MM-DD date") from exc
    return value


def initialize_project(
    output: Path,
    law_title: str,
    article: str,
    as_of: str,
    target_journal: str = "",
    project_title: str = "",
) -> list[Path]:
    validate_iso_date(as_of)
    law_title = law_title.strip()
    article = article.strip()
    if not law_title or not article:
        raise ValueError("--law and --article must not be blank")

    output = output.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"destination is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    template_dir = Path(__file__).resolve().parent.parent / "assets" / "project-template"
    if not template_dir.is_dir():
        raise FileNotFoundError(f"project template not found: {template_dir}")

    created_at = dt.date.today().isoformat()
    title = project_title.strip() or f"{law_title}{article}评注"
    replacements = {
        "PROJECT_TITLE": title,
        "LAW_TITLE": law_title,
        "ARTICLE": article,
        "AS_OF": as_of,
        "TARGET_JOURNAL": target_journal.strip(),
        "CREATED_AT": created_at,
    }

    created: list[Path] = []
    for source in sorted(template_dir.iterdir()):
        if not source.is_file():
            continue
        destination = output / source.name
        try:
            body = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copy2(source, destination)
        else:
            for token, value in replacements.items():
                # JSON and YAML templates place each substituted token inside double quotes.
                replacement = json.dumps(value, ensure_ascii=False)[1:-1] if source.suffix in {".json", ".yaml"} else value
                body = body.replace("{{" + token + "}}", replacement)
            destination.write_text(body, encoding="utf-8")
        created.append(destination)

    ledger = output / "03-source-ledger.jsonl"
    ledger.touch(exist_ok=False)
    created.append(ledger)
    return sorted(created)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        files = initialize_project(
            output=Path(args.output),
            law_title=args.law,
            article=args.article,
            as_of=args.as_of,
            target_journal=args.journal,
            project_title=args.title,
        )
    except (ValueError, FileExistsError, FileNotFoundError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Initialized {Path(args.output).expanduser().resolve()}")
    for path in files:
        print(f"- {path.name}")
    print("Initial quality state: BLOCKED (complete the evidence and sign-off gates).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
