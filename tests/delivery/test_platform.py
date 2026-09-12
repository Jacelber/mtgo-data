import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools import pages_writer
from tools import project
from tools.delivery import commands
from tools.delivery import packages, state
from tools.delivery.platform import Pages, observe_content


class PlatformTests(unittest.TestCase):
    def test_terminal_failed_write_keeps_unknown_service_and_allows_owner_restore(self):
        current = state.initial()
        current["current"] = {"operation": "A", "package": "A", "health": "passed", "remote": {"deployment_id": "1"}}
        current["packages"] = {"A": {"complete": True, "eligible": True}, "B": {"complete": True}}
        current = state.bind_remote(state.sending(state.claim(current, operation="B", package="B", base="A"), "B"), "B", {"pages_id": "known-request"})
        current["pending"].update(run="7", attempt="1")
        archive, pages = Mock(), Mock()
        archive.load_state.return_value = (current, "state-sha")
        pages.query.return_value = {"status": "deployment_failed"}
        pages.operation_record.return_value = "2"
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "manifest.json").write_text(json.dumps({"id": "B"}))
            argv = ["writer", "--operation", "B", "settle-completed", "--candidate", directory]
            with patch.object(pages_writer, "context", return_value=(archive, pages)), patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO), patch.object(packages, "verify"), patch.object(pages_writer, "observe_content", return_value={"state": "unconfirmed", "mismatches": ["index.html"]}):
                self.assertEqual(pages_writer.main(), 0)
        result = archive.save_state.call_args.args[0]
        self.assertIsNone(result["pending"])
        self.assertIsNone(result["recovery"])
        self.assertEqual(result["current"]["platform_status"], "deployment_failed")
        self.assertEqual(result["current"]["health"], "unknown")
        self.assertEqual(result["previous"]["package"], "A")
        self.assertEqual(state.request_recovery(result, intent="r", failed_operation="B", package="A", reason="Owner restore")["recovery"]["package"], "A")
        pages.create.assert_not_called()

    def test_unavailable_resource_is_unknown_not_a_product_failure_verdict(self):
        with patch("tools.delivery.platform.urlopen", side_effect=OSError("temporary service failure")):
            result = observe_content("https://example.invalid", {"probes": {"index.html": "unused"}}, "op")
        self.assertEqual(result["state"], "unconfirmed")
        self.assertIn("unavailable", result["mismatches"][0])

    def test_completed_mixed_service_can_be_reported_without_automatic_rollback(self):
        current = state.initial()
        current["current"] = {"operation": "A", "package": "A", "health": "passed", "remote": "1"}
        current["packages"] = {"A": {"complete": True, "eligible": True}, "B": {"complete": True}}
        current = state.claim(current, operation="B", package="B", base="A")
        current = state.sending(current, "B")
        remote = {"pages_id": "sha", "deployment_id": "2"}
        current = state.deployed(current, "B", remote)
        current["pending"].update(run="7", attempt="1")
        archive, pages = Mock(), Mock()
        archive.load_state.return_value = (current, "state-sha")
        pages.query.return_value = {"status": "succeed"}
        pages.operation_record.return_value = "2"
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory)
            (candidate / "manifest.json").write_text(json.dumps({"id": "B"}))
            argv = ["writer", "--operation", "B", "settle-completed", "--candidate", directory]
            observation = {"state": "unconfirmed", "mismatches": ["melee/index.html"]}
            with patch.object(pages_writer, "context", return_value=(archive, pages)), patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO), patch.object(packages, "verify"), patch.object(pages_writer, "observe_content", return_value=observation):
                self.assertEqual(pages_writer.main(), 0)
                updated = archive.save_state.call_args.args[0]
                self.assertIsNone(updated["pending"])
                self.assertIsNone(updated["recovery"])
                self.assertEqual(updated["current"]["health"], "unknown")
                self.assertEqual(updated["current"]["service_observation"], observation)
                self.assertEqual(updated["previous"]["package"], "A")
                self.assertEqual(state.request_recovery(updated, intent="r", failed_operation="B", package="A", reason="Owner restore")["recovery"]["package"], "A")
                archive.save_state.reset_mock()
                pages.query.return_value = {"status": "in_progress"}
                self.assertEqual(pages_writer.main(), 2)
                archive.save_state.assert_not_called()
        pages.create.assert_not_called()

    def test_intentional_pause_skips_cloud_request_and_claim_without_marking_failure(self):
        for command, extra in (("request", []), ("claim", ["--output", "unused"] )):
            current = state.initial()
            current["automatic_publication_pause"] = {"recovery": "restore", "reason": "Owner restore"}
            archive, pages = Mock(), Mock()
            archive.load_state.return_value = (current, "sha")
            argv = ["writer", "--operation", "automatic", command, "--package", "B", "--automatic", *extra]
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "output"
                with patch.object(pages_writer, "context", return_value=(archive, pages)), patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO) as report, patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}):
                    self.assertEqual(pages_writer.main(), 0)
                self.assertEqual(json.loads(report.getvalue())["state"], "publication_paused")
                self.assertIn("allowed=false", output.read_text())
            archive.retrieve.assert_not_called()
            archive.save_state.assert_not_called()
            pages.create.assert_not_called()

    def test_transport_keeps_every_selected_tar_byte_including_hidden_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "site"
            for relative in packages.PROBES:
                path = site / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("synthetic input")
            candidate = root / "candidate"
            manifest = packages.prepare(site, candidate, target="target", source="source")
            transport = root / "transport" / "artifact.tar"
            packages.pages_transport(candidate / "product.tar.gz", manifest, transport, target="target")
            with gzip.open(candidate / "product.tar.gz", "rb") as source:
                self.assertEqual(hashlib.file_digest(source, "sha256").hexdigest(), packages.sha256(transport))
            self.assertIn(packages.VERSION_FILE, packages.inspect(transport)["probes"])
            with self.assertRaises(ValueError):
                packages.pages_transport(candidate / "product.tar.gz", manifest, transport, target="another")

    def test_unknown_or_new_external_deployment_blocks_stale_write(self):
        pages = Pages("owner/repo")
        records = [{"id": 2, "sha": "new"}, {"id": 1, "sha": "old"}]
        for remote_status in ("in_progress", "success"):
            with patch.object(pages.client, "api", side_effect=[records, [{"state": remote_status}]]):
                with self.assertRaises(state.Conflict):
                    pages.current(expected="1")

    def test_own_waiting_environment_does_not_hide_previous_actual_base(self):
        pages = Pages("owner/repo")
        results = [[{"id": 2, "sha": "same"}, {"id": 1, "sha": "old"}],
                   [{"state": "in_progress", "log_url": "https://github.com/owner/repo/actions/runs/5/job/6"}],
                   [{"state": "success"}]]
        with patch.object(pages.client, "api", side_effect=results):
            self.assertEqual(pages.current(expected="1", own_run="5")["id"], "1")

    def test_service_probe_reports_difference_without_declaring_product_failure(self):
        manifest = {"probes": {"index.html": hashlib.sha256(b"expected").hexdigest()}}
        with patch("tools.delivery.platform.urlopen", return_value=io.BytesIO(b"different")):
            self.assertEqual(observe_content("https://example.test", manifest, "op"),
                             {"state": "unconfirmed", "mismatches": ["index.html"]})
        with patch("tools.delivery.platform.urlopen", return_value=io.BytesIO(b"expected")):
            self.assertEqual(observe_content("https://example.test", manifest, "op")["state"], "matching")

    def test_failed_stale_request_that_never_sent_does_not_block_later_valid_work(self):
        pages = Pages("owner/repo")
        responses = [[{"id": 2, "sha": "new"}, {"id": 1, "sha": "old"}],
                     [{"state": "failure", "log_url": "https://github.com/owner/repo/actions/runs/5/job/6"}],
                     {"name": "Deploy selected product", "status": "completed", "steps": [
                         {"name": "Send selected package once", "conclusion": "skipped"}]},
                     [{"state": "success"}]]
        with patch.object(pages.client, "api", side_effect=responses):
            self.assertEqual(pages.current(expected="1")["id"], "1")

    def test_failed_or_unknown_send_is_not_treated_as_no_send(self):
        pages = Pages("owner/repo")
        for conclusion in ("failure", None, "cancelled"):
            with patch.object(pages.client, "api", return_value={"name": "Deploy selected product", "status": "completed", "steps": [
                {"name": "Send selected package once", "conclusion": conclusion}]}):
                self.assertFalse(pages.no_send_job("https://github.com/owner/repo/actions/runs/5/job/6"))

    def test_status_and_missing_response_never_write_or_resend(self):
        for remote in (None, {"pages_id": "remote-1"}):
            current = state.initial()
            current["pending"] = {"operation": "op", "remote": remote, "run": "1", "attempt": "1"}
            with patch.object(pages_writer, "context") as context, patch("sys.argv", ["writer", "--operation", "op", "status"]), patch("sys.stdout", new_callable=io.StringIO):
                archive, pages = context.return_value = (Mock(), Mock())
                archive.load_state.return_value = (current, "sha")
                pages.query.return_value = {"status": "succeed"}
                pages_writer.main()
                archive.save_state.assert_not_called()
                pages.create.assert_not_called()

    def test_invalid_operation_is_rejected_before_using_credentials_or_paths(self):
        with patch.object(pages_writer, "context") as context, patch("sys.argv", ["writer", "--operation", "../bad", "status"]), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(pages_writer.main(), 2)
            context.assert_not_called()

    def test_unsent_resolution_preserves_recovery_and_refuses_unknown_send(self):
        for phase, proven, expected_code in (("claimed", True, 0), ("claimed", False, 2), ("sending", True, 2)):
            current = state.initial()
            current["recovery"] = {"id": "r", "package": "A"}
            current["pending"] = {"operation": "op", "phase": phase, "run": "1", "attempt": "1"}
            archive, pages = Mock(), Mock()
            archive.load_state.return_value = (current, "sha")
            pages.attempt_never_sent.return_value = proven
            with patch.object(pages_writer, "context", return_value=(archive, pages)), patch("sys.argv", ["writer", "--operation", "op", "settle-unsent"]), patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(pages_writer.main(), expected_code)
            if expected_code == 0:
                saved = archive.save_state.call_args.args[0]
                self.assertIsNone(saved["pending"])
                self.assertEqual(saved["recovery"]["id"], "r")
            else:
                archive.save_state.assert_not_called()
            pages.create.assert_not_called()

    def test_claim_continuation_records_new_carrier_only_after_old_send_is_excluded(self):
        target = "Jacelber/mtgo-data"
        for proven in (False, True):
            current = state.initial()
            current["packages"]["A"] = {"complete": True, "target": target}
            current = state.claim(current, operation="op", package="A", base=None)
            current["pending"].update(run="1", attempt="1")
            archive, pages = Mock(), Mock()
            archive.load_state.return_value = (current, "sha")
            pages.attempt_never_sent.return_value = proven
            # End at retrieval: no product generation or actual remote writing is needed.
            archive.retrieve.side_effect = RuntimeError("retrieval reached")
            with tempfile.TemporaryDirectory() as temporary:
                with patch.object(pages_writer, "context", return_value=(archive, pages)), patch.dict(os.environ, {"GITHUB_RUN_ID": "2", "GITHUB_RUN_ATTEMPT": "1"}), patch("sys.argv", ["writer", "--operation", "op", "claim", "--package", "A", "--output", str(Path(temporary) / "transport")]), patch("sys.stdout", new_callable=io.StringIO):
                    if proven:
                        with self.assertRaisesRegex(RuntimeError, "retrieval reached"):
                            pages_writer.main()
                    else:
                        self.assertEqual(pages_writer.main(), 2)
            if proven:
                self.assertEqual(archive.save_state.call_args.args[0]["pending"]["run"], "2")
            else:
                archive.save_state.assert_not_called()

    def test_running_attempt_is_not_a_proof_that_it_will_never_send(self):
        pages = Pages("owner/repo")
        for job_status, conclusion, expected in (("in_progress", "skipped", False), ("completed", "skipped", True), ("completed", "cancelled", False)):
            job = {"name": "Deploy selected product", "status": job_status, "steps": [{"name": "Send selected package once", "conclusion": conclusion}]}
            with patch.object(pages.client, "api", return_value={"jobs": [job]}):
                self.assertEqual(pages.attempt_never_sent("1", "1"), expected)


