from datetime import datetime, timezone
import unittest

from tools.delivery import state as flow


def baseline():
    state = flow.initial()
    state["current"] = {"operation": "deploy-A-1", "package": "A", "remote": "1", "health": "passed"}
    state["packages"] = {name: {"complete": True, "eligible": name == "A", "active": False,
                               "published_at": "2020-01-01T00:00:00Z"} for name in ("A", "B", "C", "old")}
    return state


def failed_b():
    state = flow.claim(baseline(), operation="deploy-B", package="B", base="deploy-A-1")
    state = flow.sending(state, "deploy-B")
    state = flow.deployed(state, "deploy-B", "2")
    return flow.confirmed(state, "deploy-B", health="failed", observed_operation="deploy-B")


class WriterTests(unittest.TestCase):
    def test_actual_deployment_precedes_health_and_preserves_previous(self):
        state = flow.claim(baseline(), operation="deploy-B", package="B", base="deploy-A-1")
        state = flow.deployed(flow.sending(state, "deploy-B"), "deploy-B", "2")
        self.assertEqual(state["current"]["package"], "B")
        self.assertEqual(state["current"]["health"], "unknown")
        self.assertEqual(state["previous"]["package"], "A")
        state = flow.deployed(state, "deploy-B", "2")
        self.assertEqual(state["previous"]["package"], "A")
        state = flow.confirmed(state, "deploy-B", health="failed", observed_operation="deploy-B")
        self.assertFalse(state["packages"]["B"]["eligible"])
        self.assertEqual(state["previous"]["package"], "A")

    def test_unknown_request_cannot_be_replayed_or_cleared_by_not_found(self):
        state = flow.claim(baseline(), operation="B", package="B", base="deploy-A-1")
        state = flow.sending(state, "B")
        with self.assertRaises(flow.Conflict):
            flow.sending(state, "B")
        with self.assertRaises(flow.Conflict):
            flow.no_write(state, "B", terminal_without_write=False)
        with self.assertRaises(flow.Conflict):
            flow.claim(state, operation="C", package="C", base="deploy-A-1")

    def test_recovery_survives_queue_cancellation_and_blocks_normal_writer(self):
        state = flow.request_recovery(failed_b(), intent="restore-A", failed_operation="deploy-B", package="A", reason="new B breaks navigation; A provides it")
        with self.assertRaises(flow.Conflict):
            flow.claim(state, operation="C", package="C", base="deploy-B")
        state = flow.claim(state, operation="restore-1", package="A", base="deploy-B", recovery="restore-A")
        state = flow.no_write(state, "restore-1", terminal_without_write=True)
        self.assertEqual(state["recovery"]["id"], "restore-A")
        state = flow.claim(state, operation="restore-2", package="A", base="deploy-B", recovery="restore-A")
        state = flow.deployed(flow.sending(state, "restore-2"), "restore-2", "3")
        state = flow.confirmed(state, "restore-2", health="passed", observed_operation="restore-2")
        self.assertIsNone(state["recovery"])
        with self.assertRaises(flow.Conflict):
            flow.claim(state, operation="old-C", package="C", base="deploy-A-1")
        state = flow.claim(state, operation="new-C", package="C", base="restore-2")
        self.assertEqual(state["pending"]["operation"], "new-C")

    def test_current_base_does_not_make_a_known_bad_package_publishable(self):
        current = failed_b()
        with self.assertRaises(flow.Conflict):
            flow.claim(current, operation="repeat-B", package="B", base="deploy-B")
        self.assertEqual(flow.claim(current, operation="fixed-C", package="C", base="deploy-B")["pending"]["package"], "C")

    def test_recovery_does_not_choose_an_older_package_or_missing_predecessor(self):
        for state, package in [(baseline(), "A"), (failed_b(), "old")]:
            with self.assertRaises(flow.Conflict):
                flow.request_recovery(state, intent="r", failed_operation=flow.current_id(state), package=package, reason="failure")

    def test_intent_withdrawal_requires_remote_resolution_and_releases_block(self):
        state = flow.request_recovery(failed_b(), intent="r", failed_operation="deploy-B", package="A", reason="failure")
        pending = flow.claim(state, operation="r1", package="A", base="deploy-B", recovery="r")
        with self.assertRaises(flow.Conflict):
            flow.end_recovery(pending, "r", reason="Owner canceled")
        state = flow.end_recovery(state, "r", reason="Owner withdrew before any request")
        self.assertEqual(flow.claim(state, operation="C", package="C", base="deploy-B")["pending"]["package"], "C")

    def test_cleanup_pins_current_previous_and_active_candidate_regardless_of_age(self):
        state = failed_b()
        state["packages"]["C"]["active"] = True
        self.assertEqual(flow.expired_packages(state, datetime(2026, 9, 12, tzinfo=timezone.utc)), ["old"])

    def test_owner_restore_needs_no_failure_verdict_and_pause_survives_repair_publication(self):
        current = flow.claim(baseline(), operation="B", package="B", base="deploy-A-1")
        current = flow.deployed(flow.sending(current, "B"), "B", "2")
        current = flow.confirmed(current, "B", health="passed", observed_operation="B")
        self.assertFalse(current["packages"]["B"]["active"])
        current = flow.request_recovery(current, intent="restore", failed_operation="B", package="A", reason="Owner: restore the previous version")
        with self.assertRaises(flow.Conflict):
            flow.enable_automatic_publication(current, recovery="restore", reason="Owner release")
        current = flow.claim(current, operation="restore", package="A", base="B", recovery="restore")
        current = flow.deployed(flow.sending(current, "restore"), "restore", "3")
        current = flow.confirmed(current, "restore", health="passed", observed_operation="restore")
        self.assertEqual(current["previous"]["package"], "A")
        self.assertIsNone(current["recovery"])
        with self.assertRaises(flow.Conflict):
            flow.claim(current, operation="auto-C", package="C", base="restore", automatic=True)
        current = flow.claim(current, operation="task-C", package="C", base="restore")
        current = flow.deployed(flow.sending(current, "task-C"), "task-C", "4")
        current = flow.confirmed(current, "task-C", health="passed", observed_operation="task-C")
        self.assertEqual(current["automatic_publication_pause"]["recovery"], "restore")
        with self.assertRaises(flow.Conflict):
            flow.enable_automatic_publication(current, recovery="older-restore", reason="old instruction")
        current = flow.enable_automatic_publication(current, recovery="restore", reason="Owner: resume automatic publication")
        self.assertIsNone(current["pending"])
        self.assertEqual(flow.claim(current, operation="auto-C", package="C", base="task-C", automatic=True)["pending"]["operation"], "auto-C")

    def test_restore_pause_stops_an_already_claimed_automatic_write(self):
        current = failed_b()
        current = flow.claim(current, operation="auto-C", package="C", base="deploy-B", automatic=True)
        current = flow.request_recovery(current, intent="restore", failed_operation="deploy-B", package="A", reason="Owner restore")
        with self.assertRaises(flow.Conflict):
            flow.sending(current, "auto-C")
        with self.assertRaises(flow.Conflict):
            flow.claim(current, operation="auto-C", package="C", base="deploy-B", automatic=False)
        current = flow.no_write(current, "auto-C", terminal_without_write=True)
        current = flow.end_recovery(current, "restore", reason="Owner withdrew recovery only")
        self.assertIsNotNone(current["automatic_publication_pause"])
        with self.assertRaises(flow.Conflict):
            flow.claim(current, operation="auto-D", package="C", base="deploy-B", automatic=True)

    def test_publication_time_and_candidate_end_do_not_discard_fixed_versions(self):
        current = baseline()
        del current["packages"]["B"]["published_at"]
        current = flow.deployed(flow.sending(flow.claim(current, operation="B", package="B", base="deploy-A-1"), "B"), "B", "2")
        published = current["packages"]["B"]["published_at"]
        self.assertTrue(published)
        with self.assertRaises(flow.Conflict):
            flow.end_candidate(current, "B", reason="still confirming")
        current = flow.confirmed(current, "B", health="passed", observed_operation="B")
        current = flow.end_candidate(current, "B", reason="delivery complete")
        self.assertEqual(current["packages"]["B"]["published_at"], published)
        expired = flow.expired_packages(current, datetime(2099, 1, 1, tzinfo=timezone.utc))
        self.assertNotIn("B", expired)
        self.assertNotIn("A", expired)


if __name__ == "__main__":
    unittest.main()
