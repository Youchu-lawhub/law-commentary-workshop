#!/usr/bin/env python3
"""User-level channel registry: installation-stage state, kept outside any project.

安装态与任务态分离（1.3.0）：
- 安装态（本文件管理）：已验收通道、一次性同意（代装授权/语料目录/外发边界）。
  一次配置，跨项目持久；由安装访谈（cold-start.md 安装轮）产出。
- 任务态（项目内）：每个项目导入注册表后做活性复验与降级处置，
  记录在项目内 02b-channel-decisions.md，由 audit_commentary.py 强制。

默认路径：~/.law-commentary/channel-registry.json（--registry-path 可覆盖）。

子命令：
  init                     创建空注册表（已存在则拒绝，--force 覆盖）
  ack --by NAME [--date]   记录"安装访谈已完成并由用户确认"
  import --project DIR     把注册表已验收通道导入项目 channel-probe.json
                           （要求注册表已 ack，否则拒绝）
  status                   打印注册表摘要（JSON）

退出码：0 成功；2 拒绝执行；3 注册表缺失/未完成安装访谈。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY = Path.home() / ".law-commentary" / "channel-registry.json"

EMPTY_REGISTRY: dict[str, Any] = {
    "schema_version": 1,
    "registry_meta": {
        "created_at": "",
        "interview_completed_at": "",
        "interview_confirmed_by": "",
        "note": "",
    },
    "consents": {
        "allow_agent_install": False,
        "corpus_roots": [],
        "outbound_query_ok": False,
    },
    "channels": {},
}


def today() -> str:
    return dt.date.today().isoformat()


class RegistryError(Exception):
    """携带退出码与 JSON 负载的受控失败。"""

    def __init__(self, code: int, payload: dict[str, str]) -> None:
        super().__init__(payload.get("message", ""))
        self.code = code
        self.payload = payload


def load_registry(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(
            3,
            {
                "error": "REGISTRY_MISSING",
                "message": f"通道注册表不存在：{path}。先完成安装访谈，再运行 init。",
            },
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(
            3, {"error": "REGISTRY_INVALID", "message": str(exc)}
        ) from exc
    if not isinstance(data, dict) or "channels" not in data:
        raise RegistryError(
            3,
            {
                "error": "REGISTRY_INVALID",
                "message": "注册表结构无效：缺少 channels 字段。",
            },
        )
    return data


def save_registry(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def cmd_init(args: argparse.Namespace) -> int:
    path: Path = args.registry_path
    if path.is_file() and not args.force:
        print(
            json.dumps(
                {
                    "error": "REGISTRY_EXISTS",
                    "message": f"注册表已存在：{path}（--force 覆盖）。",
                },
                ensure_ascii=False,
            )
        )
        return 2
    data = json.loads(json.dumps(EMPTY_REGISTRY))  # deep copy
    data["registry_meta"]["created_at"] = today()
    save_registry(path, data)
    print(
        json.dumps(
            {
                "ok": True,
                "path": str(path),
                "message": "空注册表已创建。完成安装访谈后运行 ack 记录用户确认。",
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_ack(args: argparse.Namespace) -> int:
    path: Path = args.registry_path
    data = load_registry(path)
    if not data["registry_meta"].get("interview_completed_at"):
        data["registry_meta"]["interview_completed_at"] = args.date or today()
    data["registry_meta"]["interview_confirmed_by"] = args.by
    if args.note:
        data["registry_meta"]["note"] = args.note
    save_registry(path, data)
    print(
        json.dumps(
            {
                "ok": True,
                "interview_completed_at": data["registry_meta"][
                    "interview_completed_at"
                ],
                "interview_confirmed_by": args.by,
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    path: Path = args.registry_path
    data = load_registry(path)
    meta = data["registry_meta"]
    if not meta.get("interview_completed_at") or not meta.get(
        "interview_confirmed_by"
    ):
        print(
            json.dumps(
                {
                    "error": "INTERVIEW_NOT_ACKED",
                    "message": (
                        "注册表尚未记录安装访谈的用户确认（ack）。"
                        "未经用户确认的通道不得导入项目——"
                        "这正是本注册表要堵住的绕过路径。"
                    ),
                },
                ensure_ascii=False,
            )
        )
        return 3

    project: Path = args.project
    probe_path = project / "channel-probe.json"
    if not probe_path.is_file():
        print(
            json.dumps(
                {
                    "error": "PROJECT_PROBE_MISSING",
                    "message": f"项目缺少 channel-probe.json：{probe_path}",
                },
                ensure_ascii=False,
            )
        )
        return 2
    try:
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
        capabilities = probe["capabilities"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(
            json.dumps(
                {"error": "PROJECT_PROBE_INVALID", "message": str(exc)},
                ensure_ascii=False,
            )
        )
        return 2

    imported: list[str] = []
    for slot, channel in data["channels"].items():
        if slot not in capabilities:
            continue
        item = capabilities[slot]
        if not isinstance(item, dict):
            continue
        item["status"] = str(channel.get("status", "unknown"))
        item["tool"] = str(channel.get("tool", ""))
        item["source"] = "imported_from_registry"
        item["registry_ref"] = f"{path}#{slot}"
        item["accepted_at"] = str(channel.get("accepted_at", ""))
        if channel.get("acceptance"):
            item.setdefault("probe_case", str(channel["acceptance"]))
        imported.append(slot)

    probe["registry_import"] = {
        "path": str(path),
        "imported_at": today(),
        "interview_confirmed_by": meta.get("interview_confirmed_by", ""),
        "imported_slots": imported,
        "consents_snapshot": {
            "allow_agent_install": bool(data["consents"]["allow_agent_install"]),
            "corpus_roots": data["consents"]["corpus_roots"],
            "outbound_query_ok": bool(data["consents"]["outbound_query_ok"]),
        },
    }
    probe_path.write_text(
        json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    untouched = sorted(
        slot
        for slot in capabilities
        if capabilities[slot].get("source") != "imported_from_registry"
        and slot not in imported
    )
    print(
        json.dumps(
            {
                "ok": True,
                "imported_slots": imported,
                "uncovered_slots": untouched,
                "message": (
                    "未覆盖槽位保持 unknown，须按任务态降级决策表处置"
                    "（02b-channel-decisions.md），由审计强制。"
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    path: Path = args.registry_path
    data = load_registry(path)
    channels = data["channels"]
    print(
        json.dumps(
            {
                "path": str(path),
                "interview_completed_at": data["registry_meta"].get(
                    "interview_completed_at", ""
                ),
                "interview_confirmed_by": data["registry_meta"].get(
                    "interview_confirmed_by", ""
                ),
                "channels_total": len(channels),
                "by_status": {
                    status: sorted(
                        slot for slot, ch in channels.items()
                        if ch.get("status") == status
                    )
                    for status in sorted(
                        {ch.get("status", "?") for ch in channels.values()}
                    )
                },
                "consents": data["consents"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="用户级通道注册表（安装态）：init / ack / import / status"
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="注册表路径（默认 ~/.law-commentary/channel-registry.json）",
    )
    # 子命令之后也接受 --registry-path（SUPPRESS 避免覆盖子命令前给出的值）
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--registry-path", type=Path, default=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", parents=[common], help="创建空注册表")
    p_init.add_argument("--force", action="store_true", help="覆盖已存在的注册表")
    p_init.set_defaults(func=cmd_init)

    p_ack = sub.add_parser("ack", parents=[common], help="记录安装访谈已完成并由用户确认")
    p_ack.add_argument("--by", required=True, help="确认者（须为用户本人）")
    p_ack.add_argument("--date", help="确认日期 YYYY-MM-DD（默认今天）")
    p_ack.add_argument("--note", help="备注")
    p_ack.set_defaults(func=cmd_ack)

    p_import = sub.add_parser(
        "import", parents=[common], help="把注册表通道导入项目 channel-probe.json"
    )
    p_import.add_argument("--project", type=Path, required=True)
    p_import.set_defaults(func=cmd_import)

    p_status = sub.add_parser("status", parents=[common], help="打印注册表摘要")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RegistryError as exc:
        print(json.dumps(exc.payload, ensure_ascii=False))
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
