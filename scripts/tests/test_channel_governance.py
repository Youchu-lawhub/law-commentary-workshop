"""Tests for 1.3.0 channel-governance audit checks and registry integration.

安装态/任务态分离的强制点：
- CHANNEL_SOURCE_MISSING：非 unknown 槽必须登记来源
- DEGRADATION_DECISION_MISSING：unknown 槽必须有 02b 处置记录
- COMPARATIVE_LAW_DECISION_MISSING / _UNCONFIRMED：比较法决定须用户拍板
- registry import → source=imported_from_registry → 审计通过 source 检查
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from audit_commentary import audit_project  # noqa: E402
from new_commentary_project import initialize_project  # noqa: E402

_reg_spec = importlib.util.spec_from_file_location(
    "channel_registry", SCRIPTS_DIR / "channel_registry.py"
)
channel_registry = importlib.util.module_from_spec(_reg_spec)
sys.modules["channel_registry"] = channel_registry
_reg_spec.loader.exec_module(channel_registry)  # type: ignore[union-attr]


def error_codes(report: dict) -> set[str]:
    return {e["code"] for e in report["errors"]}


class ChannelGovernanceAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        initialize_project(
            output=self.project,
            law_title="中华人民共和国民法典",
            article="第七条",
            as_of="2026-09-09",
            target_journal="测试期刊",
        )

    def set_slot(self, slot: str, **fields) -> None:
        probe_path = self.project / "channel-probe.json"
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
        probe["capabilities"][slot].update(fields)
        probe_path.write_text(
            json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def write_02a(self, text: str) -> None:
        (self.project / "02a-thesis-brief.md").write_text(text, encoding="utf-8")

    def test_fresh_template_fires_unconfirmed_comparative_law(self) -> None:
        report = audit_project(self.project)
        codes = error_codes(report)
        # 模板 02a 有字段但无用户确认——这正是要堵住的"Agent 代为决定"路径
        self.assertIn("COMPARATIVE_LAW_DECISION_UNCONFIRMED", codes)
        # 模板 02b 覆盖全部槽位 → unknown 槽处置检查应通过
        self.assertNotIn("DEGRADATION_DECISION_MISSING", codes)
        self.assertNotIn("CHANNEL_SOURCE_MISSING", codes)

    def test_available_slot_without_source_is_blocked(self) -> None:
        self.set_slot("scholarship.search", status="available", tool="x")
        self.write_02a("comparative_law_decision: 不启用——用户确认。")
        report = audit_project(self.project)
        self.assertIn("CHANNEL_SOURCE_MISSING", error_codes(report))

    def test_unknown_slot_missing_from_02b_is_blocked(self) -> None:
        path = self.project / "02b-channel-decisions.md"
        text = path.read_text(encoding="utf-8").replace("norm.validity", "")
        path.write_text(text, encoding="utf-8")
        self.write_02a("comparative_law_decision: 不启用——用户确认。")
        report = audit_project(self.project)
        codes = error_codes(report)
        self.assertIn("DEGRADATION_DECISION_MISSING", codes)
        joined = " ".join(
            e["message"] for e in report["errors"]
            if e["code"] == "DEGRADATION_DECISION_MISSING"
        )
        self.assertIn("norm.validity", joined)

    def test_comparative_law_decision_missing(self) -> None:
        self.write_02a("# 中心命题简报\n\n没有任何比较法字段。")
        report = audit_project(self.project)
        self.assertIn(
            "COMPARATIVE_LAW_DECISION_MISSING", error_codes(report)
        )

    def test_confirmed_decision_passes(self) -> None:
        self.write_02a("comparative_law_decision: 启用——用户确认需要德国法对照。")
        report = audit_project(self.project)
        codes = error_codes(report)
        self.assertNotIn("COMPARATIVE_LAW_DECISION_MISSING", codes)
        self.assertNotIn("COMPARATIVE_LAW_DECISION_UNCONFIRMED", codes)

    def test_registry_import_satisfies_source_check(self) -> None:
        registry = self.root / "channel-registry.json"
        code, _ = self._cli("init", "--registry-path", str(registry))
        self.assertEqual(code, 0)
        code, _ = self._cli(
            "ack", "--by", "测试用户", "--registry-path", str(registry)
        )
        self.assertEqual(code, 0)
        data = json.loads(registry.read_text(encoding="utf-8"))
        data["channels"]["norm.exact_article"] = {
            "name": "yuandian",
            "status": "available",
            "tool": "yuandian.get_article",
            "accepted_at": "2026-09-09",
            "acceptance": "取第7条逐字命中",
        }
        registry.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        code, payload = self._cli(
            "import", "--project", str(self.project), "--registry-path", str(registry)
        )
        self.assertEqual(code, 0)

        probe = json.loads(
            (self.project / "channel-probe.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            probe["capabilities"]["norm.exact_article"]["source"],
            "imported_from_registry",
        )
        self.write_02a("comparative_law_decision: 不启用——用户确认。")
        report = audit_project(self.project)
        self.assertNotIn("CHANNEL_SOURCE_MISSING", error_codes(report))

    def _cli(self, *argv: str) -> tuple[int, dict]:
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = channel_registry.main(list(argv))
        text = buffer.getvalue().strip()
        try:
            return code, json.loads(text) if text else {}
        except json.JSONDecodeError:
            return code, {"raw": text}

    def test_unacked_registry_refuses_import(self) -> None:
        registry = self.root / "channel-registry.json"
        self._cli("init", "--registry-path", str(registry))
        code, payload = self._cli(
            "import", "--project", str(self.project), "--registry-path", str(registry)
        )
        self.assertEqual(code, 3)
        self.assertEqual(payload["error"], "INTERVIEW_NOT_ACKED")
        # 未导入 → 项目 probe 保持 unknown → source 检查不应误报
        report = audit_project(self.project)
        self.assertNotIn("CHANNEL_SOURCE_MISSING", error_codes(report))


if __name__ == "__main__":
    unittest.main()
