from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from tools.delivery import checks


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        self.status = self.root / "docs/STATUS.yaml"
        self.status.write_text("current: valid\n", encoding="utf-8")
        self.evidence = self.root / "result.json"

    def test_valid_result_reused_but_relevant_change_invalidates(self):
        first = checks.run(self.root, ["status"], evidence=self.evidence)
        self.assertEqual(first["checks"][0]["state"], "passed")
        (self.root / "unrelated.txt").write_text("different branch", encoding="utf-8")
        with patch.object(checks, "status_advice", side_effect=AssertionError("must reuse")):
            self.assertEqual(checks.run(self.root, ["status"], evidence=self.evidence)["checks"][0]["state"], "reused")
        self.status.write_text("needed live fact\n" * 130, encoding="utf-8")
        changed = checks.run(self.root, ["status"], evidence=self.evidence)
        self.assertEqual(changed["checks"][0]["state"], "advisory")
        self.assertEqual(changed["state"], "passed")

    def test_legitimate_no_checks_is_distinct_from_accidental_zero_selection(self):
        self.assertEqual(checks.run(self.root, [])["state"], "not_needed")
        with self.assertRaises(ValueError):
            checks.run(self.root, [], expected=True)
        with self.assertRaises(ValueError):
            checks.run(self.root, ["unknown"])

    def test_broken_required_entry_fails_and_failure_is_not_reused(self):
        failed = checks.run(self.root, ["entries"], evidence=self.evidence)
        self.assertEqual(failed["state"], "failed")
        with patch.object(checks, "entries", wraps=checks.entries) as actual:
            checks.run(self.root, ["entries"], evidence=self.evidence)
            actual.assert_called_once()

    def test_small_and_large_status_both_preserve_content(self):
        for text in ("current: okay\n", "current: " + "x" * 6100, "required: fact\n" * 140):
            self.status.write_text(text, encoding="utf-8")
            self.assertNotEqual(checks.status_advice(self.root)["state"], "failed")
            self.assertEqual(self.status.read_text(encoding="utf-8"), text)

    def test_selected_mechanism_never_runs_unrelated_tests_or_passes_zero_execution(self):
        for output, code, expected in (("Ran 0 tests", 0, "execution_failed"), ("", 0, "execution_failed"),
                                       ("unittest.loader._FailedTest\nRan 1 test", 1, "execution_failed"),
                                       ("Ran 3 tests", 1, "failed"), ("Ran 3 tests", 0, "passed")):
            with patch.object(checks.subprocess, "run", return_value=SimpleNamespace(stdout=output, stderr="", returncode=code)) as actual:
                self.assertEqual(checks.run(self.root, ["writer"])["state"], expected)
                self.assertIn("test_state.py", actual.call_args.args[0])
                self.assertNotIn("test_*.py", actual.call_args.args[0])

    def test_other_mechanism_changes_do_not_invalidate_selected_package_proof(self):
        folder = self.root / "tools/delivery"
        folder.mkdir(parents=True)
        before = checks.identity(self.root, "packages")
        (folder / "platform.py").write_text("changed platform implementation")
        self.assertEqual(before, checks.identity(self.root, "packages"))
        (folder / "packages.py").write_text("changed packaging implementation")
        self.assertNotEqual(before, checks.identity(self.root, "packages"))


if __name__ == "__main__":
    unittest.main()
