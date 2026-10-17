import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from mtgmeta.resource_progress import ResourceProgress, digest
from tools.delivery import resource_recovery as recovery

ORIGIN = {"repository": "Jacelber/mtgo-data-governance-verification", "operation": "isolated-resource-test",
          "source": "a" * 40, "run": 100, "attempt": 1, "workflow": ".github/workflows/prepare-pages.yml"}
JPEG = b"\xff\xd8\xff\xe0synthetic-image\xff\xd9"


@pytest.mark.parametrize("kind", ["localization", "mtgo-landing-card-image-cache"])
def test_failed_resource_inputs_cross_encrypted_handoff_and_new_process(tmp_path, kind):
    progress = ResourceProgress(tmp_path / "failed-run", {"kind": kind})
    for n in range(1, 7):
        key = ({"query": [f"Card {n}"], "page": 1} if kind == "localization"
               else {"image": f"https://cards.scryfall.io/normal/{n}.jpg"})
        payload = (json.dumps({"page": 1, "total_pages": 1, "items": [{"name": f"Card {n}"}]}).encode()
                   if kind == "localization" else JPEG)
        progress.bytes(key, lambda: payload, lambda data: recovery.validate_entry(progress.state["identity"], key, data))
    # A failed seventh transfer is neither registered nor included in handoff.
    (progress.path / "seventh.part").write_bytes(b"unfinished")
    openssl = os.environ.get("OPENSSL_BINARY", "openssl")
    key, certificate = tmp_path / "key.pem", tmp_path / "public.pem"
    subprocess.run([openssl, "req", "-x509", "-newkey", "rsa:3072", "-nodes",
        "-keyout", str(key), "-out", str(certificate), "-days", "1", "-subj", "/CN=Resource recovery test"],
        check=True, capture_output=True)
    encrypted = tmp_path / "recovery.cms"
    manifest = recovery.seal(progress.path, encrypted, certificate, ORIGIN, openssl=openssl)
    assert len(manifest["progress"]["entries"]) == 6
    assert b"Card 1" not in encrypted.read_bytes() and b"synthetic-image" not in encrypted.read_bytes()
    bundle = tmp_path / "resources.zip"
    recovery.decrypt(encrypted, bundle, key, origin=ORIGIN, openssl=openssl)
    origin_path = tmp_path / "origin.json"
    origin_path.write_text(json.dumps(ORIGIN))
    restored = tmp_path / "new-run"
    result = subprocess.run([sys.executable, "-m", "tools.delivery.resource_recovery", "restore",
        "--input", str(bundle), "--output", str(restored), "--origin", str(origin_path)],
        check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["entries"] == 6
    retained = ResourceProgress(restored, {"kind": kind})
    for entry in progress.state["entries"].values():
        retained.bytes(entry["key"], lambda: pytest.fail("Already preserved resource fetched again"),
                       lambda data: recovery.validate_entry(retained.state["identity"], entry["key"], data))
    assert retained.reused == 6
    assert not list(restored.glob("*.part"))
    assert retained.state["complete"] is False
    with pytest.raises(ValueError, match="another operation"):
        recovery.inspect_bundle(bundle, origin={**ORIGIN, "operation": "other-task"})
    damaged = tmp_path / "damaged.cms"
    changed = bytearray(encrypted.read_bytes())
    changed[len(changed) // 2] ^= 1
    damaged.write_bytes(changed)
    with pytest.raises(ValueError, match="authentication"):
        recovery.decrypt(damaged, tmp_path / "invalid.zip", key, origin=ORIGIN, openssl=openssl)
    assert not (tmp_path / "invalid.zip").exists()


def test_corrupted_registered_entry_is_excluded_and_reported(tmp_path):
    state = ResourceProgress(tmp_path / "work", {"kind": "mtgo-landing-card-image-cache"})
    for n in (1, 2):
        key = {"image": f"https://cards.scryfall.io/normal/{n}.jpg"}
        state.bytes(key, lambda: JPEG, lambda _: None)
    damaged_id = digest({"image": "https://cards.scryfall.io/normal/2.jpg"})
    (state.path / (damaged_id + ".bin")).write_bytes(b"changed")
    manifest = recovery.snapshot(state.path, tmp_path / "recovery.zip", ORIGIN)
    assert manifest["excluded_entries"] == [damaged_id]
    assert len(manifest["progress"]["entries"]) == 1


def test_failure_is_allowed_but_does_not_waive_source_provenance():
    run = {"id": 100, "run_attempt": 1, "head_sha": ORIGIN["source"], "head_branch": "main",
           "event": "workflow_dispatch", "path": ORIGIN["workflow"], "conclusion": "failure",
           "repository": {"full_name": ORIGIN["repository"]}, "head_repository": {"full_name": ORIGIN["repository"]}}
    recovery.validate_source_run(ORIGIN, run)
    for changes in ({"head_branch": "feature"}, {"path": ".github/workflows/other.yml"},
                    {"run_attempt": 2}, {"head_repository": {"full_name": "other/repository"}}):
        with pytest.raises(ValueError, match="trusted producer"):
            recovery.validate_source_run(ORIGIN, {**run, **changes})
