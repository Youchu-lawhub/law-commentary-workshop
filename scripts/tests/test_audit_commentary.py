from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from audit_commentary import SIGNOFF_KEYS, audit_project  # noqa: E402
from gate import main as gate_main  # noqa: E402
from new_commentary_project import initialize_project  # noqa: E402
from render_check import validate_docx  # noqa: E402
from scan_corpus import scan  # noqa: E402


class CommentaryAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name) / "project"
        initialize_project(
            output=self.project,
            law_title="中华人民共和国民法典",
            article="第七条",
            as_of="2026-09-09",
            target_journal="测试期刊",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_csv(self, name: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        with (self.project / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def make_ready_fixture(self) -> None:
        (self.project / "research-profile.yaml").write_text(
            "schema_version: 1\nproject:\n  law_title: 民法典\n  article: 第七条\n",
            encoding="utf-8",
        )
        (self.project / "01-norm-dossier.md").write_text(
            "# 规范档案\n\n现行文本、效力和规范网络均已核验。\n",
            encoding="utf-8",
        )
        (self.project / "06-outline.md").write_text(
            "# 论证提纲\n\n核心问题、反方论证和适用边界均已列明。\n",
            encoding="utf-8",
        )
        (self.project / "02a-thesis-brief.md").write_text(
            "# 中心命题简报\n\n"
            "comparative_law_decision: 不启用——用户确认本条评注限于国内法解释论，"
            "不使用境外规范/判例/文献对照。\n",
            encoding="utf-8",
        )
        (self.project / "02b-channel-decisions.md").write_text(
            "# 降级处置表\n\n全部能力槽均为 available，无 unknown 槽；"
            "通道经 probe_existing 实测复验。\n",
            encoding="utf-8",
        )
        (self.project / "10-decision-log.md").write_text(
            "# 决策日志\n\n"
            "| 日期 | 决策 | 理由 |\n|---|---|---|\n"
            "| 2026-09-09 | 通道导入与降级处置 | 注册表导入 13 槽，全部复验 available，无降级 |\n",
            encoding="utf-8",
        )
        for name in (
            "01a-norm-brief.md",
            "03a-research-brief.md",
            "04a-evidence-brief.md",
            "06a-outline-brief.md",
            "07a-draft-brief.md",
            "09a-delivery-brief.md",
            "12-contribution-review.md",
            "13-scholarly-review.md",
        ):
            (self.project / name).write_text(
                f"# {name}\n\n本阶段已完成，关键发现、备选方案和用户决定均已记录。\n",
                encoding="utf-8",
            )
        (self.project / "11-comparative-memo.md").write_text(
            "# 比较法备忘录\n\n本项目未启用比较法；原因、边界与反向校验均已记录。\n",
            encoding="utf-8",
        )
        (self.project / "07-paper.md").write_text(
            "# 民法典第七条评注\n\n"
            "## 摘要\n\n本文讨论诚信原则的规范功能。\n\n"
            "**关键词：** 诚信原则；一般条款\n\n"
            "## 一、问题的提出\n\n现行条文确立诚信原则。[^1]\n\n"
            "## 二、解释\n\n既有研究提出了具体化路径。[^2]\n\n"
            "## 结语\n\n本文结论仅适用于已说明的规范语境。\n\n"
            "[^1]: 《中华人民共和国民法典》第7条。\n"
            "[^2]: 测试作者：《测试论文》，载《测试期刊》2025年第1期，第10页。\n",
            encoding="utf-8",
        )

        sources = [
            {
                "source_id": "S001",
                "type": "statute",
                "title": "中华人民共和国民法典",
                "status": "primary_verified",
                "checked_at": "2026-09-09",
                "locator": "第七条",
                "url_or_identifier": "https://example.invalid/statute",
                "authority": "official",
                "validity_status": "current",
                "as_of": "2026-09-09",
            },
            {
                "source_id": "S002",
                "type": "article",
                "title": "测试论文",
                "status": "fulltext_read",
                "checked_at": "2026-09-09",
                "locator": "第10页",
                "url_or_identifier": "doi:10.0000/example",
            },
        ]
        (self.project / "03-source-ledger.jsonl").write_text(
            "\n".join(json.dumps(source, ensure_ascii=False) for source in sources) + "\n",
            encoding="utf-8",
        )
        probe = json.loads((self.project / "channel-probe.json").read_text(encoding="utf-8"))
        for item in probe["capabilities"].values():
            item.update(
                {
                    "status": "available",
                    "tool": "test-tool",
                    "source": "probe_existing",
                    "probe_case": "test",
                    "probe_assert": "passed",
                    "probe_ok": True,
                }
            )
        (self.project / "channel-probe.json").write_text(
            json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        state_path = self.project / "project-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        for gate in state["gates"].values():
            gate.update(
                {
                    "status": "approved",
                    "approver": "测试用户",
                    "decided_at": "2026-09-10",
                    "decision": "approved",
                    "note": "用户确认",
                    "auto_approved": False,
                }
            )
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        self.write_csv(
            "02-search-log.csv",
            [
                "search_id",
                "channel",
                "capability",
                "query",
                "filters",
                "date_range",
                "result_count",
                "pages_reviewed",
                "source_ids_added",
                "access_level",
                "executed_at",
                "limitations",
            ],
            [
                {
                    "search_id": "Q001",
                    "channel": "official",
                    "capability": "norm",
                    "query": "民法典 第七条",
                    "executed_at": "2026-09-09",
                    "limitations": "none",
                }
            ],
        )
        self.write_csv(
            "05-claim-evidence.csv",
            [
                "claim_id",
                "proposition",
                "claim_type",
                "source_ids",
                "counter_source_ids",
                "draft_location",
                "verification_status",
                "notes",
            ],
            [
                {
                    "claim_id": "C001",
                    "proposition": "第七条确立诚信原则",
                    "claim_type": "norm_text",
                    "source_ids": "S001",
                    "counter_source_ids": "",
                    "draft_location": "一",
                    "verification_status": "verified",
                    "notes": "",
                },
                {
                    "claim_id": "C002",
                    "proposition": "既有研究讨论具体化路径",
                    "claim_type": "scholarly_attribution",
                    "source_ids": "S002",
                    "counter_source_ids": "",
                    "draft_location": "二",
                    "verification_status": "verified",
                    "notes": "",
                },
            ],
        )
        self.write_csv(
            "08-citation-audit.csv",
            [
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
            ],
            [
                {
                    "note_id": "1",
                    "draft_location": "一",
                    "claim_id": "C001",
                    "source_ids": "S001",
                    "citation_text": "民法典第七条",
                    "quote_or_paraphrase": "paraphrase",
                    "citation_mode": "direct_source",
                    "pinpoint_checked": "true",
                    "metadata_checked": "true",
                    "source_status": "primary_verified",
                    "issues": "",
                    "resolved": "true",
                },
                {
                    "note_id": "2",
                    "draft_location": "二",
                    "claim_id": "C002",
                    "source_ids": "S002",
                    "citation_text": "测试论文，第10页",
                    "quote_or_paraphrase": "paraphrase",
                    "citation_mode": "direct_source",
                    "pinpoint_checked": "true",
                    "metadata_checked": "true",
                    "source_status": "fulltext_read",
                    "issues": "",
                    "resolved": "true",
                },
            ],
        )
        signoffs = {"schema_version": 1}
        for key in SIGNOFF_KEYS:
            signoffs[key] = {
                "complete": True,
                "reviewer": "测试审校者",
                "checked_at": "2026-09-09",
                "notes": "已按测试夹具核验",
            }
        (self.project / "quality-signoff.json").write_text(
            json.dumps(signoffs, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def test_fresh_project_is_blocked(self) -> None:
        report = audit_project(self.project)
        self.assertEqual(report["verdict"], "BLOCKED")
        self.assertTrue(report["errors"])

    def test_complete_fixture_is_ready(self) -> None:
        self.make_ready_fixture()
        report = audit_project(self.project)
        self.assertEqual(report["verdict"], "READY_FOR_SUBMISSION")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["incomplete_signoffs"], [])

    def test_incomplete_human_gate_requires_review(self) -> None:
        self.make_ready_fixture()
        path = self.project / "quality-signoff.json"
        signoffs = json.loads(path.read_text(encoding="utf-8"))
        signoffs["layout_rendered"]["complete"] = False
        path.write_text(json.dumps(signoffs, ensure_ascii=False), encoding="utf-8")
        report = audit_project(self.project)
        self.assertEqual(report["verdict"], "REVIEW_REQUIRED")
        self.assertIn("layout_rendered", report["incomplete_signoffs"])

    def test_broken_footnote_chain_is_blocked(self) -> None:
        self.make_ready_fixture()
        path = self.project / "07-paper.md"
        paper = path.read_text(encoding="utf-8")
        paper = paper.replace(
            "[^2]: 测试作者：《测试论文》，载《测试期刊》2025年第1期，第10页。\n",
            "",
        )
        path.write_text(paper, encoding="utf-8")
        report = audit_project(self.project)
        self.assertEqual(report["verdict"], "BLOCKED")
        self.assertIn("FOOTNOTE_DEFINITION_MISSING", {item["code"] for item in report["errors"]})

    def test_initializer_refuses_nonempty_destination(self) -> None:
        with self.assertRaises(FileExistsError):
            initialize_project(
                output=self.project,
                law_title="中华人民共和国民法典",
                article="第八条",
                as_of="2026-09-09",
            )

    def test_initializer_rejects_invalid_date(self) -> None:
        with self.assertRaises(ValueError):
            initialize_project(
                output=Path(self.temporary.name) / "invalid-date",
                law_title="中华人民共和国民法典",
                article="第八条",
                as_of="2026-02-30",
            )

    def test_unapproved_research_gate_requires_review(self) -> None:
        self.make_ready_fixture()
        path = self.project / "project-state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["gates"]["G2_research"].update(
            {"status": "awaiting", "approver": "", "decided_at": "", "decision": ""}
        )
        path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        report = audit_project(self.project)
        self.assertEqual(report["verdict"], "REVIEW_REQUIRED")
        self.assertIn("G2_research", report["incomplete_gates"])

    def test_agent_cannot_approve_hard_gate(self) -> None:
        self.make_ready_fixture()
        path = self.project / "project-state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["gates"]["G3_outline"].update(
            {"approver": "agent", "auto_approved": True, "note": "self approved"}
        )
        path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        report = audit_project(self.project)
        self.assertEqual(report["verdict"], "BLOCKED")
        self.assertIn("HARD_GATE_SELF_APPROVED", {item["code"] for item in report["errors"]})

    def run_gate(self, *args: str) -> tuple[int, str, str]:
        """运行 gate.py 主流程并回收其输出，避免闸门文案污染 unittest 报告。"""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gate_main([str(self.project), *args])
        return code, out.getvalue(), err.getvalue()

    def test_auto_approve_rejected_for_hard_gate(self) -> None:
        # 合并后四闸全部为 hard，任何自动通过都应被拒绝并保持 pending。
        code, _, stderr = self.run_gate(
            "--auto-approve",
            "G1_topic",
            "--by",
            "agent",
            "--reason",
            "测试自动通过",
        )
        self.assertEqual(code, 2)
        self.assertIn("hard gate", stderr)
        state = json.loads((self.project / "project-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["gates"]["G1_topic"]["status"], "pending")

    def test_gate_rework_rolls_back_later_work(self) -> None:
        self.make_ready_fixture()
        code, stdout, _ = self.run_gate(
            "--rework", "G3_outline", "--by", "user", "--reason", "结构重复"
        )
        self.assertEqual(code, 0)
        self.assertIn("G3_outline: rework; resume from outline_approved", stdout)
        state = json.loads((self.project / "project-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["current_stage"], "outline_approved")
        self.assertEqual(state["gates"]["G3_outline"]["status"], "rework")
        self.assertEqual(state["gates"]["G4_final"]["status"], "pending")

    def test_comma_separated_source_ids_get_specific_error(self) -> None:
        self.make_ready_fixture()
        path = self.project / "05-claim-evidence.csv"
        with path.open("r", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        rows[0]["source_ids"] = "S001,S002"
        self.write_csv("05-claim-evidence.csv", list(rows[0]), rows)
        report = audit_project(self.project)
        self.assertIn("SOURCE_IDS_COMMA", {item["code"] for item in report["errors"]})

    def test_partial_read_requires_scope(self) -> None:
        self.make_ready_fixture()
        path = self.project / "03-source-ledger.jsonl"
        sources = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        sources[1]["status"] = "partial_read"
        path.write_text(
            "\n".join(json.dumps(source, ensure_ascii=False) for source in sources) + "\n",
            encoding="utf-8",
        )
        report = audit_project(self.project)
        self.assertIn("PARTIAL_READ_SCOPE_MISSING", {item["code"] for item in report["errors"]})

    def test_comparative_secondary_citation_must_be_disclosed(self) -> None:
        self.make_ready_fixture()
        claim_path = self.project / "05-claim-evidence.csv"
        with claim_path.open("r", encoding="utf-8") as handle:
            claims = list(csv.DictReader(handle))
        claims[1]["claim_type"] = "comparative"
        self.write_csv("05-claim-evidence.csv", list(claims[0]), claims)

        probe_path = self.project / "channel-probe.json"
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
        probe["capabilities"]["foreign.official_text"]["status"] = "missing"
        probe_path.write_text(json.dumps(probe, ensure_ascii=False), encoding="utf-8")

        report = audit_project(self.project)
        self.assertIn(
            "COMPARATIVE_SECONDARY_CITATION_UNMARKED",
            {item["code"] for item in report["errors"]},
        )

    def test_reference_docx_contract_and_anonymity(self) -> None:
        template = SCRIPTS_DIR.parent / "assets" / "templates" / "journal-cn.docx"
        self.assertEqual(validate_docx(template, anonymous=True), [])

    def test_local_corpus_index_does_not_claim_full_reading(self) -> None:
        corpus = Path(self.temporary.name) / "corpus"
        corpus.mkdir()
        (corpus / "资料.md").write_text("一份用于索引的本地研究资料。", encoding="utf-8")
        rows = scan([corpus], max_bytes=1024 * 1024, preview_chars=50)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["index_status"], "text_indexed")
        self.assertEqual(rows[0]["preview"], "一份用于索引的本地研究资料。")
        self.assertEqual(len(rows[0]["sha256"]), 64)

    def test_empty_and_unreadable_corpus_files_surface_in_rows(self) -> None:
        """空文件与读不到的文件都必须在索引里显式露出，不得被静默跳过。"""
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("running as root: permission bits do not block reads")
        corpus = Path(self.temporary.name) / "mixed-corpus"
        corpus.mkdir()
        (corpus / "empty.md").write_text("", encoding="utf-8")
        (corpus / "readable.md").write_text("可读资料", encoding="utf-8")
        blocked = corpus / "blocked.md"
        blocked.write_text("不可读资料", encoding="utf-8")
        blocked.chmod(0o000)
        try:
            rows = {
                Path(row["relative_path"]).name: row
                for row in scan([corpus], max_bytes=1024 * 1024, preview_chars=50)
            }
        finally:
            blocked.chmod(0o644)
        self.assertEqual(sorted(rows), ["blocked.md", "empty.md", "readable.md"])
        self.assertEqual(rows["readable.md"]["index_status"], "text_indexed")
        self.assertEqual(rows["empty.md"]["index_status"], "metadata_only")
        self.assertEqual(rows["empty.md"]["preview"], "")
        self.assertEqual(rows["blocked.md"]["index_status"], "read_error")
        self.assertIn("blocked.md", rows["blocked.md"]["error"])


if __name__ == "__main__":
    unittest.main()
