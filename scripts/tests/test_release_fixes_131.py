"""1.3.1 发布修复的回归测试（scripts/ 侧）。

覆盖发布说明中已由所有者修复的四项行为：

1. `validate-skill.py`：脚注按 `FOOTNOTE_DEF` 切分与计数，具名脚注（`[^alpha]:`）
   不再被读成 "0.00 注/千字"；`--help`/`-h` 退出 0，未知参数与缺失文件退出 2。
2. `gate.py`：`_review_path()` 拒绝绝对路径、符号链接组件与任何解析到项目外的名字，
   `--request`/`--check` 不再打印项目外文件内容后返回 0。
3. `package_delivery.py`：`derive_slug()` 只认单个阿拉伯数字“第N条”；`channel-probe.json`
   内的绝对路径在打包前重写为 `<末级名>[已脱敏]`；清单只记项目目录名并置
   `project_path_redacted: true`；`07-paper.md` 仍含 `{{PLACEHOLDER}}` 时打包报错（含 `--draft`）。
4. `foreign_sources.py`：`check` 必须显式 `--allow-network`，否则返回 3 与
   NETWORK_NOT_AUTHORISED；探测使用 `PROBE_USER_AGENT`；`plan` 对未登记法域返回 1。

另含本仓库 scripts/ 侧的两项收尾：`audit_commentary.py` 的收束提示与 SKILL.md §六 6
硬门禁保持一致；`scan_corpus.py` 在存在 read_error 行时返回非零退出码。

所有测试只用 tempfile 临时目录，绝不写开发者主目录，也不碰真实通道登记表；
`foreign_sources` 测试全程把 `urlopen` 替换为“一旦被调用就判定失败”的替身，绝不联网。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import foreign_sources  # noqa: E402
import scan_corpus  # noqa: E402
from audit_commentary import audit_project  # noqa: E402
from gate import _review_path, main as gate_main, require_reviewable_artifacts  # noqa: E402
from gate import review_files_for  # noqa: E402
from new_commentary_project import initialize_project  # noqa: E402
from package_delivery import (  # noqa: E402
    derive_slug,
    package,
    redact_local_paths,
    redacted_probe,
)
from verify_delivery import verify  # noqa: E402

# validate-skill.py 的文件名含连字符，只能按路径加载。
_spec = importlib.util.spec_from_file_location("validate_skill", SCRIPTS_DIR / "validate-skill.py")
validate_skill = importlib.util.module_from_spec(_spec)
sys.modules["validate_skill"] = validate_skill
_spec.loader.exec_module(validate_skill)  # type: ignore[union-attr]

SECRET_TOKEN = "PRE-SHARED-SECRET-DO-NOT-LEAK"
BACKSLASH = chr(92)


def run_script(script_name: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script_name), *[str(arg) for arg in args]],
        capture_output=True,
        text=True,
    )


def capture_main(callable_, *args) -> tuple:
    """运行脚本 main()，返回 (退出码, stdout, stderr)。"""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = callable_(*args)
    return code, out.getvalue(), err.getvalue()


class NamedFootnotePaperTests(unittest.TestCase):
    """修复项 1：具名脚注的切分、计数与命令行退出码。"""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write_paper(self, body: str, name: str = "07-paper.md") -> Path:
        path = self.root / name
        path.write_text(body, encoding="utf-8")
        return path

    def test_split_body_and_footnotes_counts_named_labels(self) -> None:
        paper = (
            "# 第一条评注\n\n规范定位如后所述。[^alpha]\n\n体系关联见另注。[^beta]\n\n"
            "[^alpha]: 甲说，见测试文献。\n"
            "[^beta]: 乙说，见测试文献二。\n"
        )
        body, footnote_section, notes = validate_skill.split_body_and_footnotes(paper)
        self.assertEqual(notes, 2)
        self.assertNotIn("[^alpha]:", body)
        self.assertTrue(footnote_section.startswith("[^alpha]:"))
        self.assertIn("乙说", footnote_section)

    def test_split_still_counts_numeric_labels_and_mixed_forms(self) -> None:
        paper = "正文。[^1]\n\n[^1]: 一号注。\n[^gamma]: 具名注。\n"
        body, footnote_section, notes = validate_skill.split_body_and_footnotes(paper)
        self.assertEqual(notes, 2)
        self.assertEqual(body, "正文。[^1]\n\n")
        self.assertIn("[^gamma]:", footnote_section)

    def test_split_without_footnote_definitions(self) -> None:
        body, footnote_section, notes = validate_skill.split_body_and_footnotes("只有正文的稿件")
        self.assertEqual((body, footnote_section, notes), ("只有正文的稿件", "", 0))

    def test_footnote_def_pattern_rejects_inline_mentions_without_colon(self) -> None:
        self.assertEqual(validate_skill.FOOTNOTE_DEF.findall("正文里的 [^alpha] 引用不是定义行"), [])

    def test_density_is_not_zero_for_named_footnotes(self) -> None:
        paper = (
            "# 诚信原则评注\n\n"
            + "本节讨论规范定位与适用范围，说明本文的问题意识。" * 4
            + "[^alpha]\n"
            + "[^beta]\n"
            + "[^gamma]\n\n"
            "[^alpha]: 甲说。\n[^beta]: 乙说。\n[^gamma]: 丙说。\n"
        )
        path = self.write_paper(paper)
        code, stdout, _ = capture_main(validate_skill.validate, path)
        match = re.search(r"(\d+\.\d\d) 注/千字（正文 (\d+) 字，脚注 (\d+)）", stdout)
        self.assertIsNotNone(match, stdout)
        self.assertEqual(match.group(3), "3", "具名脚注必须被计入注密度")
        self.assertNotEqual(match.group(1), "0.00", stdout)
        self.assertIn(code, (0, 1))

    def test_help_and_h_exit_zero(self) -> None:
        for flag in ("--help", "-h"):
            result = run_script("validate-skill.py", flag)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("用法", result.stdout)

    def test_unknown_flag_exits_two(self) -> None:
        result = run_script("validate-skill.py", "--strict", "07-paper.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("未知参数", result.stderr)
        self.assertIn("用法", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_missing_file_exits_two_with_message_on_stderr(self) -> None:
        result = run_script("validate-skill.py", self.root / "no-such-paper.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("文件不存在", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_cli_reports_named_footnote_density(self) -> None:
        path = self.write_paper(
            "# 评注\n\n"
            + "本文围绕规范属性与法律效果展开分析，逐一检视各要件。" * 4
            + "[^alpha]\n[^beta]\n\n[^alpha]: 甲说。\n[^beta]: 乙说。\n"
        )
        result = run_script("validate-skill.py", path)
        self.assertIn("脚注 2）", result.stdout, result.stdout)
        self.assertNotIn("0.00 注/千字", result.stdout)


class GateReviewPathTests(unittest.TestCase):
    """修复项 2：project-state.json 里的待确认文件路径不得越出项目目录。"""

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
        self.secret = self.root / "secret-token.txt"
        self.secret.write_text(f"账号口令：{SECRET_TOKEN}\n", encoding="utf-8")

    # ---- 夹具辅助 ----

    def complete_gate_files(self, gate_id: str = "G1_topic") -> None:
        state = json.loads((self.project / "project-state.json").read_text(encoding="utf-8"))
        for name in review_files_for(state["gates"][gate_id]):
            self.project.joinpath(name).write_text(
                "本阶段研究已完成，依据与范围见项目内记录。\n", encoding="utf-8"
            )

    def set_review_files(self, names: list, gate_id: str = "G1_topic") -> None:
        state_path = self.project / "project-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["gates"][gate_id]["review_files"] = names
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- _review_path 单元行为 ----

    def test_review_path_accepts_plain_relative_name(self) -> None:
        self.assertEqual(
            _review_path(self.project, "02a-thesis-brief.md"),
            self.project.resolve() / "02a-thesis-brief.md",
        )

    def test_review_path_rejects_parent_traversal(self) -> None:
        with self.assertRaises(ValueError):
            _review_path(self.project, "../secret-token.txt")

    def test_review_path_rejects_absolute_path(self) -> None:
        with self.assertRaises(ValueError):
            _review_path(self.project, str(self.secret))
        with self.assertRaises(ValueError):
            _review_path(self.project, "/etc/passwd")

    def test_review_path_rejects_symlink_even_when_target_is_inside_project(self) -> None:
        (self.project / "real-note.md").write_text("项目内真实文件。\n", encoding="utf-8")
        (self.project / "linked-note.md").symlink_to(self.project / "real-note.md")
        with self.assertRaises(ValueError):
            _review_path(self.project, "linked-note.md")

    def test_review_path_rejects_nested_escape_that_resolves_back_inside(self) -> None:
        # `sub/../x` 仍落在项目内，应放行；经子目录越界的必须拒绝。
        (self.project / "sub").mkdir()
        self.assertEqual(
            _review_path(self.project, "sub/../01a-norm-brief.md").resolve(),
            self.project.resolve() / "01a-norm-brief.md",
        )
        with self.assertRaises(ValueError):
            _review_path(self.project, "sub/../../secret-token.txt")

    def test_require_reviewable_artifacts_refuses_escaping_name(self) -> None:
        self.complete_gate_files()
        self.set_review_files(["../secret-token.txt"])
        state = json.loads((self.project / "project-state.json").read_text(encoding="utf-8"))
        with self.assertRaises(ValueError) as caught:
            require_reviewable_artifacts(self.project, state["gates"]["G1_topic"])
        self.assertIn("超出项目目录", str(caught.exception))

    # ---- 命令行端到端：绝不打印项目外文件，且退出码非零 ----

    def test_cli_request_gate_does_not_leak_file_outside_project(self) -> None:
        self.complete_gate_files()
        self.set_review_files(["../secret-token.txt"])
        result = run_script("gate.py", self.project, "--request", "G1_topic")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn(SECRET_TOKEN, result.stdout)
        self.assertNotIn(SECRET_TOKEN, result.stderr)
        self.assertNotIn(str(self.secret.resolve()), result.stdout)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("超出项目目录", result.stderr)
        # 拒绝读取后，闸门状态不得被改写为 awaiting
        state = json.loads((self.project / "project-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["gates"]["G1_topic"]["status"], "pending")

    def test_cli_check_gate_does_not_leak_file_outside_project(self) -> None:
        self.complete_gate_files()
        self.set_review_files(["../secret-token.txt"])
        result = run_script("gate.py", self.project, "--check", "G1_topic")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn(SECRET_TOKEN, result.stdout)

    def test_cli_request_gate_refuses_absolute_path(self) -> None:
        self.complete_gate_files()
        self.set_review_files([str(self.secret)])
        result = run_script("gate.py", self.project, "--request", "G1_topic")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn(SECRET_TOKEN, result.stdout)

    def test_cli_request_gate_refuses_symlinked_review_file(self) -> None:
        self.complete_gate_files()
        (self.project / "linked-note.md").symlink_to(self.secret)
        self.set_review_files(["linked-note.md"])
        result = run_script("gate.py", self.project, "--request", "G1_topic")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn(SECRET_TOKEN, result.stdout)

    def test_legit_review_files_still_print_and_request_succeeds(self) -> None:
        self.complete_gate_files()
        code, stdout, _ = capture_main(gate_main, [str(self.project), "--request", "G1_topic"])
        self.assertEqual(code, 0, stdout)
        self.assertIn("本阶段研究已完成", stdout)
        state = json.loads((self.project / "project-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["gates"]["G1_topic"]["status"], "awaiting")


class PackageDeliverySlugAndRedactionTests(unittest.TestCase):
    """修复项 3：slug 推导、本机路径脱敏、占位符门禁与 --force 说明。"""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def make_profile_project(self, article: str, name: str = "case") -> Path:
        project = self.root / name
        project.mkdir(parents=True, exist_ok=True)
        (project / "research-profile.yaml").write_text(
            "schema_version: 1\nproject:\n  law_title: 中华人民共和国民法典\n"
            f'  article: "{article}"\n',
            encoding="utf-8",
        )
        return project

    def make_draft_project(self, name: str = "delivery-case", paper_text: str = "# 稿件\n") -> Path:
        project = self.root / name
        project.mkdir(parents=True, exist_ok=True)
        (project / "07-paper.md").write_text(paper_text, encoding="utf-8")
        (project / "07-paper.docx").write_bytes(b"PK\x03\x04test")
        (project / "quality-signoff.json").write_text("{}", encoding="utf-8")
        (project / "03-source-ledger.jsonl").write_text("{}\n", encoding="utf-8")
        return project

    # ---- derive_slug ----

    def test_derive_slug_accepts_single_arabic_article(self) -> None:
        self.assertEqual(derive_slug(self.make_profile_project("第1165条", "a1")), "art1165")
        self.assertEqual(derive_slug(self.make_profile_project("第 7 条", "a3")), "art7")

    def test_derive_slug_refuses_multiple_articles(self) -> None:
        self.assertIsNone(derive_slug(self.make_profile_project("第7条、第8条", "multi")))

    def test_derive_slug_refuses_chinese_numerals(self) -> None:
        self.assertIsNone(derive_slug(self.make_profile_project("第一千一百六十五条", "cn")))

    def test_derive_slug_refuses_profile_without_article(self) -> None:
        project = self.root / "no-article"
        project.mkdir()
        (project / "research-profile.yaml").write_text("project:\n  title: 无条文号\n", encoding="utf-8")
        self.assertIsNone(derive_slug(project))
        self.assertIsNone(derive_slug(self.root / "no-profile-dir"))

    def test_derive_slug_keeps_first_art_number_for_paragraph_qualifier(self) -> None:
        # 已文档化口径（SKILL.md §八）：只数 `第N条` 的出现次数，款次不参与推导，
        # 因此 `第1165条第1款` 仍得到 art1165；两个及以上条文才拒绝推断。
        self.assertEqual(derive_slug(self.make_profile_project("第1165条第1款", "para")), "art1165")

    # ---- redact_local_paths / redacted_probe ----

    def test_posix_and_windows_absolute_paths_are_redacted(self) -> None:
        self.assertEqual(
            redact_local_paths("/Users/lcw-testuser/proj/channel-probe.json"),
            "channel-probe.json[已脱敏]",
        )
        self.assertEqual(redact_local_paths(f"C:{BACKSLASH}Users{BACKSLASH}me{BACKSLASH}probe.json"), "probe.json[已脱敏]")
        self.assertEqual(redact_local_paths(f"{BACKSLASH}{BACKSLASH}server{BACKSLASH}share{BACKSLASH}f.log"), "f.log[已脱敏]")

    def test_relative_paths_and_prose_are_untouched(self) -> None:
        self.assertEqual(redact_local_paths("channel-probe.json"), "channel-probe.json")
        self.assertEqual(redact_local_paths("已确认通道可用"), "已确认通道可用")
        self.assertEqual(redact_local_paths(7), 7)
        self.assertIsNone(redact_local_paths(None))

    def test_redaction_walks_nested_structures(self) -> None:
        value = {
            "probe": "/Users/lcw-testuser/work/project/channel-probe.json",
            "capabilities": [{"log": "/Users/lcw-testuser/work/out.log", "note": "relative/ok.md"}],
        }
        redacted = redact_local_paths(value)
        self.assertEqual(redacted["probe"], "channel-probe.json[已脱敏]")
        self.assertEqual(redacted["capabilities"][0]["log"], "out.log[已脱敏]")
        self.assertEqual(redacted["capabilities"][0]["note"], "relative/ok.md")

    def test_redacted_probe_returns_redacted_bytes(self) -> None:
        source = self.root / "channel-probe.json"
        source.write_text(
            json.dumps(
                {
                    "registry_path": "/Users/lcw-testuser/work/channel-registry.json",
                    "capabilities": {"norm.exact_article": {"output": f"C:{BACKSLASH}tmp{BACKSLASH}probe.log"}},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        payload = redacted_probe(source)
        self.assertIsInstance(payload, bytes)
        text = payload.decode("utf-8")
        self.assertNotIn("/Users/lcw-testuser", text)
        self.assertIn("channel-registry.json[已脱敏]", text)
        self.assertIn("probe.log[已脱敏]", text)

    def test_redacted_probe_refuses_unparseable_json(self) -> None:
        source = self.root / "broken-probe.json"
        source.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            redacted_probe(source)

    # ---- 打包端到端 ----

    def test_packaged_probe_and_manifest_do_not_carry_local_paths(self) -> None:
        project = self.make_draft_project("民法典第7条评注")
        resolved = project.resolve()
        (project / "channel-probe.json").write_text(
            json.dumps(
                {"probe_home": str(resolved), "log": str(resolved / "probe.log"), "capabilities": {}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        manifest = package(
            project, "art1165", project / "delivery", include_support=True, force=False, draft=True
        )
        self.assertEqual(manifest["project"], project.name)
        self.assertNotIn("/", manifest["project"])
        self.assertIs(manifest["project_path_redacted"], True)

        delivery = project / "delivery"
        probe_text = (delivery / "art1165-channel-probe.json").read_text(encoding="utf-8")
        probe_copy = json.loads(probe_text)
        self.assertEqual(probe_copy["probe_home"], f"{project.name}[已脱敏]")
        self.assertEqual(probe_copy["log"], "probe.log[已脱敏]")
        self.assertNotIn(str(resolved), probe_text)

        manifest_text = (delivery / "art1165-delivery-manifest.json").read_text(encoding="utf-8")
        self.assertNotIn(str(resolved), manifest_text)
        self.assertNotIn(str(resolved.parent), manifest_text)
        # 脱敏后的字节仍必须与清单哈希一致，否则交付完整性校验会失效
        self.assertEqual(verify(delivery)["status"], "INTEGRITY_OK")

    def test_broken_probe_json_leaves_no_partial_delivery(self) -> None:
        project = self.make_draft_project("broken-probe")
        (project / "channel-probe.json").write_text("{oops", encoding="utf-8")
        with self.assertRaises(ValueError):
            package(
                project, "art1165", project / "delivery", include_support=True, force=False, draft=True
            )
        self.assertFalse((project / "delivery").exists())

    def test_placeholder_in_paper_blocks_draft_packaging(self) -> None:
        project = self.make_draft_project("placeholder", "# 稿件\n\n{{LAW_TITLE}}第7条。\n")
        with self.assertRaises(ValueError):
            package(project, "art1165", project / "delivery", include_support=False, force=False, draft=True)

        result = run_script("package_delivery.py", "--project", project, "--slug", "art1165", "--draft")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("占位符", result.stderr)
        self.assertFalse((project / "delivery").exists())

    def test_filled_paper_passes_the_placeholder_gate(self) -> None:
        project = self.make_draft_project("filled", "# 稿件\n\n第七条确立诚信原则。\n")
        result = run_script("package_delivery.py", "--project", project, "--slug", "art1165", "--draft")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((project / "delivery" / "art1165-commentary.md").is_file())

    def test_force_help_says_directory_is_backed_up(self) -> None:
        result = run_script("package_delivery.py", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"renamed\s+to\s+a\s+backup")

    def test_derived_slug_used_when_slug_omitted(self) -> None:
        project = self.make_profile_project("第1165条", "derived")
        (project / "07-paper.md").write_text("# 稿件\n\n第一千一百六十五条。\n", encoding="utf-8")
        result = run_script("package_delivery.py", "--project", project, "--draft")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((project / "delivery" / "art1165-commentary.md").is_file())

    def test_ambiguous_article_requires_explicit_slug(self) -> None:
        project = self.make_profile_project("第一千一百六十五条", "ambiguous")
        (project / "07-paper.md").write_text("# 稿件\n", encoding="utf-8")
        result = run_script("package_delivery.py", "--project", project, "--draft")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("无法从 research-profile.yaml 推导 slug", result.stderr)
        self.assertFalse((project / "delivery").exists())


class ForeignSourcesNetworkAuthorisationTests(unittest.TestCase):
    """修复项 4：check 必须显式授权联网；探测标识如实署名。

    本类测试全程不允许真实网络：`urlopen` 被替换为“一旦被调用即失败”的替身，
    需要模拟响应时在测试内再套一层替身。
    """

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.registry = self.root / "registry.json"
        self.registry.write_text(json.dumps(self.registry_data(), ensure_ascii=False), encoding="utf-8")
        self._registry_backup = foreign_sources.REGISTRY
        foreign_sources.REGISTRY = self.registry
        self.addCleanup(setattr, foreign_sources, "REGISTRY", self._registry_backup)

        patcher = mock.patch.object(
            foreign_sources.urllib.request, "urlopen", side_effect=AssertionError("real network IO")
        )
        self.urlopen_guard = patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def registry_data() -> dict:
        return {
            "generated": "2026-01-01",
            "refresh_cadence_days": 90,
            "sources": [
                {
                    "id": "de-official",
                    "title": "Gesetze im Internet",
                    "jurisdictions": ["DE"],
                    "kind": "website",
                    "role": "primary",
                    "auth": "none",
                    "state": "VERIFIED_KEYLESS",
                    "layers": ["norm"],
                    "url": "https://www.gesetze-im-internet.de/bgb/",
                    "provider": "BMJ",
                    "upstream": "BGBl",
                    "official_hosts": ["gesetze-im-internet.de"],
                    "acceptance": "逐字命中第 242 条",
                    "checked": "2026-01-01",
                },
                {
                    "id": "de-mcp",
                    "title": "DE legal MCP",
                    "jurisdictions": ["DE"],
                    "kind": "mcp",
                    "state": "UNVERIFIED",
                    "layers": ["norm"],
                    "url": "https://example.invalid/mcp",
                    "checked": "",
                },
                {
                    "id": "de-no-url",
                    "title": "无端点条目",
                    "jurisdictions": ["DE"],
                    "kind": "website",
                    "state": "UNVERIFIED",
                    "layers": ["norm"],
                    "checked": "",
                },
            ],
            "official_hosts": {"DE": ["gesetze-im-internet.de"]},
        }

    def fake_urlopen(self, **kwargs):
        """在测试内临时替换 urlopen；退出后回落到 setUp 的“禁止联网”替身。"""
        return mock.patch.object(foreign_sources.urllib.request, "urlopen", **kwargs)

    # ---- check：未授权即拒绝，且绝不发起请求 ----

    def test_check_without_allow_network_refuses_with_exit_three(self) -> None:
        code, stdout, _ = capture_main(foreign_sources.main, ["check", "--id", "de-official"])
        self.assertEqual(code, 3)
        self.assertIn("NETWORK_NOT_AUTHORISED", stdout)
        self.assertIn("gesetze-im-internet.de", stdout)
        self.assertIn("--allow-network", stdout)

    def test_check_performs_no_http_before_authorisation(self) -> None:
        # 未加 --allow-network 时不得进入 urllib：替身计数必须为 0。
        code, stdout, _ = capture_main(foreign_sources.main, ["check", "--id", "de-official"])
        self.assertEqual(code, 3)
        self.assertEqual(self.urlopen_guard.call_count, 0, "check 在未授权时不得发起请求")
        self.assertNotIn("ALIVE", stdout)
        self.assertNotIn("UNREACHABLE", stdout)

    def test_mcp_entry_is_never_probed_even_with_flag(self) -> None:
        code, stdout, _ = capture_main(
            foreign_sources.main, ["check", "--id", "de-mcp", "--allow-network"]
        )
        self.assertEqual(code, 0)
        self.assertIn("NOT_AUTO_CHECKABLE", stdout)
        self.assertEqual(self.urlopen_guard.call_count, 0, "MCP 条目不得被 HTTP 探测")

    def test_entry_without_url_is_never_probed(self) -> None:
        code, stdout, _ = capture_main(
            foreign_sources.main, ["check", "--id", "de-no-url", "--allow-network"]
        )
        self.assertEqual(code, 0)
        self.assertIn("NOT_AUTO_CHECKABLE", stdout)
        self.assertEqual(self.urlopen_guard.call_count, 0)

    def test_unknown_id_exits_two(self) -> None:
        code, stdout, _ = capture_main(foreign_sources.main, ["check", "--id", "nope"])
        self.assertEqual(code, 2)
        self.assertIn("unknown id", stdout)

    def test_check_with_flag_uses_honest_user_agent(self) -> None:
        captured = {}

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, limit=-1):
                return b"offizielle normtext " * 60

        def fake_urlopen(request, timeout=None):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse()

        with self.fake_urlopen(side_effect=fake_urlopen):
            code, stdout, _ = capture_main(
                foreign_sources.main, ["check", "--id", "de-official", "--allow-network"]
            )
        self.assertEqual(code, 0, stdout)
        self.assertIn("ALIVE", stdout)
        request = captured["request"]
        self.assertEqual(request.get_header("User-agent"), foreign_sources.PROBE_USER_AGENT)
        self.assertIn("law-commentary-workshop", foreign_sources.PROBE_USER_AGENT)
        self.assertNotEqual(request.full_url, "")
        self.assertEqual(captured["timeout"], 10)

    def test_unreachable_endpoint_returns_one(self) -> None:
        with self.fake_urlopen(
            side_effect=urllib.error.URLError("name resolution failed")
        ):
            code, stdout, _ = capture_main(
                foreign_sources.main, ["check", "--id", "de-official", "--allow-network"]
            )
        self.assertEqual(code, 1)
        self.assertIn("UNREACHABLE", stdout)

    def test_gone_endpoint_returns_one(self) -> None:
        gone = urllib.error.HTTPError(
            "https://www.gesetze-im-internet.de/bgb/", 404, "Not Found", None, None
        )
        with self.fake_urlopen(side_effect=gone):
            code, stdout, _ = capture_main(
                foreign_sources.main, ["check", "--id", "de-official", "--allow-network"]
            )
        self.assertEqual(code, 1)
        self.assertIn("GONE", stdout)

    def test_auth_required_endpoint_returns_one(self) -> None:
        forbidden = urllib.error.HTTPError(
            "https://www.gesetze-im-internet.de/bgb/", 401, "Unauthorized", None, None
        )
        with self.fake_urlopen(side_effect=forbidden):
            code, stdout, _ = capture_main(
                foreign_sources.main, ["check", "--id", "de-official", "--allow-network"]
            )
        self.assertEqual(code, 1)
        self.assertIn("AUTH_OR_FORBIDDEN", stdout)

    def test_transport_mismatch_is_informative_not_a_failure(self) -> None:
        mismatch = urllib.error.HTTPError(
            "https://www.gesetze-im-internet.de/bgb/", 405, "Method Not Allowed", None, None
        )
        with self.fake_urlopen(side_effect=mismatch):
            code, stdout, _ = capture_main(
                foreign_sources.main, ["check", "--id", "de-official", "--allow-network"]
            )
        self.assertEqual(code, 0)
        self.assertIn("TRANSPORT_MISMATCH", stdout)

    def test_no_challenge_interception_is_reported_as_no_text(self) -> None:
        class ChallengeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, limit=-1):
                return b"just a moment, checking your browser" * 30

        with self.fake_urlopen(return_value=ChallengeResponse()):
            code, stdout, _ = capture_main(
                foreign_sources.main, ["check", "--id", "de-official", "--allow-network"]
            )
        self.assertEqual(code, 1)
        self.assertIn("NO_TEXT", stdout)

    # ---- plan / 纯函数 ----

    def test_plan_for_unregistered_jurisdiction_exits_one(self) -> None:
        code, stdout, _ = capture_main(
            foreign_sources.main, ["plan", "--jurisdiction", "ZZ"]
        )
        self.assertEqual(code, 1)
        self.assertIn("gate: UNREGISTERED_JURISDICTION", stdout)

    def test_plan_for_registered_jurisdiction_exits_zero(self) -> None:
        code, stdout, _ = capture_main(
            foreign_sources.main, ["plan", "--jurisdiction", "de", "--layer", "norm"]
        )
        self.assertEqual(code, 0, stdout)
        self.assertIn("gate: CANDIDATES_REQUIRE_ACCEPTANCE", stdout)
        self.assertIn("de-official", stdout)

    def test_plan_with_no_channel_for_layer_exits_zero_with_gate(self) -> None:
        code, stdout, _ = capture_main(
            foreign_sources.main, ["plan", "--jurisdiction", "DE", "--layer", "case"]
        )
        self.assertEqual(code, 0, stdout)
        self.assertIn("gate: NO_BOUND_CHANNEL", stdout)

    def test_layers_of_falls_back_to_alias_mapping(self) -> None:
        self.assertEqual(foreign_sources.layers_of({"layers": ["governing_law", "case_law"]}), ["norm", "case"])
        self.assertEqual(foreign_sources.layers_of({"commentary_layers": ["scholarship"]}), ["scholarship"])
        self.assertEqual(foreign_sources.layers_of({}), [])

    def test_age_days_tolerates_blank_and_broken_dates(self) -> None:
        self.assertIsNone(foreign_sources.age_days(""))
        self.assertIsNone(foreign_sources.age_days("2026-13-45"))
        self.assertIsInstance(foreign_sources.age_days("2000-01-01"), int)


class ClosingSectionGateConsistencyTests(unittest.TestCase):
    """audit_commentary 的收束提示不得与 SKILL.md §六 6“无结论章”硬门禁相冲突。"""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name) / "project"
        initialize_project(
            output=self.project,
            law_title="中华人民共和国民法典",
            article="第七条",
            as_of="2026-09-09",
            target_journal="测试期刊",
        )

    def audit_section_findings(self, body: str) -> list:
        (self.project / "07-paper.md").write_text(body, encoding="utf-8")
        report = audit_project(self.project)
        return [item["message"] for item in report["warnings"] if item["code"] == "PAPER_SECTION_MISSING"]

    def test_commentary_ending_with_burden_section_is_not_pushed_to_add_conclusion(self) -> None:
        messages = self.audit_section_findings(
            "# 民法典第七条评注\n\n"
            "## 摘要\n\n本文讨论诚信原则。\n\n"
            "**关键词：** 诚信原则\n\n"
            "## 一、规范定位\n\n条文确立诚信原则。\n\n"
            "## 二、构成要件\n\n要件逐项检视。\n\n"
            "## 三、法律效果\n\n效果依案型而定。\n\n"
            "## 四、证明责任\n\n主张适用诚信原则者就其要件事实负举证责任。\n"
        )
        self.assertFalse(
            [message for message in messages if "收束" in message or "结语" in message],
            f"证明责任收尾的评注不应再被提示补写结语/结论：{messages}",
        )

    def test_paper_without_burden_section_and_without_closing_still_warns(self) -> None:
        messages = self.audit_section_findings(
            "# 民法典第七条评注\n\n"
            "## 摘要\n\n本文讨论诚信原则。\n\n"
            "**关键词：** 诚信原则\n\n"
            "## 一、规范定位\n\n条文确立诚信原则。\n\n"
            "## 二、构成要件\n\n要件逐项检视。\n"
        )
        closing = [message for message in messages if "证明责任" in message]
        self.assertEqual(len(closing), 1, messages)
        self.assertIn("收束", closing[0])

    def test_warning_never_asks_for_a_conclusion_chapter(self) -> None:
        messages = self.audit_section_findings(
            "# 民法典第七条评注\n\n## 摘要\n\n本文讨论诚信原则。\n\n"
            "**关键词：** 诚信原则\n\n## 一、规范定位\n\n条文确立诚信原则。\n"
        )
        closing = [message for message in messages if "结语" in message or "结论" in message]
        self.assertEqual(len(closing), 1, messages)
        self.assertIn("不得", closing[0])
        self.assertIn("SKILL.md", closing[0])
        self.assertNotIn("未发现结语或结论", " ".join(messages))

    def test_abstract_and_keyword_findings_are_unchanged(self) -> None:
        messages = self.audit_section_findings("# 民法典第七条评注\n\n## 一、规范定位\n\n条文已定。\n\n## 二、证明责任\n\n举证分配已定。\n")
        self.assertIn('未发现“摘要”', messages)
        self.assertIn('未发现“关键词”', messages)


class ScanCorpusExitCodeTests(unittest.TestCase):
    """scan_corpus 存在 read_error 行时必须返回非零，避免把部分失败当成功。"""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "index.jsonl"

    def blocked_file(self, corpus: Path, name: str) -> Path:
        path = corpus / name
        path.write_text("受限资料", encoding="utf-8")
        path.chmod(0o000)
        return path

    def scan(self, corpus: Path) -> tuple:
        return capture_main(
            scan_corpus.main, ["--root", str(corpus), "--output", str(self.output)]
        )

    def test_clean_corpus_exits_zero(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("running as root: permission bits do not block reads")
        corpus = self.root / "clean"
        corpus.mkdir()
        (corpus / "资料.md").write_text("可读资料", encoding="utf-8")
        code, stdout, stderr = self.scan(corpus)
        self.assertEqual(code, 0, stderr)
        self.assertIn("Indexed 1 files", stdout)

    def test_partial_read_error_exits_one_and_still_prints_results(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("running as root: permission bits do not block reads")
        corpus = self.root / "partial"
        corpus.mkdir()
        (corpus / "ok.md").write_text("可读资料", encoding="utf-8")
        blocked = self.blocked_file(corpus, "blocked.md")
        try:
            code, stdout, stderr = self.scan(corpus)
        finally:
            blocked.chmod(0o644)
        self.assertEqual(code, 1, f"stdout={stdout}\nstderr={stderr}")
        self.assertIn("Indexed 2 files", stdout)
        self.assertIn("read_error", stderr)
        rows = [json.loads(line) for line in self.output.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sorted(row["index_status"] for row in rows), ["read_error", "text_indexed"])

    def test_total_read_failure_exits_two(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("running as root: permission bits do not block reads")
        corpus = self.root / "unreadable"
        corpus.mkdir()
        blocked = self.blocked_file(corpus, "only.md")
        try:
            code, stdout, stderr = self.scan(corpus)
        finally:
            blocked.chmod(0o644)
        self.assertEqual(code, 2, f"stdout={stdout}\nstderr={stderr}")
        self.assertIn("1 of 1", stderr)

    def test_corpus_without_supported_files_still_exits_zero(self) -> None:
        corpus = self.root / "empty-dir"
        corpus.mkdir()
        (corpus / "notes.doc").write_text("不支持的后缀", encoding="utf-8")
        code, stdout, stderr = self.scan(corpus)
        self.assertEqual(code, 0, stderr)
        self.assertIn("Indexed 0 files", stdout)

    def test_invalid_arguments_exit_two(self) -> None:
        corpus = self.root / "bad-args"
        corpus.mkdir()
        code, _, stderr = capture_main(
            scan_corpus.main,
            ["--root", str(corpus), "--output", str(self.output), "--preview-chars", "-1"],
        )
        self.assertEqual(code, 2)
        self.assertIn("--preview-chars", stderr)


if __name__ == "__main__":
    unittest.main()
