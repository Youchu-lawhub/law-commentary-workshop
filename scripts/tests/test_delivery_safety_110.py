import subprocess,sys,tempfile,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DeliverySafety(unittest.TestCase):
    def test_blocked_project_cannot_ship(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'07-paper.md').write_text('draft',encoding='utf-8')
            r=subprocess.run([sys.executable,str(ROOT/'package_delivery.py'),'--project',str(p),'--slug','art1165'],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)
            self.assertFalse((p/'delivery').exists())
    def test_draft_explicit_label(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'07-paper.md').write_text('draft',encoding='utf-8')
            r=subprocess.run([sys.executable,str(ROOT/'package_delivery.py'),'--project',str(p),'--slug','art1165','--draft'],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertTrue((p/'delivery/DRAFT-NOT-FOR-SUBMISSION.txt').exists())
            self.assertEqual(json.loads((p/'delivery/art1165-delivery-manifest.json').read_text())['delivery_mode'],'draft_not_for_submission')
if __name__=='__main__':unittest.main()
