#!/usr/bin/env python3
"""Record and inspect human collaboration gates for commentary projects."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any


# 四个共创确认闸（由原七闸合并而来）。
# 每闸映射为 (本闸完成时置为 completed 的阶段列表, 通过后进入的下一阶段)。
# G1_topic   = 原 G1_norm_scope + G2_thesis（选题：规范范围 + 研究问题/暂定立场）
# G2_research= 原 G3_research + G4_evidence（研究：资料覆盖 + 命题-证据取舍）
# G3_outline = 原 G5_outline（大纲）
# G4_final   = 原 G6_draft + G7_delivery（终稿：论证成立 + 编校放行 + 交付形态）
GATE_FLOW = OrderedDict(
    [
        ("G1_topic", (["norm_locked", "problem_mapped"], "retrieval_complete")),
        ("G2_research", (["retrieval_complete", "evidence_synthesized"], "outline_approved")),
        ("G3_outline", (["outline_approved"], "draft_complete")),
        ("G4_final", (["draft_complete", "editorial_gate", "delivery"], None)),
    ]
)

# 请求/查看闸门时，逐份全文打印待确认文件的单文件行数上限；超出则头尾截断并给出完整路径。
MAX_PRINT_LINES = 2000

NON_USER_APPROVERS = {"agent", "assistant", "codex", "auto", "system"}


def soft_auto_is_authorized(project: Path) -> bool:
    profile = project / "research-profile.yaml"
    try:
        text = profile.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(
        re.search(
            r"^\s*auto_approve_soft_gates\s*:\s*(?:true|yes|1)\s*(?:#.*)?$",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
    )


def load_state(project: Path) -> tuple[Path, dict[str, Any]]:
    state_path = project.expanduser().resolve() / "project-state.json"
    if not state_path.is_file():
        raise FileNotFoundError(f"project state not found: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state.get("gates"), dict):
        raise ValueError("project-state.json has no gates; migrate it to schema_version 2")
    missing = [gate_id for gate_id in GATE_FLOW if gate_id not in state["gates"]]
    if missing:
        raise ValueError("project-state.json is missing gates: " + ", ".join(missing))
    return state_path, state


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = dt.date.today().isoformat()
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_decision(
    project: Path,
    gate_id: str,
    actor: str,
    decision: str,
    reason: str,
    affected: str,
) -> None:
    path = project / "10-decision-log.md"
    if not path.exists():
        path.write_text("# 决策日志\n\n", encoding="utf-8")
    entry = (
        f"\n### {dt.date.today().isoformat()} · {gate_id} · {decision}\n\n"
        f"- 决定者：{actor}\n"
        f"- 决定：{decision}\n"
        f"- 理由：{reason or '未另行说明'}\n"
        f"- 受影响的命题/章节/文件：{affected}\n"
        "- 被否决或替代的方案：见对应阶段简报或用户意见\n"
        "- 后续动作：依 project-state.json 从当前阶段继续\n"
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def validate_gate(state: dict[str, Any], gate_id: str) -> dict[str, Any]:
    if gate_id not in GATE_FLOW:
        raise ValueError(f"unknown gate: {gate_id}")
    gate = state["gates"].get(gate_id)
    if not isinstance(gate, dict):
        raise ValueError(f"gate data is invalid: {gate_id}")
    return gate


def review_files_for(gate: dict[str, Any]) -> list[str]:
    """Collect every file this gate must present to the user, brief first, deduplicated."""
    ordered: list[str] = []
    brief = str(gate.get("brief", "")).strip()
    if brief:
        ordered.append(brief)
    declared = gate.get("review_files") or []
    if isinstance(declared, str):
        declared = [declared]
    for name in declared:
        name = str(name).strip()
        if name and name not in ordered:
            ordered.append(name)
    artifact = str(gate.get("artifact", "")).strip()
    if artifact and artifact not in ordered:
        ordered.append(artifact)
    return ordered


def _review_path(project: Path, name: str) -> Path:
    """把状态文件声明的文件名解析为项目目录内的路径。

    `project-state.json` 属于可被共享、复制与手工编辑的数据，其中的路径名不可信：
    越界（`../`、绝对路径）或符号链接一律拒绝，避免把项目外的文件读进会话输出。
    """
    root = project.resolve()
    relative = Path(name)
    candidate = root / relative
    if relative.is_absolute() or candidate.is_symlink() or not candidate.resolve().is_relative_to(root):
        raise ValueError(f"待确认文件路径超出项目目录，已拒绝读取：{name}")
    return candidate


def _print_review_file(project: Path, name: str) -> None:
    path = _review_path(project, name)
    print("\n" + "=" * 72)
    print(f"# 待确认文件：{name}")
    print("=" * 72)
    if not path.is_file():
        print("[文件不存在——尚不能请求本闸]")
        return
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) > MAX_PRINT_LINES:
        head = MAX_PRINT_LINES - 60
        print("\n".join(lines[:head]))
        print(f"\n... [中间 {len(lines) - head - 40} 行已省略；完整文件见 {path}] ...\n")
        print("\n".join(lines[-40:]))
    else:
        print(text.rstrip())


def print_gate(project: Path, gate_id: str, gate: dict[str, Any]) -> None:
    print(f"{gate_id} [{gate.get('mode', '')}] status={gate.get('status', '')}")
    print(f"Question: {gate.get('question', '')}")
    names = review_files_for(gate)
    if not names:
        print("Review files: missing")
        return
    print("Review files: " + ", ".join(names))
    print("\n以下为本闸全部待确认文件的完整内容，请据此判断后再决定：")
    for name in names:
        _print_review_file(project, name)


def require_reviewable_artifacts(project: Path, gate: dict[str, Any]) -> None:
    names = review_files_for(gate)
    if not names:
        raise ValueError("gate declares no review files")
    for name in names:
        path = _review_path(project, name)
        if not path.is_file():
            raise FileNotFoundError(f"review file is missing: {name}")
        body = path.read_text(encoding="utf-8")
        if not body.strip() or re.search(r"\{\{[^{}\n]+\}\}", body):
            raise ValueError(f"review file is empty or contains unfinished placeholders: {name}")


def require_predecessors(state: dict[str, Any], gate_id: str) -> None:
    ids = list(GATE_FLOW)
    for earlier in ids[:ids.index(gate_id)]:
        if state["gates"][earlier].get("status") != "approved":
            raise ValueError(f"resolve earlier gate first: {earlier}")


def request_gate(project: Path, state_path: Path, state: dict[str, Any], gate_id: str) -> None:
    gate = validate_gate(state, gate_id)
    require_predecessors(state, gate_id)
    require_reviewable_artifacts(project, gate)
    brief = project / str(gate.get("brief", ""))
    gate["status"] = "awaiting"
    gate["decision"] = ""
    gate["approver"] = ""
    gate["decided_at"] = ""
    gate["note"] = ""
    gate["auto_approved"] = False
    save_state(state_path, state)
    append_decision(project, gate_id, "agent", "awaiting_user", gate.get("question", ""), brief.name)
    print_gate(project, gate_id, gate)


def approve_gate(
    project: Path,
    state_path: Path,
    state: dict[str, Any],
    gate_id: str,
    actor: str,
    note: str,
    auto: bool = False,
) -> None:
    gate = validate_gate(state, gate_id)
    mode = str(gate.get("mode", ""))
    normalized_actor = actor.strip().lower()
    if not actor.strip():
        raise ValueError("--by is required")
    if mode == "hard" and (auto or normalized_actor in NON_USER_APPROVERS):
        raise ValueError("a hard gate must be approved by the user, not by the Agent or auto-approval")
    if auto and mode != "soft":
        raise ValueError("only soft gates may be auto-approved")
    if auto and not soft_auto_is_authorized(project):
        raise ValueError("soft-gate auto-approval is not authorized in research-profile.yaml")
    if auto and not note.strip():
        raise ValueError("soft-gate auto-approval requires an explicit reason")

    require_predecessors(state, gate_id)
    require_reviewable_artifacts(project, gate)
    if gate.get("status") != "awaiting":
        raise ValueError("request the current reviewable gate before recording approval")
    if mode == "hard" and not note.strip():
        raise ValueError("hard-gate approval must record the actual user instruction and conversation locator")
    gate["status"] = "approved"
    gate["approver"] = actor.strip()
    gate["decided_at"] = dt.date.today().isoformat()
    gate["decision"] = "approved"
    gate["note"] = note.strip()
    gate["auto_approved"] = auto

    completed_stages, next_stage = GATE_FLOW[gate_id]
    stages = state.get("stages", {})
    if isinstance(stages, dict):
        for stage_name in completed_stages:
            if stage_name in stages:
                stages[stage_name] = "completed"
        if next_stage and stages.get(next_stage) == "pending":
            stages[next_stage] = "in_progress"
            state["current_stage"] = next_stage
        elif next_stage is None:
            state["current_stage"] = "delivery"
    save_state(state_path, state)
    decision = "auto_approved" if auto else "approved"
    append_decision(project, gate_id, actor.strip(), decision, note, str(gate.get("artifact", "")))
    print(f"{gate_id}: approved by {actor.strip()}")


def rework_gate(
    project: Path,
    state_path: Path,
    state: dict[str, Any],
    gate_id: str,
    actor: str,
    reason: str,
) -> None:
    if not actor.strip() or not reason.strip():
        raise ValueError("--by and --reason are required for rework")
    gate = validate_gate(state, gate_id)
    stage_names = list(state.get("stages", {}).keys())
    completed_stages, _ = GATE_FLOW[gate_id]
    restart_stage = completed_stages[0]
    if restart_stage in stage_names:
        restart_index = stage_names.index(restart_stage)
        for index, stage_name in enumerate(stage_names):
            if index < restart_index:
                continue
            state["stages"][stage_name] = "in_progress" if index == restart_index else "pending"
        state["current_stage"] = restart_stage

    gate_ids = list(GATE_FLOW)
    gate_index = gate_ids.index(gate_id)
    for later_id in gate_ids[gate_index:]:
        later = state["gates"][later_id]
        later["status"] = "rework" if later_id == gate_id else "pending"
        later["approver"] = actor.strip() if later_id == gate_id else ""
        later["decided_at"] = dt.date.today().isoformat() if later_id == gate_id else ""
        later["decision"] = "rework" if later_id == gate_id else ""
        later["note"] = reason.strip() if later_id == gate_id else ""
        later["auto_approved"] = False

    save_state(state_path, state)
    append_decision(project, gate_id, actor.strip(), "rework", reason.strip(), restart_stage)
    print(f"{gate_id}: rework; resume from {restart_stage}")


def print_status(state: dict[str, Any]) -> None:
    print(f"Current stage: {state.get('current_stage', '')}")
    print("Gates:")
    for gate_id in GATE_FLOW:
        gate = state["gates"][gate_id]
        suffix = " (auto)" if gate.get("auto_approved") else ""
        print(f"- {gate_id}: {gate.get('status', '')} [{gate.get('mode', '')}]{suffix}")
    next_gate = next(
        (
            gate_id
            for gate_id in GATE_FLOW
            if state["gates"][gate_id].get("status") != "approved"
        ),
        None,
    )
    print(f"Next unresolved gate: {next_gate or 'none'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect and record commentary collaboration gates.")
    parser.add_argument("project", help="Commentary project directory")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--status", action="store_true", help="Show all gate statuses")
    actions.add_argument("--check", metavar="GATE", help="Print a gate and its brief without mutation")
    actions.add_argument("--request", metavar="GATE", help="Mark a gate awaiting and print its brief")
    actions.add_argument("--approve", metavar="GATE", help="Record explicit approval")
    actions.add_argument("--auto-approve", metavar="GATE",
                         help="Auto-approve a soft gate. All shipped gates are hard, so this fails unless a gate is explicitly marked soft and authorized via research-profile.yaml (collaboration.auto_approve_soft_gates)")
    actions.add_argument("--rework", metavar="GATE", help="Record rework and roll back later stages")
    parser.add_argument("--by", default="", help="Decision maker, e.g. user or an actual name")
    parser.add_argument("--note", default="", help="Approval note")
    parser.add_argument("--reason", default="", help="Rework or auto-approval reason")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = Path(args.project).expanduser().resolve()
    try:
        state_path, state = load_state(project)
        if args.status:
            print_status(state)
        elif args.check:
            print_gate(project, args.check, validate_gate(state, args.check))
        elif args.request:
            request_gate(project, state_path, state, args.request)
        elif args.approve:
            approve_gate(project, state_path, state, args.approve, args.by, args.note)
        elif args.auto_approve:
            approve_gate(
                project,
                state_path,
                state,
                args.auto_approve,
                args.by or "agent",
                args.reason,
                auto=True,
            )
        elif args.rework:
            rework_gate(project, state_path, state, args.rework, args.by, args.reason)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
