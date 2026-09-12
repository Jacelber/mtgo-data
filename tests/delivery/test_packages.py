import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from tools.delivery import packages


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.site = self.root / "site"
        for name, content in {"index.html": "MTGO", "melee/index.html": "Tabletop", "stats/catalog.json": '{"formats": []}'}.items():
            path = self.site / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_same_selected_content_reuses_exact_bytes_across_workspaces(self):
        first = packages.prepare(self.site, self.root / "first", target="test", source="source-A")
        second = packages.prepare(self.site, self.root / "second", target="test", source="source-B")
        self.assertEqual(first["id"], second["id"])
        packages.extract(self.root / "first/product.tar.gz", first, self.root / "preview", target="test")
        self.assertEqual((self.root / "preview/melee/index.html").read_text(), "Tabletop")

    def test_legitimate_new_content_forms_new_candidate_without_freezing_old_values(self):
        first = packages.prepare(self.site, self.root / "first", target="test", source="A")
        (self.site / "index.html").write_text("new accepted MTGO", encoding="utf-8")
        second = packages.prepare(self.site, self.root / "second", target="test", source="B")
        self.assertNotEqual(first["id"], second["id"])
        packages.verify(self.root / "second/product.tar.gz", second, target="test")

    def test_corruption_wrong_target_and_reusing_destination_are_rejected(self):
        manifest = packages.prepare(self.site, self.root / "candidate", target="test", source="A")
        package = self.root / "candidate/product.tar.gz"
        with self.assertRaises(ValueError):
            packages.verify(package, manifest, target="other")
        package.write_bytes(package.read_bytes() + b"corrupt")
        with self.assertRaises(ValueError):
            packages.extract(package, manifest, self.root / "preview", target="test")
        self.assertFalse((self.root / "preview").exists())
        with self.assertRaises(ValueError):
            packages.prepare(self.site, self.root / "candidate", target="test", source="A")

    def test_unsafe_archive_members_rejected_before_extraction(self):
        for name, kind in [("../escape", tarfile.REGTYPE), ("/absolute", tarfile.REGTYPE),
                           ("C:/escape", tarfile.REGTYPE), ("link", tarfile.SYMTYPE),
                           ("hardlink", tarfile.LNKTYPE), ("NUL.txt", tarfile.REGTYPE)]:
            with self.subTest(name=name):
                path = self.root / "unsafe.tar"
                with tarfile.open(path, "w") as stream:
                    info = tarfile.TarInfo(name)
                    info.type = kind
                    info.size = 1 if kind == tarfile.REGTYPE else 0
                    info.linkname = "../escape" if kind != tarfile.REGTYPE else ""
                    stream.addfile(info, io.BytesIO(b"x") if info.size else None)
                with self.assertRaises(ValueError):
                    packages.inspect(path)

    def test_manifest_cannot_claim_missing_product_is_complete(self):
        (self.site / "melee/index.html").unlink()
        with self.assertRaises(ValueError):
            packages.prepare(self.site, self.root / "candidate", target="test", source="A")
        self.assertFalse((self.root / "candidate/manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
