import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from tools.delivery import packages, parts
from tools.delivery.github import APIError
from tests.delivery import test_parts as fixtures


class GitArchive:
    repository = "owner/private"
    commit = "a" * 40
    tree = "b" * 40

    def __init__(self, files):
        self.entries, self.blobs = [], {}
        self.registered = False
        self.public = False
        self.truncated = False
        for name, data in files.items():
            sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            self.entries.append({"path": name, "mode": "100644", "type": "blob", "size": len(data), "sha": sha})
            self.blobs[sha] = {"sha": sha, "size": len(data), "encoding": "base64", "content": base64.b64encode(data).decode()}

    def private(self):
        if self.public:
            raise APIError("Must be private")

    def api(self, path):
        suffix = path.split("/git/", 1)[1]
        if suffix == "commits/" + self.commit:
            return {"sha": self.commit, "tree": {"sha": self.tree}}
        if suffix == "trees/" + self.tree:
            return {"tree": self.entries, "truncated": self.truncated}
        if suffix.startswith("blobs/"):
            return self.blobs[suffix.removeprefix("blobs/")]
        raise AssertionError(path)

    def archive(self, root, *, target):
        manifest = json.loads((root / "manifest.json").read_bytes())
        packages.verify(root / "product.tar.gz", manifest, target=target)
        self.package = (root / "product.tar.gz").read_bytes()
        self.registered = True
        return {"id": manifest["id"], "state": "archived"}


class GitPartsTests(unittest.TestCase):
    setUp = fixtures.PartsTests.setUp

    def run_archive(self, client, commit=None):
        return parts.archive_git_parts(client, self.identifier, commit or client.commit, target=self.target)

    def test_exact_private_bytes_reach_original_archiver(self):
        client = GitArchive(self.files)
        self.assertEqual(self.run_archive(client)["id"], self.identifier)
        self.assertEqual(client.package, (self.candidate / "product.tar.gz").read_bytes())

    def test_mutable_ref_and_public_repository_are_rejected(self):
        client = GitArchive(self.files)
        with self.assertRaises(ValueError):
            self.run_archive(client, "refs/heads/handoff")
        client.public = True
        with self.assertRaises(APIError):
            self.run_archive(client)
        self.assertFalse(client.registered)

    def test_membership_metadata_and_content_damage_never_reach_archiver(self):
        for damage in ("missing", "extra", "size", "symlink", "duplicate", "truncated", "blob", "encoding"):
            with self.subTest(damage=damage):
                client = GitArchive(self.files)
                part = next(e for e in client.entries if e["path"] == self.names[0])
                if damage == "missing":
                    client.entries.remove(part)
                elif damage == "extra":
                    client.entries.append({**part, "path": "execute.py"})
                elif damage == "size":
                    part["size"] += 1
                elif damage == "symlink":
                    part["mode"] = "120000"
                elif damage == "duplicate":
                    client.entries.append(deepcopy(part))
                elif damage == "truncated":
                    client.truncated = True
                elif damage == "blob":
                    client.blobs[part["sha"]]["content"] = base64.b64encode(b"x" * part["size"]).decode()
                else:
                    client.blobs[part["sha"]]["encoding"] = "utf-8"
                with self.assertRaises((APIError, ValueError)):
                    self.run_archive(client)
                self.assertFalse(client.registered)

    def test_wrong_target_manifest_and_valid_git_blob_with_corrupt_package_are_rejected(self):
        for damage in ("target", "package"):
            with self.subTest(damage=damage):
                files = dict(self.files)
                if damage == "target":
                    files["manifest.json"] = json.dumps({**self.manifest, "target": "other/product"}).encode()
                else:
                    data = files[self.names[0]]
                    files[self.names[0]] = bytes([data[0] ^ 1]) + data[1:]
                client = GitArchive(files)
                with self.assertRaises((APIError, ValueError)):
                    self.run_archive(client)
                self.assertFalse(client.registered)
