#!/usr/bin/env python3
"""Static release gate for a law-commentary project.

This script checks traceability and completion invariants. It cannot determine
whether an interpretation is academically persuasive; that remains part of the
recorded human sign-off.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


REQUIRED_FILES = (
    "research-profile.yaml",
    "project-state.json",
    "channel-probe.json",
    "01-norm-dossier.md",
    "01a-norm-brief.md",
    "02-search-log.csv",
    "02a-thesis-brief.md",
    "02b-channel-decisions.md",
    "03-source-ledger.jsonl",
    "03a-research-brief.md",
    "04-case-matrix.csv",
    "04a-evidence-brief.md",
    "05-claim-evidence.csv",
    "06-outline.md",
    "06a-outline-brief.md",
    "07-paper.md",
    "07a-draft-brief.md",
    "08-citation-audit.csv",
    "09a-delivery-brief.md",
    "10-decision-log.md",
    "11-comparative-memo.md",
    "quality-signoff.json",
    "12-contribution-review.md",
    "13-scholarly-review.md",
)

HARD_GATES = {"G1_topic", "G2_research", "G3_outline", "G4_final"}
ALL_GATES = {
    "G1_topic",
    "G2_research",
    "G3_outline",
    "G4_final",
}
NON_USER_APPROVERS = {"agent", "assistant", "codex", "auto", "system"}

SIGNOFF_KEYS = (
    "retrieval_log_complete",
    "retrieval_saturation_reviewed",
    "adverse_sources_checked",
    "norm_text_current",
    "norm_hierarchy_checked",
    "cases_primary_checked",
    "case_subsequent_status_checked",
    "comparative_law_context_checked",
    "citations_pinpoint_checked",
    "quotations_compared",
    "cross_references_checked",
    "terminology_consistent",
    "argument_coherence_checked",
    "counterarguments_addressed",
    "practice_usability_checked",
    "abstract_matches_body",
    "journal_rules_current",
    "anonymization_checked",
    "academic_integrity_reviewed",
    "layout_rendered",
    "proofread_fresh_pass",
    "genre_coverage_checked",
    "contribution_comparison_checked",
    "scholarly_revision_completed",
    "norm_attribute_identified",
    "norm_combination_table_completed",
    "institution_distinction_completed",
    "exception_rules_enumerated",
    "procedure_and_burden_section_checked",
    "legislation_critique_labeled",
    "note_comment_layers_completed",
    "statements_and_judgments_distinguished",
    "case_types_matrix_completed",
    "case_collection_statement_consistent",
    "paragraph_codes_consistent",
    "jurisdiction_labels_checked",
    "comparative_law_necessity_checked",
    "foreign_source_tier_verified",
    "translation_terminology_checked",
    "translation_citation_integrity_checked",
    "translation_human_review_signed",
    "format_profile_confirmed",
    "format_profile_matches_output",
    "journal_format_spec_checked",
)

ALLOWED_SOURCE_STATUSES = {
    "discovered",
    "metadata_verified",
    "abstract_read",
    "partial_read",
    "fulltext_read",
    "primary_verified",
    "excluded",
}
PRIMARY_TYPES = {
    "statute",
    "regulation",
    "norm",
    "judicial_interpretation",
    "legislative_material",
    "case",
    "official_report",
    "foreign_law",
    "foreign_case",
}
ACADEMIC_TYPES = {"article", "book", "commentary", "thesis"}
EVIDENCE_REQUIRED_CLAIMS = {
    "norm_text",
    "history",
    "case_holding",
    "scholarly_attribution",
    "empirical",
    "comparative",
}
PLACEHOLDER_PATTERN = re.compile(
    r"\{\{[^{}\n]+\}\}|\[(?:待核实|待查证|待补充|待定)\]|\b(?:TODO|TBD)\b",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def finding(code: str, file_name: str, message: str) -> dict[str, str]:
    return {"code": code, "file": file_name, "message": message}


def is_true(value: Any) -> bool:
    if value is True:
        return True
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "checked"}


def split_ids(value: str | None) -> list[str]:
    return [part.strip() for part in re.split(r"[;|]", value or "") if part.strip()]


def target_minimum(profile_text: str) -> int | None:
    match = re.search(r"^\s*target_length\s*:\s*['\"]?([^\n#'\"]+)", profile_text, re.MULTILINE)
    if not match:
        return None
    numbers = [int(value) for value in re.findall(r"\d{4,6}", match.group(1))]
    return numbers[0] if numbers else None


def source_is_citable(source: dict[str, Any]) -> bool:
    source_type = str(source.get("type", "")).strip()
    status = str(source.get("status", "")).strip()
    if source_type in PRIMARY_TYPES:
        return status == "primary_verified"
    if source_type in ACADEMIC_TYPES:
        return status in {"partial_read", "fulltext_read"}
    return status in {"partial_read", "fulltext_read", "primary_verified"}


def read_csv_file(
    path: Path,
    required_columns: Iterable[str],
    errors: list[dict[str, str]],
) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or [])
            missing = sorted(set(required_columns) - columns)
            if missing:
                errors.append(
                    finding(
                        "CSV_COLUMNS_MISSING",
                        path.name,
                        "缺少字段：" + "、".join(missing),
                    )
                )
                return []
            rows: list[dict[str, str]] = []
            for line_number, row in enumerate(reader, start=2):
                extras = row.pop(None, None)
                if extras:
                    errors.append(
                        finding(
                            "CSV_COLUMN_SHIFT",
                            f"{path.name}:第 {line_number} 行",
                            "实际列数超过表头；多值字段请用分号，不要使用未加引号的英文逗号",
                        )
                    )
                clean = {str(key): str(value or "") for key, value in row.items()}
                if any(value.strip() for value in clean.values()) or extras:
                    rows.append(clean)
            return rows
    except (OSError, csv.Error) as exc:
        errors.append(finding("CSV_READ_ERROR", path.name, str(exc)))
        return []


def validate_linked_sources(
    ids: Iterable[str],
    location: str,
    sources: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    for source_id in ids:
        source = sources.get(source_id)
        if source is None:
            errors.append(
                finding("SOURCE_LINK_MISSING", location, f"引用了不存在的来源 ID：{source_id}")
            )
        elif not source_is_citable(source):
            errors.append(
                finding(
                    "SOURCE_NOT_CITABLE",
                    location,
                    f"来源 {source_id} 尚未达到可引用状态（当前：{source.get('status', '')}）",
                )
            )


def audit_project(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    incomplete_signoffs: list[str] = []
    incomplete_gates: list[str] = []
    metrics: dict[str, int] = {
        "sources": 0,
        "citable_sources": 0,
        "claims": 0,
        "included_cases": 0,
        "footnotes": 0,
        "citation_audit_rows": 0,
    }

    if not project.is_dir():
        errors.append(finding("PROJECT_NOT_FOUND", str(project), "项目目录不存在"))
        return finalize(project, errors, warnings, incomplete_signoffs, incomplete_gates, metrics)

    for name in REQUIRED_FILES:
        if not (project / name).is_file():
            errors.append(finding("REQUIRED_FILE_MISSING", name, "缺少必需项目文件"))

    text_files = tuple(name for name in REQUIRED_FILES if name.endswith((".md", ".yaml")))
    profile_text = ""
    for name in text_files:
        path = project / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if name == "research-profile.yaml":
                profile_text = text
        except OSError as exc:
            errors.append(finding("TEXT_READ_ERROR", name, str(exc)))
            continue
        for match in list(PLACEHOLDER_PATTERN.finditer(text))[:20]:
            line = text.count("\n", 0, match.start()) + 1
            errors.append(
                finding(
                    "UNRESOLVED_PLACEHOLDER",
                    name,
                    f"第 {line} 行仍含占位符：{match.group(0)}",
                )
            )

    soft_auto_authorized = bool(
        re.search(
            r"^\s*auto_approve_soft_gates\s*:\s*(?:true|yes|1)\s*(?:#.*)?$",
            profile_text,
            re.IGNORECASE | re.MULTILINE,
        )
    )

    state_path = project / "project-state.json"
    state: dict[str, Any] = {}
    if state_path.is_file():
        try:
            loaded_state = json.loads(state_path.read_text(encoding="utf-8"))
            if not isinstance(loaded_state, dict):
                raise ValueError("project state is not an object")
            state = loaded_state
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(finding("STATE_JSON_INVALID", state_path.name, str(exc)))
        except ValueError as exc:
            errors.append(finding("STATE_JSON_INVALID", state_path.name, str(exc)))

    gates = state.get("gates") if isinstance(state, dict) else None
    if not isinstance(gates, dict):
        errors.append(finding("GATE_SCHEMA_MISSING", state_path.name, "缺少 schema_version 2 的确认闸记录"))
    else:
        for gate_id in sorted(ALL_GATES):
            gate = gates.get(gate_id)
            if not isinstance(gate, dict):
                errors.append(finding("GATE_MISSING", state_path.name, f"缺少确认闸：{gate_id}"))
                continue
            status = str(gate.get("status", "")).strip()
            if status == "rework":
                errors.append(
                    finding("GATE_REWORK_PENDING", state_path.name, f"{gate_id} 已要求返工但尚未重新提交")
                )
            elif status != "approved":
                incomplete_gates.append(gate_id)
            else:
                approver = str(gate.get("approver", "")).strip()
                decided_at = str(gate.get("decided_at", "")).strip()
                if not approver or not DATE_PATTERN.match(decided_at):
                    incomplete_gates.append(gate_id)
                if gate_id in HARD_GATES and (
                    is_true(gate.get("auto_approved"))
                    or approver.lower() in NON_USER_APPROVERS
                ):
                    errors.append(
                        finding(
                            "HARD_GATE_SELF_APPROVED",
                            state_path.name,
                            f"{gate_id} 必须由用户批准，Agent/自动批准无效",
                        )
                    )
                if is_true(gate.get("auto_approved")) and not str(gate.get("note", "")).strip():
                    errors.append(
                        finding(
                            "SOFT_GATE_AUTO_REASON_MISSING",
                            state_path.name,
                            f"{gate_id} 自动通过但未记录授权理由",
                        )
                    )
                if is_true(gate.get("auto_approved")) and not soft_auto_authorized:
                    errors.append(
                        finding(
                            "SOFT_GATE_AUTO_UNAUTHORIZED",
                            state_path.name,
                            f"{gate_id} 自动通过，但 research-profile.yaml 未授权",
                        )
                    )

    capability_status: dict[str, str] = {}
    capability_sources: dict[str, str] = {}
    probe_path = project / "channel-probe.json"
    if probe_path.is_file():
        try:
            probe = json.loads(probe_path.read_text(encoding="utf-8"))
            capabilities = probe.get("capabilities", {})
            if not isinstance(capabilities, dict):
                raise ValueError("capabilities is not an object")
            for capability, item in capabilities.items():
                if isinstance(item, dict):
                    status = str(item.get("status", "")).strip()
                    if status not in {"available", "partial", "auth_required", "missing", "unknown"}:
                        errors.append(
                            finding(
                                "CAPABILITY_STATUS_INVALID",
                                probe_path.name,
                                f"{capability} 状态无效：{status}",
                            )
                        )
                    capability_status[str(capability)] = status
                    capability_sources[str(capability)] = str(
                        item.get("source", "")
                    ).strip()
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(finding("CHANNEL_PROBE_INVALID", probe_path.name, str(exc)))

    # —— 安装态/任务态分离（1.3.0）：通道来源、降级处置与比较法决定 ——
    decisions_path = project / "02b-channel-decisions.md"
    decisions_text = ""
    if decisions_path.is_file():
        try:
            decisions_text = decisions_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(finding("TEXT_READ_ERROR", decisions_path.name, str(exc)))

    non_unknown = [
        slot
        for slot, status in capability_status.items()
        if status not in {"", "unknown"}
    ]
    missing_source = [
        slot for slot in non_unknown if not capability_sources.get(slot)
    ]
    if missing_source:
        errors.append(
            finding(
                "CHANNEL_SOURCE_MISSING",
                probe_path.name,
                "以下能力槽状态非 unknown 但缺少 source 登记"
                "（应为 imported_from_registry 或 probe_existing 等来源标记）："
                + "、".join(sorted(missing_source)),
            )
        )

    unknown_slots = sorted(
        slot
        for slot, status in capability_status.items()
        if status in {"", "unknown"}
    )
    if unknown_slots:
        if not decisions_text:
            errors.append(
                finding(
                    "DEGRADATION_DECISION_MISSING",
                    decisions_path.name,
                    "存在 unknown 能力槽但缺少降级处置记录（02b-channel-decisions.md）",
                )
            )
        else:
            unaddressed = [
                slot for slot in unknown_slots if slot not in decisions_text
            ]
            if unaddressed:
                errors.append(
                    finding(
                        "DEGRADATION_DECISION_MISSING",
                        decisions_path.name,
                        "以下 unknown 能力槽未在降级处置表中处置："
                        + "、".join(unaddressed),
                    )
                )

    thesis_path = project / "02a-thesis-brief.md"
    if thesis_path.is_file():
        try:
            thesis_text = thesis_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(finding("TEXT_READ_ERROR", thesis_path.name, str(exc)))
            thesis_text = ""
        if "comparative_law_decision" not in thesis_text:
            errors.append(
                finding(
                    "COMPARATIVE_LAW_DECISION_MISSING",
                    thesis_path.name,
                    "02a 缺少 comparative_law_decision 字段（启用/不启用 + 用户确认）",
                )
            )
        else:
            # 只检查字段行及其紧邻续行（至空行为止），并剥离 {{占位符}}——
            # 防止模板其他章节的"请用户确认"字样廉价满足检查
            field_block = ""
            for line in thesis_text.splitlines():
                if "comparative_law_decision" in line:
                    field_block = line
                    continue
                if field_block:
                    if not line.strip():
                        break
                    field_block += "\n" + line
            resolved_block = re.sub(
                r"\{\{.*?\}\}", "", field_block, flags=re.S
            )
            if not any(
                marker in resolved_block
                for marker in ("用户确认", "用户批准", "用户决定")
            ):
                errors.append(
                    finding(
                        "COMPARATIVE_LAW_DECISION_UNCONFIRMED",
                        thesis_path.name,
                        "comparative_law_decision 未见用户确认记录——比较法是否启用须由用户拍板，"
                        "不得由 Agent 自行决定",
                    )
                )
        # 比较法不启动也必须有任务级用户确认（foreign.* 槽缺失时的合法收窄路径）
        if (
            "不启用" in thesis_text
            and capability_status.get("foreign.official_text") == "available"
        ):
            warnings.append(
                finding(
                    "COMPARATIVE_LAW_DECLINED_BUT_CHANNEL_PRESENT",
                    thesis_path.name,
                    "声明不启用比较法，但 foreign.official_text 通道可用——请核对决定是否基于过期的通道状态",
                )
            )

    decision_log_path = project / "10-decision-log.md"
    if decision_log_path.is_file():
        try:
            log_text = decision_log_path.read_text(encoding="utf-8")
        except OSError:
            log_text = ""
        if "通道导入与降级处置" not in log_text:
            warnings.append(
                finding(
                    "CHANNEL_DECISION_LOG_ROW_MISSING",
                    decision_log_path.name,
                    "决策日志建议包含『通道导入与降级处置』行（导入来源、复验结果、降级去向）",
                )
            )

    sources: dict[str, dict[str, Any]] = {}
    ledger_path = project / "03-source-ledger.jsonl"
    if ledger_path.is_file():
        try:
            lines = ledger_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            errors.append(finding("LEDGER_READ_ERROR", ledger_path.name, str(exc)))
            lines = []
        for line_number, raw_line in enumerate(lines, start=1):
            if not raw_line.strip():
                continue
            try:
                source = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                errors.append(
                    finding("LEDGER_JSON_INVALID", ledger_path.name, f"第 {line_number} 行：{exc}")
                )
                continue
            if not isinstance(source, dict):
                errors.append(
                    finding("LEDGER_ROW_INVALID", ledger_path.name, f"第 {line_number} 行不是对象")
                )
                continue
            source_id = str(source.get("source_id", "")).strip()
            if not source_id:
                errors.append(
                    finding("SOURCE_ID_MISSING", ledger_path.name, f"第 {line_number} 行缺少 source_id")
                )
                continue
            if source_id in sources:
                errors.append(
                    finding("SOURCE_ID_DUPLICATE", ledger_path.name, f"来源 ID 重复：{source_id}")
                )
                continue
            sources[source_id] = source
            for field in ("type", "title", "status", "checked_at"):
                if not str(source.get(field, "")).strip():
                    errors.append(
                        finding(
                            "SOURCE_FIELD_MISSING",
                            ledger_path.name,
                            f"来源 {source_id} 缺少字段：{field}",
                        )
                    )
            status = str(source.get("status", "")).strip()
            if status not in ALLOWED_SOURCE_STATUSES:
                errors.append(
                    finding(
                        "SOURCE_STATUS_INVALID",
                        ledger_path.name,
                        f"来源 {source_id} 状态无效：{status}",
                    )
                )
            if source_is_citable(source):
                for field in ("locator", "url_or_identifier"):
                    if not str(source.get(field, "")).strip():
                        errors.append(
                            finding(
                                "CITABLE_SOURCE_FIELD_MISSING",
                                ledger_path.name,
                                f"可引用来源 {source_id} 缺少字段：{field}",
                            )
                        )
                checked_at = str(source.get("checked_at", "")).strip()
                if not DATE_PATTERN.match(checked_at):
                    errors.append(
                        finding(
                            "SOURCE_DATE_INVALID",
                            ledger_path.name,
                            f"可引用来源 {source_id} 的 checked_at 不是 YYYY-MM-DD",
                        )
                    )
            if status == "partial_read":
                for field in ("locator", "read_scope", "source_form"):
                    if not str(source.get(field, "")).strip():
                        errors.append(
                            finding(
                                "PARTIAL_READ_SCOPE_MISSING",
                                ledger_path.name,
                                f"部分阅读来源 {source_id} 缺少字段：{field}",
                            )
                        )
        if not sources:
            errors.append(finding("SOURCE_LEDGER_EMPTY", ledger_path.name, "来源账本为空"))

    metrics["sources"] = len(sources)
    metrics["citable_sources"] = sum(source_is_citable(source) for source in sources.values())
    norm_sources = [
        source
        for source in sources.values()
        if str(source.get("type", "")) in {"statute", "regulation", "norm", "judicial_interpretation"}
        and str(source.get("status", "")) == "primary_verified"
    ]
    if sources and not norm_sources:
        errors.append(
            finding(
                "PRIMARY_NORM_MISSING",
                ledger_path.name,
                "没有达到 primary_verified 的中国规范来源",
            )
        )
    if norm_sources:
        current_official_norms = [
            source
            for source in norm_sources
            if str(source.get("authority", "")).strip().lower()
            in {"official", "official_cross_check"}
            and str(source.get("validity_status", "")).strip().lower()
            in {"current", "in_force", "现行有效"}
            and DATE_PATTERN.match(str(source.get("as_of", "")).strip())
        ]
        if not current_official_norms:
            errors.append(
                finding(
                    "CURRENT_OFFICIAL_NORM_MISSING",
                    ledger_path.name,
                    "规范来源缺少官方/官方交叉核验、现行效力状态或研究截止日记录",
                )
            )
    if sources and capability_status.get("norm.validity") != "available":
        errors.append(
            finding(
                "NORM_VALIDITY_CAPABILITY_MISSING",
                probe_path.name,
                "norm.validity 未通过真实探测，规范不得完成最终放行",
            )
        )
    academic_sources = [
        source
        for source in sources.values()
        if str(source.get("type", "")) in ACADEMIC_TYPES
        and str(source.get("status", "")) in {"partial_read", "fulltext_read"}
    ]
    if sources and not academic_sources:
        errors.append(
            finding(
                "ACADEMIC_SOURCE_MISSING",
                ledger_path.name,
                "没有达到 partial_read 或 fulltext_read 且可定位的学术来源",
            )
        )

    search_path = project / "02-search-log.csv"
    if search_path.is_file():
        search_rows = read_csv_file(
            search_path,
            ("search_id", "channel", "query", "executed_at", "limitations"),
            errors,
        )
        if not search_rows:
            errors.append(finding("SEARCH_LOG_EMPTY", search_path.name, "检索日志尚无记录"))

    claim_path = project / "05-claim-evidence.csv"
    claim_rows: list[dict[str, str]] = []
    claims_by_id: dict[str, dict[str, str]] = {}
    comparative_claim_ids: set[str] = set()
    if claim_path.is_file():
        claim_rows = read_csv_file(
            claim_path,
            (
                "claim_id",
                "proposition",
                "claim_type",
                "source_ids",
                "counter_source_ids",
                "draft_location",
                "verification_status",
                "notes",
            ),
            errors,
        )
        seen_claims: set[str] = set()
        for index, row in enumerate(claim_rows, start=2):
            claim_id = (row.get("claim_id") or "").strip()
            location = f"{claim_path.name}:第 {index} 行"
            if not claim_id:
                errors.append(finding("CLAIM_ID_MISSING", location, "缺少 claim_id"))
            elif claim_id in seen_claims:
                errors.append(finding("CLAIM_ID_DUPLICATE", location, f"命题 ID 重复：{claim_id}"))
            seen_claims.add(claim_id)
            if claim_id:
                claims_by_id[claim_id] = row
            claim_type = (row.get("claim_type") or "").strip()
            status = (row.get("verification_status") or "").strip()
            if not (row.get("proposition") or "").strip():
                errors.append(finding("CLAIM_TEXT_MISSING", location, "命题文本为空"))
            if status not in {"draft", "verified", "blocked", "withdrawn"}:
                errors.append(
                    finding(
                        "CLAIM_STATUS_INVALID",
                        location,
                        f"无效状态：{status or '空'}；若状态变成空值或章节名，通常是英文逗号造成列错位",
                    )
                )
            elif status in {"draft", "blocked"}:
                errors.append(finding("CLAIM_NOT_VERIFIED", location, f"最终项目仍含 {status} 命题"))
            if status == "verified" and not (row.get("draft_location") or "").strip():
                errors.append(finding("CLAIM_LOCATION_MISSING", location, "已核实命题缺少正文定位"))
            source_ids = split_ids(row.get("source_ids"))
            counter_ids = split_ids(row.get("counter_source_ids"))
            for field in ("source_ids", "counter_source_ids"):
                if "," in (row.get(field) or ""):
                    errors.append(
                        finding(
                            "SOURCE_IDS_COMMA",
                            location,
                            f"{field} 含英文逗号；多个 ID 必须用分号分隔",
                        )
                    )
            if status == "verified" and claim_type in EVIDENCE_REQUIRED_CLAIMS and not source_ids:
                errors.append(finding("CLAIM_EVIDENCE_MISSING", location, "该类命题必须绑定来源"))
            if status == "verified" and claim_type == "scholarly_attribution":
                academic_links = [
                    sources[source_id]
                    for source_id in source_ids
                    if source_id in sources
                    and str(sources[source_id].get("type", "")).strip() in ACADEMIC_TYPES
                ]
                if not academic_links:
                    errors.append(
                        finding(
                            "SCHOLARLY_SOURCE_TYPE_MISSING",
                            location,
                            "作者观点必须链接到已实际阅读的学术来源",
                        )
                    )
                elif capability_status.get("scholarship.fulltext") != "available" and any(
                    str(source.get("status", "")).strip() == "partial_read"
                    for source in academic_links
                ):
                    warnings.append(
                        finding(
                            "SCHOLARSHIP_PARTIAL_SCOPE",
                            location,
                            "学术全文通道未完全可用；该归属只能限于来源账本记录的已读范围",
                        )
                    )
            if status == "verified" and claim_type == "case_holding" and capability_status.get(
                "case.fulltext"
            ) != "available":
                errors.append(
                    finding(
                        "CASE_FULLTEXT_CAPABILITY_MISSING",
                        location,
                        "case.fulltext 未通过探测，不得归纳裁判理由",
                    )
                )
            if status == "verified" and claim_type == "comparative" and claim_id:
                comparative_claim_ids.add(claim_id)
            if status != "withdrawn":
                validate_linked_sources(source_ids + counter_ids, location, sources, errors)
        if not claim_rows:
            errors.append(finding("CLAIM_MATRIX_EMPTY", claim_path.name, "命题—证据矩阵为空"))
    metrics["claims"] = len(claim_rows)

    case_path = project / "04-case-matrix.csv"
    if case_path.is_file():
        case_rows = read_csv_file(
            case_path,
            (
                "case_id",
                "source_id",
                "case_name",
                "case_number",
                "court",
                "decision_date",
                "document_type",
                "authority_level",
                "procedure",
                "material_facts",
                "issue",
                "holding",
                "reasoning",
                "rule_extracted",
                "law_version",
                "subsequent_status",
                "source_url",
                "verified_at",
                "included",
                "exclusion_reason",
            ),
            errors,
        )
        for index, row in enumerate(case_rows, start=2):
            if not is_true(row.get("included")):
                if not (row.get("exclusion_reason") or "").strip():
                    errors.append(
                        finding(
                            "EXCLUDED_CASE_REASON_MISSING",
                            f"{case_path.name}:第 {index} 行",
                            "未纳入案例缺少排除理由",
                        )
                    )
                continue
            metrics["included_cases"] += 1
            location = f"{case_path.name}:第 {index} 行"
            for field in (
                "case_id",
                "source_id",
                "case_name",
                "case_number",
                "court",
                "decision_date",
                "document_type",
                "material_facts",
                "issue",
                "holding",
                "reasoning",
                "rule_extracted",
                "law_version",
                "subsequent_status",
                "verified_at",
            ):
                if not (row.get(field) or "").strip():
                    errors.append(
                        finding("INCLUDED_CASE_FIELD_MISSING", location, f"纳入案例缺少字段：{field}")
                    )
            validate_linked_sources([(row.get("source_id") or "").strip()], location, sources, errors)
            linked = sources.get((row.get("source_id") or "").strip())
            if linked and str(linked.get("type", "")) not in {"case", "official_report"}:
                errors.append(
                    finding("CASE_SOURCE_TYPE_INVALID", location, "纳入案例未链接到案例类原始来源")
                )
            if capability_status.get("case.fulltext") != "available":
                errors.append(
                    finding(
                        "CASE_FULLTEXT_CAPABILITY_MISSING",
                        location,
                        "纳入案例但 case.fulltext 未通过真实探测",
                    )
                )
            if capability_status.get("case.subsequent") != "available":
                errors.append(
                    finding(
                        "CASE_SUBSEQUENT_CAPABILITY_MISSING",
                        location,
                        "纳入案例但 case.subsequent 未通过真实探测",
                    )
                )
        if not case_rows:
            warnings.append(
                finding(
                    "CASE_MATRIX_EMPTY",
                    case_path.name,
                    "案例矩阵为空；若条款确无适用案例，应在人工签署说明不适用理由",
                )
            )

    paper_path = project / "07-paper.md"
    defined_notes: set[str] = set()
    referenced_notes: set[str] = set()
    if paper_path.is_file():
        try:
            paper = paper_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(finding("PAPER_READ_ERROR", paper_path.name, str(exc)))
            paper = ""
        paper_without_comments = re.sub(r"<!--.*?-->", "", paper, flags=re.DOTALL)
        definition_pattern = re.compile(r"^\[\^([A-Za-z0-9_-]+)\]:", re.MULTILINE)
        definitions = definition_pattern.findall(paper_without_comments)
        defined_notes = set(definitions)
        for line in paper_without_comments.splitlines():
            if definition_pattern.match(line):
                continue
            referenced_notes.update(re.findall(r"\[\^([A-Za-z0-9_-]+)\]", line))
        if len(definitions) != len(defined_notes):
            errors.append(finding("FOOTNOTE_DEFINITION_DUPLICATE", paper_path.name, "脚注定义存在重复编号"))
        for note in sorted(referenced_notes - defined_notes):
            errors.append(finding("FOOTNOTE_DEFINITION_MISSING", paper_path.name, f"脚注 {note} 无定义"))
        for note in sorted(defined_notes - referenced_notes):
            errors.append(finding("FOOTNOTE_ORPHAN", paper_path.name, f"脚注 {note} 未被正文引用"))
        metrics["footnotes"] = len(referenced_notes)
        if not referenced_notes:
            errors.append(finding("FOOTNOTES_EMPTY", paper_path.name, "成稿没有可审计脚注"))
        for required_heading in ("摘要", "关键词"):
            if required_heading not in paper:
                warnings.append(
                    finding("PAPER_SECTION_MISSING", paper_path.name, f"未发现“{required_heading}”")
                )
        visible_text = re.sub(r"[`#>*_\[\](){}\s-]", "", paper_without_comments)
        chinese_characters = len(re.findall(r"[\u3400-\u9fff]", paper_without_comments))
        target_floor = target_minimum(profile_text)
        if target_floor and chinese_characters < target_floor:
            errors.append(
                finding(
                    "PAPER_BELOW_TARGET_LENGTH",
                    paper_path.name,
                    f"正文约 {chinese_characters} 个中文字符，低于 research-profile.yaml 目标下限 {target_floor}",
                )
            )
        elif not target_floor and len(visible_text) < 8000:
            warnings.append(
                finding(
                    "PAPER_SHORT",
                    paper_path.name,
                    f"可见文本约 {len(visible_text)} 字符；请依目标期刊字数规则人工判断",
                )
            )

        # ---- 结构与口径提示（可由 quality-signoff 逐项闭合） ----
        if not re.search(r"案例(搜集|收集|检索)情况说明|案例来源说明", paper_without_comments):
            warnings.append(
                finding(
                    "CASE_COLLECTION_STATEMENT_MISSING",
                    paper_path.name,
                    "未发现案例搜集情况说明；须交代来源、检索式、截止日、命中数、剔除数与有效数",
                )
            )
        if not re.search(r"规范(性质|属性)|请求权基础规范|辅助规范|抗辩规范|不完全(主要)?规范", paper_without_comments):
            warnings.append(
                finding(
                    "NORM_ATTRIBUTE_UNDETECTED",
                    paper_path.name,
                    "未识别规范属性（请求权基础/不完全主要/辅助/抗辩/参引）",
                )
            )
        codes = [int(x) for x in re.findall(r"[［【](\d{1,3})[］】]", paper_without_comments)]
        unique_codes = sorted(set(codes))
        if unique_codes:
            gaps = [n for n in range(unique_codes[0], unique_codes[-1] + 1) if n not in unique_codes]
            if gaps:
                warnings.append(
                    finding(
                        "PARAGRAPH_CODE_GAP",
                        paper_path.name,
                        f"段码不连续，缺 {len(gaps)} 个编号（首个缺口 {gaps[0]}）",
                    )
                )
        headings = re.findall(r"^#{1,3}\s*(.+)$", paper_without_comments, re.MULTILINE)
        h1 = [h for h in headings if re.match(r"^[一二三四五六七八九十]+、", h.strip())]
        if "证明责任" in paper_without_comments and h1 and "证明责任" not in h1[-1] and "程序法" not in h1[-1]:
            warnings.append(
                finding(
                    "BURDEN_NOT_FINAL_SECTION",
                    paper_path.name,
                    f"证明责任未置于末章（当前末章：{h1[-1].strip()}）",
                )
            )
        # 评注体裁不设“结论/结语”章（SKILL.md §六 6 为硬门禁），收尾要求由证明责任承担：
        # 只有在既找不到证明责任部分、也找不到结语/结论时才提示收束缺失，且不得建议补写结论章。
        mentions_burden = "证明责任" in paper_without_comments
        if not mentions_burden and "结语" not in paper_without_comments and "结论" not in paper_without_comments:
            warnings.append(
                finding(
                    "PAPER_SECTION_MISSING",
                    paper_path.name,
                    "未见证明责任部分，全文也缺少收束；评注以证明责任作为最后一个实体部分，"
                    "不得为此另设“结论”章（无“结论”章是硬门禁，见 SKILL.md §六 6）",
                )
            )
        if re.search(r"台湾民法第|我国台湾民法第", paper_without_comments):
            warnings.append(
                finding(
                    "JURISDICTION_LABEL_AMBIGUOUS",
                    paper_path.name,
                    "台湾地区规范须标明法域与规范称谓",
                )
            )
        if "法律另有规定的" in paper_without_comments and not any("除外" in h for h in headings):
            warnings.append(
                finding(
                    "EXCEPTION_RULE_NOT_SEPARATED",
                    paper_path.name,
                    "条文含参引但书，未见独立的除外规则部分",
                )
            )
        if not re.search(r"通说|少数说|有力说|本文认为|本文主张", paper_without_comments):
            warnings.append(
                finding(
                    "NOTE_COMMENT_LAYERS_UNDETECTED",
                    paper_path.name,
                    "未见通说/少数说与本文立场的区分，无法确认注评双层",
                )
            )

    citation_path = project / "08-citation-audit.csv"
    audited_notes: set[str] = set()
    if citation_path.is_file():
        citation_rows = read_csv_file(
            citation_path,
            (
                "note_id",
                "draft_location",
                "claim_id",
                "source_ids",
                "citation_text",
                "quote_or_paraphrase",
                "citation_mode",
                "pinpoint_checked",
                "metadata_checked",
                "source_status",
                "issues",
                "resolved",
            ),
            errors,
        )
        metrics["citation_audit_rows"] = len(citation_rows)
        for index, row in enumerate(citation_rows, start=2):
            note_id = (row.get("note_id") or "").strip().removeprefix("^")
            location = f"{citation_path.name}:第 {index} 行"
            if not note_id:
                errors.append(finding("CITATION_NOTE_ID_MISSING", location, "缺少 note_id"))
                continue
            if note_id in audited_notes:
                errors.append(finding("CITATION_NOTE_DUPLICATE", location, f"重复审计脚注：{note_id}"))
            audited_notes.add(note_id)
            for field in (
                "draft_location",
                "claim_id",
                "source_ids",
                "citation_text",
                "citation_mode",
                "source_status",
            ):
                if not (row.get(field) or "").strip():
                    errors.append(finding("CITATION_FIELD_MISSING", location, f"缺少字段：{field}"))
            for field in ("claim_id", "source_ids"):
                if "," in (row.get(field) or ""):
                    errors.append(
                        finding(
                            "SOURCE_IDS_COMMA" if field == "source_ids" else "CLAIM_IDS_COMMA",
                            location,
                            f"{field} 含英文逗号；多个 ID 必须用分号分隔",
                        )
                    )
            validate_linked_sources(split_ids(row.get("source_ids")), location, sources, errors)
            citation_claim_ids = split_ids(row.get("claim_id"))
            for claim_id in citation_claim_ids:
                claim = claims_by_id.get(claim_id)
                if claim is None:
                    errors.append(
                        finding("CITATION_CLAIM_MISSING", location, f"脚注未链接到有效命题：{claim_id}")
                    )
                elif (claim.get("verification_status") or "").strip() != "verified":
                    errors.append(
                        finding("CITATION_CLAIM_NOT_VERIFIED", location, f"脚注所连命题尚未核实：{claim_id}")
                    )
            if (
                comparative_claim_ids.intersection(citation_claim_ids)
                and capability_status.get("foreign.official_text") != "available"
            ):
                if (row.get("citation_mode") or "").strip() != "secondary_citation" or "转引自" not in (
                    row.get("citation_text") or ""
                ):
                    errors.append(
                        finding(
                            "COMPARATIVE_SECONDARY_CITATION_UNMARKED",
                            location,
                            "未取得外国官方原文时，比较法脚注必须标 citation_mode=secondary_citation 并写明“转引自”",
                        )
                    )
            for field in ("pinpoint_checked", "metadata_checked", "resolved"):
                if not is_true(row.get(field)):
                    errors.append(finding("CITATION_CHECK_INCOMPLETE", location, f"{field} 尚未完成"))
        for note in sorted(referenced_notes - audited_notes):
            errors.append(finding("FOOTNOTE_NOT_AUDITED", citation_path.name, f"脚注 {note} 未进入引注审计表"))
        for note in sorted(audited_notes - defined_notes):
            errors.append(finding("AUDIT_NOTE_NOT_IN_PAPER", citation_path.name, f"审计表脚注 {note} 不在成稿中"))

    signoff_path = project / "quality-signoff.json"
    signoffs: dict[str, Any] = {}
    if signoff_path.is_file():
        try:
            signoffs = json.loads(signoff_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(finding("SIGNOFF_JSON_INVALID", signoff_path.name, str(exc)))
            signoffs = {}
        if not isinstance(signoffs, dict):
            errors.append(finding("SIGNOFF_FORMAT_INVALID", signoff_path.name, "签署文件不是 JSON 对象"))
            signoffs = {}
        for key in SIGNOFF_KEYS:
            item = signoffs.get(key)
            if not isinstance(item, dict):
                incomplete_signoffs.append(key)
                continue
            checked_at = str(item.get("checked_at", "")).strip()
            if (
                not is_true(item.get("complete"))
                or not str(item.get("reviewer", "")).strip()
                or not DATE_PATTERN.match(checked_at)
                or not str(item.get("notes", "")).strip()
            ):
                incomplete_signoffs.append(key)

        pdf_expected = any(project.glob("*.pdf"))
        if (
            pdf_expected
            and is_true(signoffs.get("layout_rendered", {}).get("complete"))
            and capability_status.get("export.pdf_render") != "available"
        ):
            errors.append(
                finding(
                    "LAYOUT_SIGNOFF_WITHOUT_RENDERER",
                    signoff_path.name,
                    "项目含 PDF 交付但 export.pdf_render 未通过探测，layout_rendered 不得签署",
                )
            )

    if comparative_claim_ids:
        comparative_path = project / "11-comparative-memo.md"
        if comparative_path.is_file():
            try:
                memo = comparative_path.read_text(encoding="utf-8")
            except OSError as exc:
                errors.append(finding("COMPARATIVE_MEMO_READ_ERROR", comparative_path.name, str(exc)))
                memo = ""
            for heading in ("法域选择理由", "可移植性", "反向校验"):
                if heading not in memo:
                    errors.append(
                        finding(
                            "COMPARATIVE_MEMO_SECTION_MISSING",
                            comparative_path.name,
                            f"启用比较法但缺少“{heading}”记录",
                        )
                    )

    return finalize(project, errors, warnings, incomplete_signoffs, incomplete_gates, metrics)


def finalize(
    project: Path,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
    incomplete_signoffs: list[str],
    incomplete_gates: list[str],
    metrics: dict[str, int],
) -> dict[str, Any]:
    if errors:
        verdict = "BLOCKED"
    elif incomplete_signoffs or incomplete_gates:
        verdict = "REVIEW_REQUIRED"
    else:
        verdict = "READY_FOR_SUBMISSION"
    return {
        "schema_version": 1,
        "project": str(project),
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "verdict": verdict,
        "errors": errors,
        "warnings": warnings,
        "incomplete_signoffs": sorted(set(incomplete_signoffs)),
        "incomplete_gates": sorted(set(incomplete_gates)),
        "metrics": metrics,
        "disclaimer": "该结论只表示通过本项目的技术门禁，不保证学术质量、同行评审或期刊录用。",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 法律评注质量报告",
        "",
        f"- 放行状态：`{report['verdict']}`",
        f"- 生成时间：{report['generated_at']}",
        f"- 项目目录：`{report['project']}`",
        "",
        "## 结构化统计",
        "",
    ]
    labels = {
        "sources": "来源总数",
        "citable_sources": "可引用来源",
        "claims": "命题数",
        "included_cases": "纳入案例",
        "footnotes": "正文脚注",
        "citation_audit_rows": "引注审计记录",
    }
    for key, value in report["metrics"].items():
        lines.append(f"- {labels.get(key, key)}：{value}")

    lines.extend(["", "## 阻断项", ""])
    if report["errors"]:
        for item in report["errors"]:
            lines.append(f"- `{item['code']}` · `{item['file']}`：{item['message']}")
    else:
        lines.append("- 无")

    lines.extend(["", "## 警告", ""])
    if report["warnings"]:
        for item in report["warnings"]:
            lines.append(f"- `{item['code']}` · `{item['file']}`：{item['message']}")
    else:
        lines.append("- 无")

    lines.extend(["", "## 未完成人工签署", ""])
    if report["incomplete_signoffs"]:
        for key in report["incomplete_signoffs"]:
            lines.append(f"- `{key}`")
    else:
        lines.append("- 无")

    lines.extend(["", "## 未通过确认闸", ""])
    if report["incomplete_gates"]:
        for key in report["incomplete_gates"]:
            lines.append(f"- `{key}`")
    else:
        lines.append("- 无")

    lines.extend(
        [
            "",
            "## 结论边界",
            "",
            report["disclaimer"],
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit a law-commentary project release gate.")
    parser.add_argument("project", help="Project directory")
    parser.add_argument("--output", help="Write the Markdown report to this path")
    parser.add_argument("--json", action="store_true", help="Print the full JSON report")
    parser.add_argument("--lint", action="store_true", help="Only report file/JSON/CSV/placeholder format errors")
    parser.add_argument("--list-citable", action="store_true", help="List sources currently eligible for citation")
    return parser


def lint_only(report: dict[str, Any]) -> dict[str, Any]:
    prefixes = (
        "REQUIRED_FILE_",
        "UNRESOLVED_",
        "CSV_",
        "SOURCE_IDS_COMMA",
        "CLAIM_IDS_COMMA",
        "STATE_JSON_",
        "CHANNEL_PROBE_",
        "LEDGER_JSON_",
        "SIGNOFF_JSON_",
    )
    errors = [item for item in report["errors"] if item["code"].startswith(prefixes)]
    lint_report = dict(report)
    lint_report["errors"] = errors
    lint_report["warnings"] = []
    lint_report["incomplete_signoffs"] = []
    lint_report["incomplete_gates"] = []
    lint_report["verdict"] = "BLOCKED" if errors else "LINT_OK"
    lint_report["disclaimer"] = "格式预检通过不表示证据、论证、确认闸或投稿质量已经通过。"
    return lint_report


def print_citable_sources(project: Path) -> int:
    ledger = project.expanduser().resolve() / "03-source-ledger.jsonl"
    try:
        lines = ledger.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    count = 0
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            source = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"error: ledger line {line_number}: {exc}", file=sys.stderr)
            return 2
        if isinstance(source, dict) and source_is_citable(source):
            count += 1
            print(
                f"{source.get('source_id', '')}\t{source.get('status', '')}\t"
                f"{source.get('title', '')}\t{source.get('locator', '')}"
            )
    if not count:
        print("No citable sources.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_citable:
        return print_citable_sources(Path(args.project))
    report = audit_project(Path(args.project))
    if args.lint:
        report = lint_only(report)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"{report['verdict']}: {len(report['errors'])} error(s), "
            f"{len(report['warnings'])} warning(s), "
            f"{len(report['incomplete_signoffs'])} incomplete sign-off(s), "
            f"{len(report['incomplete_gates'])} incomplete gate(s)"
        )
        if args.output:
            print(f"Report written to {Path(args.output).expanduser().resolve()}")
    return {
        "READY_FOR_SUBMISSION": 0,
        "LINT_OK": 0,
        "REVIEW_REQUIRED": 1,
        "BLOCKED": 2,
    }[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
