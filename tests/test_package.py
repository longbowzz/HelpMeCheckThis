import json
import re
import unittest
from pathlib import Path

from scripts.helpmecheck import __version__


ROOT = Path(__file__).resolve().parents[1]


class PackageMetadataTests(unittest.TestCase):
    def setUp(self):
        self.package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    def test_name_matches_skill_frontmatter(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        match = re.search(r"^name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(self.package["name"], match.group(1))

    def test_version_matches_runtime(self):
        self.assertEqual(self.package["version"], __version__)

    def test_license_and_repository_metadata(self):
        self.assertEqual(self.package["license"], "MIT")
        self.assertIn("HelpMeCheckThis", self.package["repository"]["url"])
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("longbowzz", license_text)

    def test_package_is_public(self):
        self.assertFalse(self.package.get("private", False))
        self.assertEqual(self.package["publishConfig"]["access"], "public")

    def test_bin_entry_exists_and_is_executable_script(self):
        entry = self.package["bin"]["helpmecheck"]
        bin_path = ROOT / entry
        self.assertTrue(bin_path.is_file())
        self.assertTrue(bin_path.read_text(encoding="utf-8").startswith("#!/usr/bin/env node"))

    def test_files_allowlist_covers_runtime_resources(self):
        files = self.package["files"]
        for required in ("SKILL.md", "references/", "templates/", "scripts/", "bin/"):
            self.assertIn(required, files)
        self.assertIn("!**/__pycache__/**", files)
        self.assertIn("!**/*.pyc", files)
        self.assertFalse(any(entry.startswith("tests") for entry in files))

    def test_required_package_files_exist(self):
        for relative in ("SKILL.md", "README.md", "README.zh-CN.md", "LICENSE",
                         "config.example.json", "bin/helpmecheck.js", "tools/check-pack.mjs"):
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
