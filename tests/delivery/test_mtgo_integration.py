"""Small real Git histories for reuse, not product regression fixtures."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.delivery.gitfacts import preparation_source, InfrastructureError
import mtgo_fetch_checkpoint as checkpoint
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("integration", Path(__file__).parents[2] / "tools/integrate_mtgo_candidate.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mtgo-integration-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repository"
        self.root.mkdir()
        self.artifact = Path(self.temp.name) / "artifact"
        self.git("init")
        self.git("config", "user.name", "Synthetic test")
        self.git("config", "user.email", "synthetic@example.invalid")
        for path in ("src/generator.py", "data/standard/input.json", "stats/standard/mtgo/result.json", "README.md"):
            self.write(path, "original\n")
        self.git("add", ".")
        self.git("commit", "-m", "synthetic base")
        self.base = self.git("rev-parse", "HEAD")

    def git(self, *args):
        return module.text(self.root, *args)

    def write(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8")

    def export(self, change=True):
        if change:
            self.write("stats/standard/mtgo/result.json", "candidate\n")
            self.write("stats/standard/mtgo/new.json", "new candidate file\n")
        module.export(self.root, self.artifact)
        (self.artifact / "generation-subject.txt").write_text("a" * 64, encoding="utf-8")
        self.git("reset", "--hard", self.base)

    def commit(self, path, value):
        self.write(path, value)
        self.git("add", ".")
        self.git("commit", "-m", "another delivery")

    def test_disjoint_delivery_preserved_and_lost_push_response_reuses_commit(self):
        self.export()
        self.commit("README.md", "new docs\n")
        self.commit("stats/modern/melee/result.json", "new Tabletop delivery\n")
        result = module.integrate(self.root, self.artifact, "HEAD", "100")
        self.assertEqual(result["status"], "prepared")
        self.assertEqual((self.root / "README.md").read_text(), "new docs\n")
        self.assertEqual((self.root / "stats/modern/melee/result.json").read_text(), "new Tabletop delivery\n")
        self.assertEqual((self.root / "stats/standard/mtgo/result.json").read_text(), "candidate\n")
        self.assertTrue((self.root / "stats/standard/mtgo/new.json").is_file())
        head = self.git("rev-parse", "HEAD")
        reused = module.integrate(self.root, self.artifact, "HEAD", "100")
        self.assertTrue(reused["reused"])
        self.assertEqual(reused["commit"], head)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_changed_input_retains_candidate_without_modifying_current_delivery(self):
        self.export()
        self.commit("src/generator.py", "changed algorithm\n")
        head = self.git("rev-parse", "HEAD")
        with self.assertRaisesRegex(ValueError, "src/generator.py"):
            module.integrate(self.root, self.artifact, "HEAD", "101")
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertTrue((self.artifact / "output.patch").is_file())

    def test_overlapping_output_does_not_overwrite_later_delivery(self):
        self.export()
        self.commit("stats/standard/mtgo/result.json", "later output\n")
        with self.assertRaises(subprocess.CalledProcessError):
            module.integrate(self.root, self.artifact, "HEAD", "102")
        self.assertEqual((self.root / "stats/standard/mtgo/result.json").read_text(), "later output\n")
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_no_change_has_no_evidence_commit(self):
        self.export(change=False)
        result = module.integrate(self.root, self.artifact, "HEAD", "103")
        self.assertEqual(result["status"], "unchanged")
        self.assertFalse(result["changed"])
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base)

    def test_whole_site_preparation_includes_later_delivered_work(self):
        self.commit("stats/modern/melee/result.json", "delivered Tabletop update\n")
        deployed = self.git("rev-parse", "HEAD")
        self.commit("README.md", "later accepted documentation\n")
        latest = self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/remotes/origin/master", latest)
        self.assertEqual(preparation_source(self.root, self.base, deployed), latest)
        self.git("checkout", "--detach", self.base)
        self.commit("other-delivery.txt", "not yet integrated\n")
        with self.assertRaisesRegex(InfrastructureError, "integrate that delivery"):
            preparation_source(self.root, self.base, self.git("rev-parse", "HEAD"))
        with self.assertRaisesRegex(InfrastructureError, "actual deployed source"):
            preparation_source(self.root, self.base, "unknown-source")

    def test_fetch_resume_survives_unrelated_commit_but_not_changed_collection_inputs(self):
        self.commit("README.md", "new documentation\n")
        current = self.git("rev-parse", "HEAD")
        self.assertTrue(checkpoint.compatible_source(self.root, self.base, current))
        value = checkpoint.new_checkpoint("owner/repo", self.base, ["standard"], ["standard"])
        value["operations"]["events/standard"] = "complete"
        path = Path(self.temp.name) / "checkpoint.json"
        checkpoint._write(path, value)
        with patch.object(Path, "cwd", return_value=self.root):
            self.assertEqual(checkpoint.main(["rebind", "--checkpoint", str(path), "--repository", "owner/repo",
                "--source", self.base, "--commit", current, "--event-formats", "standard", "--match-formats", "standard"]), 0)
        carried = checkpoint._load(path)
        self.assertEqual(carried["operations"], value["operations"])
        self.assertEqual(carried["commit"], current)
        self.commit("data/standard/input.json", "changed collection input\n")
        self.assertFalse(checkpoint.compatible_source(self.root, self.base, self.git("rev-parse", "HEAD")))


if __name__ == "__main__":
    unittest.main()
