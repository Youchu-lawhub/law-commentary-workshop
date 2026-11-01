import shutil,sys,tempfile,unittest
from pathlib import Path
SCRIPTS=Path(__file__).resolve().parents[1]
PACKAGE_ROOT=SCRIPTS.parent
sys.path.insert(0,str(SCRIPTS))
from preflight import inspect
class PreflightTests(unittest.TestCase):
    def copy_install(self,target:Path)->Path:
        """把发布包整棵树复制到临时目录，作为可控的安装态夹具。"""
        shutil.copytree(PACKAGE_ROOT,target,symlinks=True,
                        ignore=shutil.ignore_patterns('__pycache__','.git','delivery'))
        return target
    def test_empty_install_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=inspect(tmp)
            self.assertEqual(data['status'],'BLOCKED')
            self.assertIn('SKILL.md',data['missing_files'])
    def test_bundled_install_has_no_missing_files(self):
        data=inspect()
        self.assertEqual(data['missing_files'],[])
        self.assertNotEqual(data['status'],'BLOCKED')
    def test_removed_required_file_is_reported(self):
        """缺文件必须出现在 missing_files：整树复制后逐个删掉清单内的必需文件复验。"""
        with tempfile.TemporaryDirectory() as tmp:
            install=self.copy_install(Path(tmp)/'install')
            baseline=inspect(install)
            self.assertEqual(baseline['missing_files'],[],baseline['findings'])
            removed=install/'LICENSE'
            self.assertTrue(removed.is_file(),'LICENSE must exist in the shipped package')
            removed.unlink()
            data=inspect(install)
            self.assertEqual(data['missing_files'],['LICENSE'])
            self.assertEqual(data['status'],'BLOCKED')
            self.assertTrue(any('LICENSE' in item for item in data['findings']),data['findings'])
    def test_missing_nested_required_file_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            install=self.copy_install(Path(tmp)/'install')
            (install/'assets'/'project-template'/'07-paper.md').unlink()
            data=inspect(install)
            self.assertEqual(data['missing_files'],['assets/project-template/07-paper.md'])
if __name__=='__main__':unittest.main()
