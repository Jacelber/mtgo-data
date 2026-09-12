"""A private candidate crosses a public handoff without disclosure or rebuilding."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.delivery import packages


class HandoffTests(unittest.TestCase):
    def test_private_handoff_roundtrip_and_tampering(self):
        openssl = os.environ.get("OPENSSL_BINARY", "openssl")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            key, certificate = root / "key.pem", root / "public.pem"
            result = subprocess.run([openssl, "req", "-x509", "-newkey", "rsa:3072", "-nodes",
                "-keyout", str(key), "-out", str(certificate), "-days", "1", "-subj", "/CN=Synthetic handoff"], capture_output=True)
            self.assertEqual(result.returncode, 0, "OpenSSL test-key preparation failed")
            site = root / "site"
            for name in packages.PROBES:
                path = site / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("synthetic private candidate content")
            candidate = root / "candidate"
            manifest = packages.prepare(site, candidate, target="synthetic", source="prepared")
            sealed = root / "handoff.cms"
            packages.seal_candidate(candidate, sealed, certificate, target="synthetic", openssl=openssl)
            self.assertNotIn(b"synthetic private candidate content", sealed.read_bytes())
            restored = root / "restored"
            self.assertEqual(packages.open_candidate(sealed, restored, key, target="synthetic", openssl=openssl), manifest)
            self.assertEqual((candidate / "product.tar.gz").read_bytes(), (restored / "product.tar.gz").read_bytes())
            changed = bytearray(sealed.read_bytes())
            changed[len(changed) // 2] ^= 1
            damaged = root / "damaged.cms"
            damaged.write_bytes(changed)
            with self.assertRaises(ValueError):
                packages.open_candidate(damaged, root / "invalid", key, target="synthetic", openssl=openssl)
            self.assertFalse((root / "invalid").exists())
