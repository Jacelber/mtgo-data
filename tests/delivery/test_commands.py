import unittest
from unittest.mock import Mock, patch
from tools.delivery import commands, state


TARGET = "Jacelber/mtgo-data-governance-verification"


def failed_product():
    current = state.initial()
    current["current"] = {"operation": "B", "package": "B", "health": "failed"}
    current["previous"] = {"operation": "A1", "package": "A", "health": "passed"}
    current["packages"] = {name: {"complete": True, "eligible": name == "A", "target": TARGET} for name in ("A", "B")}
    return current


class DispatchTests(unittest.TestCase):
    def test_paused_automatic_dispatch_never_posts_but_task_dispatch_does_not_release(self):
        current = state.request_recovery(failed_product(), intent="restore", failed_operation="B", package="A", reason="Owner restore")
        current = state.end_recovery(current, "restore", reason="Owner canceled this restore")
        archive, pages = Mock(), Mock()
        archive.load_state.return_value = (current, "sha")
        pages.client.api.return_value = {"workflow_runs": []}
        with patch.object(commands, "context", return_value=(archive, pages)):
            self.assertEqual(commands.dispatch(TARGET, "auto", "A", "B", "publish", automatic=True)["state"], "publication_paused")
            pages.client.api.assert_not_called()
            commands.dispatch(TARGET, "task", "A", "B", "publish")
        self.assertEqual(pages.client.api.call_args.kwargs["body"]["inputs"]["automatic"], "false")
        archive.save_state.assert_not_called()

    def test_owner_release_saves_state_without_dispatching_a_publication(self):
        current = failed_product()
        current["automatic_publication_pause"] = {"recovery": "restore", "reason": "Owner restore"}
        archive, pages = Mock(), Mock()
        archive.load_state.return_value = (current, "sha")
        with patch.object(commands, "context", return_value=(archive, pages)):
            result = commands.enable_automatic(TARGET, "restore", "Owner: enable automatic publication")
        self.assertFalse(result["dispatch_started"])
        self.assertIsNone(archive.save_state.call_args.args[0]["automatic_publication_pause"])
        pages.client.api.assert_not_called()

    def test_recovery_intent_survives_submission_failure_and_can_resume(self):
        archive, pages = Mock(), Mock()
        saved = failed_product()
        sequence = []
        archive.load_state.side_effect = lambda: (saved, "observed")
        def save(updated, sha):
            nonlocal saved
            sequence.append("intent")
            saved = updated
        archive.save_state.side_effect = save
        def api(path, **kwargs):
            if kwargs.get("method") == "POST":
                sequence.append("dispatch")
                raise RuntimeError("response unknown")
            return {"workflow_runs": []}
        pages.client.api.side_effect = api
        with patch.object(commands, "context", return_value=(archive, pages)):
            with self.assertRaises(RuntimeError):
                commands.dispatch(TARGET, "restore", "A", "B", "recovery", "B introduced broken link")
            self.assertEqual(sequence, ["intent", "dispatch"])
            self.assertEqual(saved["recovery"]["id"], "restore")
            pages.client.api.side_effect = None
            pages.client.api.return_value = {"workflow_runs": [{"display_title": "restore (recovery)", "status": "queued", "id": 12, "html_url": "run/12"}]}
            self.assertEqual(commands.dispatch(TARGET, "restore", "", None, "resume")["state"], "already_submitted")
            self.assertEqual(sequence, ["intent", "dispatch"])

    def test_running_original_is_queried_instead_of_submitting_another_workflow(self):
        current = failed_product()
        current["pending"] = {"operation": "r", "package": "A", "base": "B", "run": "77"}
        archive, pages = Mock(), Mock()
        archive.load_state.return_value = (current, "sha")
        pages.client.api.return_value = {"status": "in_progress", "id": 77, "html_url": "run/77"}
        with patch.object(commands, "context", return_value=(archive, pages)):
            self.assertEqual(commands.dispatch(TARGET, "r", "", None, "resume")["run"], 77)
        pages.client.api.assert_called_once()
        archive.save_state.assert_not_called()

    def test_stale_publication_never_reaches_workflow_submission(self):
        archive, pages = Mock(), Mock()
        archive.load_state.return_value = (failed_product(), "sha")
        with patch.object(commands, "context", return_value=(archive, pages)):
            with self.assertRaises(state.Conflict):
                commands.dispatch(TARGET, "new", "B", "A1", "publish")
        pages.client.api.assert_not_called()
        archive.save_state.assert_not_called()

    def test_wrong_target_recovery_cannot_leave_a_blocking_intent(self):
        archive, pages = Mock(), Mock()
        current = failed_product()
        current["packages"]["A"]["target"] = "another/repo"
        archive.load_state.return_value = (current, "sha")
        with patch.object(commands, "context", return_value=(archive, pages)):
            with self.assertRaises(state.Conflict):
                commands.dispatch(TARGET, "r", "A", "B", "recovery", "broken B")
        archive.save_state.assert_not_called()
        pages.client.api.assert_not_called()
