from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from package_delivery import package  # noqa: E402


class PackageDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name) / "project"
        self.project.mkdir()
        (self.project / "07-paper.md").write_text("# 稿件", encoding="utf-8")
        (self.project / "07-paper.docx").write_bytes(b"PK\x03\x04test")
        (self.project / "quality-signoff.json").write_text("{}", encoding="utf-8")
        (self.project / "03-source-ledger.jsonl").write_text("{}\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_standard_names_and_manifest(self) -> None:
        manifest = package(self.project, "art1165", self.project / "delivery", include_support=False, force=False, draft=True)
        names = {item["target"] for item in manifest["copied"]}
        self.assertIn("art1165-commentary.docx", names)
        self.assertIn("art1165-commentary.md", names)
        self.assertIn("art1165-quality-signoff.json", names)
        self.assertNotIn("art1165-source-ledger.jsonl", names)

        manifest_path = self.project / "delivery" / "art1165-delivery-manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(data["slug"], "art1165")
        self.assertTrue(any(item["source"] == "07-paper.pdf" for item in data["skipped"]))

    def test_support_and_no_overwrite(self) -> None:
        package(self.project, "art1165", self.project / "delivery", include_support=True, force=False, draft=True)
        self.assertTrue((self.project / "delivery" / "art1165-source-ledger.jsonl").is_file())

        with self.assertRaises(ValueError):
            package(self.project, "art1165", self.project / "delivery", include_support=True, force=False, draft=True)

    def test_invalid_slug_rejected(self) -> None:
        with self.assertRaises(ValueError):
            package(self.project, "Art 1165", self.project / "delivery", include_support=False, force=False, draft=True)


if __name__ == "__main__":
    unittest.main()