class CompletedResumeTests(unittest.TestCase):
    """Exercise the ended-write state through both real command entry points."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.candidate = root / "candidate"
        site = root / "site"
        for relative in packages.PROBES:
            path = site / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("selected product", encoding="utf-8")
        self.target = "Jacelber/mtgo-data"
        self.manifest = packages.prepare(site, self.candidate, target=self.target, source="synthetic")
        self.package = self.manifest["id"]
        self.saved = state.initial()
        self.saved["current"] = {"operation": "A", "package": "A", "health": "passed"}
        self.saved["packages"] = {"A": {"complete": True, "eligible": True},
            self.package: {"complete": True, "target": self.target}}
        self.saved = state.sending(state.claim(self.saved, operation="B", package=self.package, base="A"), "B")
        self.saved = state.bind_remote(self.saved, "B", {"pages_id": "original-request"})
        self.saved["pending"].update(run="7", attempt="1")
        self.archive, self.pages = Mock(), Mock()
        self.archive.load_state.side_effect = lambda: (self.saved, "sha")
        self.archive.save_state.side_effect = self.save
        self.archive.retrieve.return_value = self.manifest
        self.pages.query.return_value = {"status": "succeed"}
        self.pages.operation_record.return_value = "2"
        self.observation = {"state": "unconfirmed", "mismatches": ["index.html"]}
        self.addCleanup(patch.stopall)
        patch.object(pages_writer, "context", return_value=(self.archive, self.pages)).start()
        patch.object(commands, "context", return_value=(self.archive, self.pages)).start()
        patch.object(pages_writer, "observe_content", side_effect=lambda *args: self.observation).start()

    def save(self, updated, sha):
        self.assertEqual(sha, "sha")
        self.saved = updated
        return "sha"

    def invoke(self, entry, command="resume"):
        with patch("sys.stdout", new_callable=io.StringIO) as report:
            if entry == "writer":
                with patch("sys.argv", ["writer", "--operation", "B", command, "--candidate", str(self.candidate)]):
                    code = pages_writer.main()
            else:
                code = project.main(["resume", "--operation", "B"])
        return code, json.loads(report.getvalue())

    def settle(self):
        self.assertEqual(self.invoke("writer", "settle-completed")[0], 0)
        self.assertIsNone(self.saved["pending"])
        self.assertEqual(self.saved["current"]["health"], "unknown")
        self.archive.save_state.reset_mock()
        self.pages.query.reset_mock()

    def test_settle_then_both_resumes_preserve_unknown_confirm_and_reuse(self):
        self.settle()
        for entry in ("writer", "project"):
            code, result = self.invoke(entry)
            self.assertEqual((code, result["state"]), (3, "unconfirmed"))
            self.assertEqual(self.saved["current"]["health"], "unknown")
        self.assertEqual(self.pages.query.call_count, 2)
        self.pages.query.assert_called_with("original-request")
        self.archive.save_state.assert_not_called()
        self.archive.retrieve.assert_called_once_with(self.package, unittest.mock.ANY, target=self.target)
        self.observation = {"state": "matching", "mismatches": []}
        self.assertEqual(self.invoke("project")[1]["state"], "confirmed")
        self.assertEqual(self.saved["current"]["health"], "passed")
        self.assertEqual(self.saved["previous"]["package"], "A")
        self.assertTrue(self.saved["packages"][self.package]["eligible"])
        self.assertIsNone(self.saved["pending"])
        self.assertIsNone(self.saved["recovery"])
        self.pages.query.reset_mock()
        self.archive.save_state.reset_mock()
        self.archive.retrieve.reset_mock()
        for entry in ("writer", "project"):
            self.assertEqual(self.invoke(entry), (0, {"state": "already_confirmed", "current": self.saved["current"]}))
        self.pages.query.assert_not_called()
        self.archive.retrieve.assert_not_called()
        self.archive.save_state.assert_not_called()
        self.pages.create.assert_not_called()
        self.pages.cancel.assert_not_called()
        self.pages.client.api.assert_not_called()  # No workflow dispatch, including after unknown.

    def test_known_defect_never_becomes_success_from_matching_bytes(self):
        self.settle()
        self.saved["current"].update(health="failed", defect="known content error")
        self.saved["packages"][self.package]["failed"] = True
        self.observation = {"state": "matching", "mismatches": []}
        for entry in ("writer", "project"):
            code, result = self.invoke(entry)
            self.assertEqual((code, result["state"]), (1, "failed"))
        self.pages.query.assert_not_called()
        self.archive.save_state.assert_not_called()
        self.archive.retrieve.assert_not_called()

    def test_terminal_platform_failure_stays_unknown(self):
        self.pages.query.return_value = {"status": "deployment_failed"}
        self.settle()
        self.observation = {"state": "matching", "mismatches": []}
        for entry in ("writer", "project"):
            code, result = self.invoke(entry)
            self.assertEqual((code, result["state"]), (3, "unknown"))
        self.archive.save_state.assert_not_called()
        self.archive.retrieve.assert_not_called()

    def test_new_write_cannot_be_overwritten_by_old_confirmation(self):
        self.settle()
        self.observation = {"state": "matching", "mismatches": []}
        self.archive.save_state.side_effect = state.Conflict("Writer state changed")
        self.assertEqual(self.invoke("project")[0], 2)
        self.assertEqual(self.saved["current"]["health"], "unknown")
        self.pages.create.assert_not_called()

    def test_other_pending_or_external_deployment_prevents_confirmation(self):
        self.settle()
        self.saved["pending"] = {"operation": "new"}
        self.assertEqual(self.invoke("writer")[0], 2)
        self.pages.query.assert_not_called()
        self.saved["pending"] = None
        self.pages.current.side_effect = state.Conflict("Another deployment changed the production base")
        self.assertEqual(self.invoke("project")[0], 2)
        self.archive.save_state.assert_not_called()

    def test_confirmation_ends_only_its_recovery_and_keeps_automatic_pause(self):
        self.settle()
        self.saved["recovery"] = {"id": "B", "package": self.package}
        pause = {"recovery": "B", "reason": "Owner restore"}
        self.saved["automatic_publication_pause"] = pause
        self.observation = {"state": "matching", "mismatches": []}
        self.assertEqual(self.invoke("writer")[1]["state"], "confirmed")
        self.assertIsNone(self.saved["recovery"])
        self.assertEqual(self.saved["automatic_publication_pause"], pause)


if __name__ == "__main__":
    unittest.main()
