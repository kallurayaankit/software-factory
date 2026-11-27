import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class FactoryCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "review"

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, str(ROOT / "factory.py"), *map(str, args)],
                                capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, code, result.stderr)
        return result

    def build(self, sample="ready"):
        result = self.cli("build", ROOT / "examples" / f"{sample}.json", self.output)
        return result.stdout.strip().splitlines()[-1].split(": ", 1)[1]

    def approve(self, fingerprint, code=0):
        return self.cli("approve", self.output, "--reviewer", "Example Reviewer",
                        "--fingerprint", fingerprint, code=code)

    def test_ready_review_and_approval(self):
        token = self.build()
        checked = self.cli("verify", self.output)
        self.assertIn(token, checked.stdout)
        self.assertIn("READY FOR HUMAN REVIEW", checked.stdout)
        self.assertFalse((self.output / "approval.json").exists())
        self.approve(token)
        approval = json.loads((self.output / "approval.json").read_text())
        self.assertEqual(approval["fingerprint"], token)
        self.assertIn("no release", approval["scope"])
        self.approve(token, code=2)

    def test_blocked_approval_denied(self):
        token = self.build("blocked")
        self.assertIn("BLOCKED", self.cli("verify", self.output).stdout)
        self.assertIn("approval denied", self.approve(token, code=2).stderr)
        self.assertFalse((self.output / "approval.json").exists())

    def test_tampered_report_cannot_be_approved(self):
        token = self.build()
        (self.output / "report.md").write_text("Not the reviewed report")
        self.assertIn("changed", self.approve(token, code=2).stderr)

    def test_wrong_fingerprint_cannot_be_approved(self):
        self.build()
        self.assertIn("does not match", self.approve("wrong", code=2).stderr)

    def test_invalid_brief_leaves_no_output(self):
        source = Path(self.tmp.name) / "bad.json"
        source.write_text('{"release": "one", "release": "two", "goal": "demo", "checks": []}')
        self.assertIn("Duplicate field", self.cli("build", source, self.output, code=2).stderr)
        self.assertFalse(self.output.exists())

    def test_build_does_not_overwrite_existing_directory(self):
        self.build()
        self.assertIn("already exists", self.cli("build", ROOT / "examples/blocked.json",
                                                 self.output, code=2).stderr)
        self.assertIn("READY FOR HUMAN REVIEW", self.cli("verify", self.output).stdout)


if __name__ == "__main__":
    unittest.main()
