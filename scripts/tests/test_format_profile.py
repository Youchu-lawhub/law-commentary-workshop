from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from apply_format_profile import apply_profile  # noqa: E402
from format_profile import load_profile, validate_profile  # noqa: E402


class FormatProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.tmp = Path(self.temporary.name)
        self.profile_path = ROOT / "assets" / "format-profiles" / "journal-cn-default.json"
        self.template = ROOT / "assets" / "templates" / "journal-cn.docx"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_presets_validate(self) -> None:
        for path in (ROOT / "assets" / "format-profiles").glob("*.json"):
            self.assertEqual(validate_profile(load_profile(path)), [], path.name)

    def test_invalid_profile_is_rejected(self) -> None:
        data = load_profile(self.profile_path)
        data["body"]["alignment"] = "middle"
        data["footnote"]["size_pt"] = 0
        errors = validate_profile(data)
        self.assertTrue(any("alignment" in item for item in errors))
        self.assertTrue(any("footnote.size_pt" in item for item in errors))

    def test_apply_writes_styles_and_margins(self) -> None:
        target = self.tmp / "out.docx"
        shutil.copyfile(self.template, target)
        profile = load_profile(self.profile_path)
        apply_profile(profile, target)

        with zipfile.ZipFile(target) as z:
            styles = z.read("word/styles.xml").decode("utf-8")
            document = z.read("word/document.xml").decode("utf-8")

        normal = re.search(r'<w:style [^>]*w:styleId="Normal".*?</w:style>', styles, re.S).group(0)
        self.assertIn('<w:sz w:val="21"', normal)
        self.assertIn('w:firstLineChars="200"', normal)
        self.assertIn('w:line="300"', normal)

        heading1 = re.search(r'<w:style [^>]*w:styleId="Heading1".*?</w:style>', styles, re.S).group(0)
        self.assertIn('<w:sz w:val="28"', heading1)

        footnote = re.search(r'<w:style [^>]*w:styleId="FootnoteText".*?</w:style>', styles, re.S).group(0)
        self.assertIn('<w:sz w:val="18"', footnote)

        self.assertIn('<w:pgMar w:top="1440" w:right="1797" w:bottom="1440" w:left="1797"', document)


if __name__ == "__main__":
    unittest.main()
