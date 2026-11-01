"""Tests for scripts/channel_registry.py — installation-state registry."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import importlib.util
import sys

SCRIPTS = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "channel_registry", SCRIPTS / "channel_registry.py"
)
channel_registry = importlib.util.module_from_spec(_spec)
sys.modules["channel_registry"] = channel_registry
_spec.loader.exec_module(channel_registry)  # type: ignore[union-attr]


class ChannelRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.registry = self.root / "channel-registry.json"
        self.project = self.root / "proj"
        self.project.mkdir()
        probe = {
            "schema_version": 1,
            "checked_at": "2026-11-01",
            "capabilities": {
                "scholarship.search": {"status": "unknown", "tool": ""},
                "norm.exact_article": {"status": "unknown", "tool": ""},
                "foreign.case": {"status": "unknown", "tool": ""},
            },
        }
        (self.project / "channel-probe.json").write_text(
            json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def run_cli(self, *argv: str) -> tuple[int, dict]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = channel_registry.main(list(argv))
        text = buffer.getvalue().strip()
        try:
            payload = json.loads(text) if text else {}
        except json.JSONDecodeError:
            payload = {"raw": text}
        return code, payload

    def test_init_then_ack_then_import_marks_source(self) -> None:
        code, payload = self.run_cli("init", "--registry-path", str(self.registry))
        self.assertEqual(code, 0)
        code, payload = self.run_cli(
            "ack", "--by", "测试用户", "--registry-path", str(self.registry)
        )
        self.assertEqual(code, 0)

        # 手工登记一条已验收通道（模拟安装访谈后由 Agent 写入）
        data = json.loads(self.registry.read_text(encoding="utf-8"))
        data["channels"]["scholarship.search"] = {
            "name": "wanfang",
            "status": "available",
            "tool": "wanfang.search",
            "accepted_at": "2026-11-01",
            "acceptance": "PQ 检索式返回真实题录",
        }
        self.registry.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        code, payload = self.run_cli(
            "import", "--project", str(self.project), "--registry-path", str(self.registry)
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["imported_slots"], ["scholarship.search"])
        self.assertIn("norm.exact_article", payload["uncovered_slots"])

        probe = json.loads(
            (self.project / "channel-probe.json").read_text(encoding="utf-8")
        )
        slot = probe["capabilities"]["scholarship.search"]
        self.assertEqual(slot["status"], "available")
        self.assertEqual(slot["source"], "imported_from_registry")
        self.assertTrue(slot["registry_ref"].endswith("#scholarship.search"))
        self.assertEqual(
            probe["registry_import"]["interview_confirmed_by"], "测试用户"
        )
        # 未覆盖槽保持 unknown —— 任务态降级处置的责任范围
        self.assertEqual(probe["capabilities"]["norm.exact_article"]["status"], "unknown")

    def test_import_refused_without_interview_ack(self) -> None:
        code, _ = self.run_cli("init", "--registry-path", str(self.registry))
        self.assertEqual(code, 0)
        code, payload = self.run_cli(
            "import", "--project", str(self.project), "--registry-path", str(self.registry)
        )
        self.assertEqual(code, 3)
        self.assertEqual(payload["error"], "INTERVIEW_NOT_ACKED")

    def test_import_refused_without_registry(self) -> None:
        code, payload = self.run_cli(
            "import", "--project", str(self.project), "--registry-path", str(self.registry)
        )
        self.assertEqual(code, 3)
        self.assertEqual(payload["error"], "REGISTRY_MISSING")

    def test_init_refuses_overwrite_without_force(self) -> None:
        code, _ = self.run_cli("init", "--registry-path", str(self.registry))
        self.assertEqual(code, 0)
        code, payload = self.run_cli("init", "--registry-path", str(self.registry))
        self.assertEqual(code, 2)
        self.assertEqual(payload["error"], "REGISTRY_EXISTS")
        code, _ = self.run_cli(
            "init", "--registry-path", str(self.registry), "--force"
        )
        self.assertEqual(code, 0)

    def test_project_without_probe_is_refused(self) -> None:
        code, _ = self.run_cli("init", "--registry-path", str(self.registry))
        code, _ = self.run_cli(
            "ack", "--by", "测试用户", "--registry-path", str(self.registry)
        )
        empty = self.root / "empty-project"
        empty.mkdir()
        code, payload = self.run_cli(
            "import", "--project", str(empty), "--registry-path", str(self.registry)
        )
        self.assertEqual(code, 2)
        self.assertEqual(payload["error"], "PROJECT_PROBE_MISSING")

    def test_status_reports_by_status_groups(self) -> None:
        code, _ = self.run_cli("init", "--registry-path", str(self.registry))
        code, _ = self.run_cli(
            "ack", "--by", "测试用户", "--registry-path", str(self.registry)
        )
        data = json.loads(self.registry.read_text(encoding="utf-8"))
        data["channels"]["norm.exact_article"] = {
            "name": "yuandian",
            "status": "available",
        }
        self.registry.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        code, payload = self.run_cli("status", "--registry-path", str(self.registry))
        self.assertEqual(code, 0)
        self.assertEqual(payload["channels_total"], 1)
        self.assertEqual(payload["by_status"]["available"], ["norm.exact_article"])
        self.assertEqual(payload["interview_confirmed_by"], "测试用户")


if __name__ == "__main__":
    unittest.main()
