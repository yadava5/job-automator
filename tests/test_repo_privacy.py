import json
import re
import subprocess
import unittest
from pathlib import Path


class RepoPrivacyTests(unittest.TestCase):
    def test_generated_private_outputs_are_not_tracked(self):
        tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()

        forbidden_prefixes = (
            "docs/archive/legacy-auto-apply/",
            "docs/superpowers/",
            "outputs/",
            "resume/source/",
            "resume/archive/",
            "resume/generated/",
            "tmp/",
            ".playwright-cli/",
        )
        leaked = [path for path in tracked if path.startswith(forbidden_prefixes)]

        self.assertEqual(leaked, [])

    def test_public_resume_json_has_no_private_metadata(self):
        resume = json.loads(Path("resume/resume.json").read_text(encoding="utf-8"))
        serialized = json.dumps(resume, sort_keys=True)

        self.assertNotIn("source", resume)
        self.assertEqual(resume["basics"].get("phone", ""), "")
        self.assertIsNone(re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", serialized))
        self.assertNotIn("resume/source/current", serialized)
        self.assertNotIn("iCloud current resume", serialized)
        self.assertNotIn("application-packs", serialized)


if __name__ == "__main__":
    unittest.main()
