from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.delivery import packages, parts
from tools.delivery.github import APIError


class Archive:
    repository = "owner/private"

    def __init__(self, files):
        self.files = dict(files)
        self.deleted = []
        self.uploads = 0
        self.fail_after_upload = False
        self.fail_delete = False
        self.remote_digest = None
        self.registered = False

    def private(self):
        pass

    def release(self, identifier):
        return {"id": 9, "draft": True, "assets": [
            {"id": name, "name": name, "state": "uploaded", "size": len(content),
             "digest": self.remote_digest if name == "product.tar.gz" else None}
            for name, content in self.files.items()]}

    def command(self, arguments):
        if arguments[1] == "download":
            name = arguments[arguments.index("--pattern") + 1]
            root = Path(arguments[arguments.index("--dir") + 1])
            (root / name).write_bytes(self.files[name])
        elif arguments[1] == "upload":
            package = Path(arguments[3])
            self.files[package.name] = package.read_bytes()
            self.uploads += 1
            if self.fail_after_upload:
                self.fail_after_upload = False
                raise APIError("Upload response lost")
        else:
            raise AssertionError(arguments)
        return ""

    def api(self, path, *, method):
        assert method == "DELETE"
        if self.fail_delete:
            self.fail_delete = False
            raise APIError("Delete unavailable")
        name = path.rsplit("/", 1)[1]
        self.deleted.append(name)
        del self.files[name]

    def archive(self, root, *, target):
        assert set(self.files) == {"product.tar.gz", "manifest.json"}
        manifest = json.loads((root / "manifest.json").read_text())
        packages.verify(root / "product.tar.gz", manifest, target=target)
        assert self.files["product.tar.gz"] == (root / "product.tar.gz").read_bytes()
        self.registered = True
        return {"state": "archived", "id": manifest["id"]}


class PartsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        site = self.root / "site"
        for name, content in {"index.html": "accepted", "melee/index.html": "tabletop",
                              "stats/catalog.json": '{"formats": []}'}.items():
            p = site / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        self.target = "owner/product"
        self.candidate = self.root / "candidate"
        self.manifest = packages.prepare(site, self.candidate, target=self.target, source="accepted")
        self.identifier = self.manifest["id"]
        self.patch = patch.object(parts, "PART_BYTES", 128)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        destination = self.root / "parts"
        parts.split(self.candidate, destination, target=self.target)
        self.files = {p.name: p.read_bytes() for p in destination.iterdir()}
        self.names = sorted(set(self.files) - {"manifest.json"})
        self.assertGreater(len(self.names), 1)

    def run_archive(self, client):
        return parts.archive_parts(client, self.identifier, target=self.target)

    def test_round_trip_exact_bytes_with_no_platform_digest(self):
        client = Archive(self.files)
        self.assertEqual(self.run_archive(client)["state"], "archived")
        self.assertEqual(client.files["product.tar.gz"], (self.candidate / "product.tar.gz").read_bytes())
        self.assertEqual(set(client.deleted), set(self.names))

    def test_missing_wrong_size_corrupt_and_unexpected_parts_never_register(self):
        for damage in ("missing", "size", "corrupt", "extra"):
            with self.subTest(damage=damage):
                files = deepcopy(self.files)
                name = self.names[0]
                if damage == "missing":
                    del files[name]
                elif damage == "size":
                    files[name] += b"x"
                elif damage == "corrupt":
                    files[name] = bytes([files[name][0] ^ 1]) + files[name][1:]
                else:
                    files["unrelated.txt"] = b"preserve me"
                client = Archive(files)
                with self.assertRaises((APIError, ValueError)):
                    self.run_archive(client)
                self.assertFalse(client.registered)
                self.assertFalse(client.deleted)
                self.assertEqual(client.uploads, 0)

    def test_wrong_target_identity_and_unbounded_size_rejected(self):
        for field, value in (("target", "other"), ("id", "pages-" + "0" * 64),
                             ("bytes", packages.MAX_BYTES + 1), ("bytes", True)):
            with self.subTest(field=field, value=value):
                manifest = {**self.manifest, field: value}
                client = Archive({**self.files, "manifest.json": json.dumps(manifest).encode()})
                with self.assertRaises(ValueError):
                    self.run_archive(client)
                self.assertEqual(client.uploads, 0)

    def test_lost_upload_response_resumes_existing_full_file(self):
        client = Archive(self.files)
        client.fail_after_upload = True
        with self.assertRaises(APIError):
            self.run_archive(client)
        self.assertFalse(client.deleted)
        self.run_archive(client)
        self.assertEqual(client.uploads, 1)
        self.assertTrue(client.registered)

    def test_partial_cleanup_resumes_without_requiring_all_parts(self):
        client = Archive(self.files)
        client.fail_delete = True
        with self.assertRaises(APIError):
            self.run_archive(client)
        del client.files[self.names[0]]
        self.run_archive(client)
        self.assertEqual(client.uploads, 1)
        self.assertTrue(client.registered)

    def test_wrong_remote_digest_preserves_handoff(self):
        client = Archive(self.files)
        client.remote_digest = "sha256:" + "0" * 64
        with self.assertRaises(APIError):
            self.run_archive(client)
        self.assertFalse(client.deleted)
        self.assertFalse(client.registered)

    def test_existing_damaged_full_file_is_never_overwritten(self):
        content = (self.candidate / "product.tar.gz").read_bytes()
        client = Archive({**self.files, "product.tar.gz": b"x" + content[1:]})
        with self.assertRaises(ValueError):
            self.run_archive(client)
        self.assertEqual(client.uploads, 0)
        self.assertFalse(client.deleted)

    def test_split_does_not_overwrite_an_existing_handoff(self):
        with self.assertRaises(FileExistsError):
            parts.split(self.candidate, self.root / "parts", target=self.target)
