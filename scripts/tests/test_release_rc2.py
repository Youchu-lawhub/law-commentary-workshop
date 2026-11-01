import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from verify_delivery import verify

class RC2ReleaseTests(unittest.TestCase):
    def cmd(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'package_delivery.py'),*map(str,args)],capture_output=True,text=True)

    def test_roundtrip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'case';p.mkdir();(p/'07-paper.md').write_text('study',encoding='utf8')
            result=self.cmd('--project',p,'--slug','art1165','--draft')
            self.assertEqual(result.returncode,0,result.stderr)
            folder=p/'delivery';self.assertEqual(verify(folder)['status'],'INTEGRITY_OK')
            (folder/'art1165-commentary.md').write_text('changed',encoding='utf8')
            self.assertEqual(verify(folder)['status'],'BLOCKED')

    def test_no_partial_delivery_on_unsafe_input(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'case';p.mkdir();(p/'07-paper.md').write_text('x')
            (p/'07-paper.docx').symlink_to(p/'07-paper.md')
            r=self.cmd('--project',p,'--slug','art1165','--draft')
            self.assertNotEqual(r.returncode,0)
            self.assertFalse((p/'delivery').exists())

    def test_existing_package_not_overwritten_without_force(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'case';p.mkdir();(p/'07-paper.md').write_text('v1')
            self.assertEqual(self.cmd('--project',p,'--slug','art1165','--draft').returncode,0)
            (p/'07-paper.md').write_text('v2')
            self.assertNotEqual(self.cmd('--project',p,'--slug','art1165','--draft').returncode,0)
            self.assertEqual((p/'delivery/art1165-commentary.md').read_text(),'v1')
            self.assertEqual(self.cmd('--project',p,'--slug','art1165','--draft','--force').returncode,0)
            self.assertEqual((p/'delivery/art1165-commentary.md').read_text(),'v2')
            self.assertEqual(verify(p/'delivery')['status'],'INTEGRITY_OK')

    def test_reject_symlink_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'case';p.mkdir();(p/'07-paper.md').write_text('x')
            other=Path(temp)/'other';other.mkdir()
            (p/'alias').symlink_to(other,target_is_directory=True)
            r=self.cmd('--project',p,'--slug','art1165','--draft','--out',p/'alias'/'delivery')
            self.assertNotEqual(r.returncode,0)
            self.assertFalse((other/'delivery').exists())

    def test_missing_document_fails_formal_path(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'case';p.mkdir();(p/'07-paper.md').write_text('x')
            r=self.cmd('--project',p,'--slug','art1165')
            self.assertNotEqual(r.returncode,0)
            self.assertFalse((p/'delivery').exists())

if __name__=='__main__':unittest.main()
