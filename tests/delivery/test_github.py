import base64
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.delivery.github import APIError, GitHub
from tools.delivery.state import Conflict, initial


class GitHubTests(unittest.TestCase):
    def test_uploaded_assets_without_platform_digest_are_read_before_registration(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "manifest.json").write_text(json.dumps({"id": "pages-" + "a" * 64}))
                (root / "product.tar.gz").write_bytes(b"original selected archive")
                client = GitHub("owner/archive")
                release = {"id": 9, "draft": True, "html_url": "private-release", "assets": []}
                uploaded = {**release, "assets": [{"name": name, "state": "uploaded"} for name in ("product.tar.gz", "manifest.json")]}
                seen = []
                def transport(arguments):
                    if arguments[1] == "download":
                        name = arguments[arguments.index("--pattern") + 1]
                        seen.append(name)
                        destination = Path(arguments[arguments.index("--dir") + 1]) / name
                        destination.write_bytes(b"damaged" if corrupt and name == "product.tar.gz" else (root / name).read_bytes())
                    return ""
                with patch.object(client, "private"), patch("tools.delivery.github.packages.verify"), patch.object(client, "release", side_effect=[release, uploaded]), patch.object(client, "command", side_effect=transport), patch.object(client, "api", return_value={**uploaded, "draft": False}), patch.object(client, "load_state", return_value=(initial(), "sha")), patch.object(client, "save_state") as saved:
                    if corrupt:
                        with self.assertRaises(APIError):
                            client.archive(root, target="owner/product")
                        saved.assert_not_called()
                    else:
                        self.assertEqual(client.archive(root, target="owner/product")["state"], "archived")
                        self.assertEqual(set(seen), {"product.tar.gz", "manifest.json"})
                        self.assertTrue(saved.call_args.args[0]["packages"]["pages-" + "a" * 64]["complete"])

    def test_existing_draft_is_found_when_tag_endpoint_returns_404(self):
        client = GitHub("owner/archive")
        identifier = "pages-" + "a" * 64
        draft = {"id": 123, "tag_name": identifier, "draft": True, "assets": []}
        with patch.object(client, "api", side_effect=[APIError("not found", 404), [draft]]) as actual:
            self.assertEqual(client.release(identifier), draft)
            self.assertEqual(actual.call_count, 2)

    def test_new_candidate_is_absent_only_after_draft_lookup(self):
        client = GitHub("owner/archive")
        with patch.object(client, "api", side_effect=[APIError("not found", 404), []]):
            self.assertIsNone(client.release("pages-" + "b" * 64))

    def test_state_write_uses_observed_sha_and_conflict_does_not_retry(self):
        client = GitHub("owner/archive")
        with patch.object(client, "api", side_effect=APIError("conflict", 409)) as actual:
            with self.assertRaises(Conflict):
                client.save_state(initial(), "observed-sha")
            actual.assert_called_once()
            self.assertEqual(actual.call_args.kwargs["body"]["sha"], "observed-sha")

    def test_query_500_stays_execution_failure_and_can_be_queried_again(self):
        client = GitHub("owner/archive")
        document = {"sha": "current-sha", "content": base64.b64encode(json.dumps(initial()).encode()).decode()}
        with patch.object(client, "api", side_effect=[APIError("unavailable", 500), document]) as actual:
            with self.assertRaises(APIError):
                client.load_state()
            self.assertEqual(client.load_state()[1], "current-sha")
            self.assertEqual(actual.call_count, 2)
            self.assertTrue(all("method" not in call.kwargs for call in actual.call_args_list))

    def test_state_missing_is_initial_but_permission_failure_is_not(self):
        client = GitHub("owner/archive")
        with patch.object(client, "api", side_effect=APIError("missing", 404)):
            self.assertEqual(client.load_state(), (initial(), None))
        with patch.object(client, "api", side_effect=APIError("forbidden", 403)):
            with self.assertRaises(APIError):
                client.load_state()

    def test_archive_refuses_public_repository_before_upload(self):
        client = GitHub("owner/archive")
        with patch.object(client, "api", return_value={"private": False}):
            with self.assertRaises(APIError):
                client.private()

    def test_verification_state_cannot_modify_production_record(self):
        client = GitHub("owner/archive", state_path="state/verification-pages.json")
        with patch.object(client, "api", return_value={"content": {"sha": "new"}}) as actual:
            client.save_state(initial(), None)
            self.assertEqual(actual.call_args.args[0], "repos/owner/archive/contents/state/verification-pages.json")

    def test_cleanup_conflict_never_deletes_a_newly_needed_package(self):
        client = GitHub("owner/archive")
        current = initial()
        current["packages"]["old"] = {"complete": True, "active": False, "ended_at": "2020-01-01T00:00:00Z", "release": 9}
        with patch.object(client, "private"), patch.object(client, "load_state", return_value=(current, "old-sha")), patch.object(client, "save_state", side_effect=Conflict("another writer claimed it")), patch.object(client, "release") as release:
            with self.assertRaises(Conflict):
                client.prune(execute=True)
            release.assert_not_called()

    def test_cleanup_timeout_keeps_exclusion_then_resumes_without_redeleting(self):
        client = GitHub("owner/archive")
        current = initial()
        current["packages"]["old"] = {"complete": True, "active": False, "ended_at": "2020-01-01T00:00:00Z", "release": 9}
        def save(value, sha):
            nonlocal current
            current = deepcopy(value)
            return "new-sha"
        with patch.object(client, "private"), patch.object(client, "load_state", side_effect=lambda: (deepcopy(current), "sha")), patch.object(client, "save_state", side_effect=save), patch.object(client, "release", return_value={"id": 9}) as release, patch.object(client, "api", side_effect=APIError("response unknown", 500)) as api:
            with self.assertRaises(APIError):
                client.prune(execute=True)
            self.assertTrue(current["packages"]["old"]["deleting"])
            self.assertFalse(current["packages"]["old"]["complete"])
            release.return_value = None  # The first DELETE actually completed.
            api.reset_mock()
            self.assertEqual(client.prune(execute=True)["removed"], ["old"])
            api.assert_not_called()
            self.assertNotIn("old", current["packages"])


if __name__ == "__main__":
    unittest.main()
