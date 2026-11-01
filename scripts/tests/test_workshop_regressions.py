from __future__ import annotations
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPTS_DIR))
# 兼容两种发现方式：`discover -s scripts/tests` 以顶层模块名导入，
# `discover -s scripts/tests -t .` 以 `scripts.tests.*` 导入。
# 把测试目录本身放进 sys.path，夹具模块在两种情况下都能按顶层名导入。
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0,str(TESTS_DIR))
from gate import main as gate_main, review_files_for
from new_commentary_project import initialize_project
from audit_commentary import audit_project
import test_audit_commentary as fixture_module

class WorkshopRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.project=Path(self.tmp.name)/'project'
        initialize_project(self.project,'测试规范','第1条','2026-10-03')
    def tearDown(self):
        self.tmp.cleanup()
    def run_gate(self,*args):
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            return gate_main([str(self.project),*args])
    def complete_artifacts(self,gate_id):
        state=json.loads((self.project/'project-state.json').read_text())
        for name in review_files_for(state['gates'][gate_id]):
            (self.project/name).write_text('已实际完成本阶段研究，依据与范围见记录。',encoding='utf-8')
    def test_cannot_approve_outline_before_prior_gates(self):
        self.complete_artifacts('G3_outline')
        self.assertEqual(self.run_gate('--approve','G3_outline','--by','user','--note','按此写'),2)
        self.assertEqual(self.run_gate('--request','G3_outline'),2)
    def test_cannot_request_unfinished_template(self):
        self.assertEqual(self.run_gate('--request','G1_topic'),2)
    def test_real_sequential_request_and_approval(self):
        self.complete_artifacts('G1_topic')
        self.assertEqual(self.run_gate('--approve','G1_topic','--by','user','--note','选题合适'),2)
        self.assertEqual(self.run_gate('--request','G1_topic'),0)
        self.assertEqual(self.run_gate('--approve','G1_topic','--by','user','--note','对话第2轮：选题合适'),0)
        self.complete_artifacts('G2_research')
        self.assertEqual(self.run_gate('--request','G2_research'),0)
        self.assertEqual(self.run_gate('--approve','G2_research','--by','user'),2)
        self.assertEqual(self.run_gate('--approve','G2_research','--by','user','--note','对话第3轮：按当前资料范围继续'),0)
    def test_initializer_escapes_quoted_and_multiline_titles(self):
        p=Path(self.tmp.name)/'quoted'
        title='含"引号"的标题\n次行\\内容'
        initialize_project(p,'测试规范','第1条','2026-10-03',project_title=title)
        self.assertEqual(json.loads((p/'project-state.json').read_text())['project_title'],title)
        yaml_text=(p/'research-profile.yaml').read_text()
        line=next(l for l in yaml_text.splitlines() if l.strip().startswith('title:'))
        self.assertEqual(json.loads(line.split(':',1)[1].strip()),title)
    def test_blank_signoff_evidence_cannot_be_ready(self):
        fixture=fixture_module.CommentaryAuditTests();fixture.setUp()
        try:
            fixture.make_ready_fixture()
            p=fixture.project/'quality-signoff.json';data=json.loads(p.read_text())
            data['argument_coherence_checked']['notes']=''
            p.write_text(json.dumps(data))
            report=audit_project(fixture.project)
            self.assertEqual(report['verdict'],'REVIEW_REQUIRED')
            self.assertIn('argument_coherence_checked',report['incomplete_signoffs'])
        finally:fixture.tearDown()
    def test_missing_academic_review_blocks_release(self):
        fixture=fixture_module.CommentaryAuditTests();fixture.setUp()
        try:
            fixture.make_ready_fixture()
            (fixture.project/'13-scholarly-review.md').unlink()
            self.assertEqual(audit_project(fixture.project)['verdict'],'BLOCKED')
        finally:fixture.tearDown()

if __name__=='__main__':unittest.main()
