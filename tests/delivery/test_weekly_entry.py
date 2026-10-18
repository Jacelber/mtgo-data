import json
from pathlib import Path

import pytest

from tools.delivery import weekly, packages


class Remote:
    def __init__(self):
        self.state = {"current": None, "pending": None, "recovery": None}
        self.preparations = self.sends = self.archives = 0
        self.timeout = False

    def observe(self, record):
        return self.state

    def query_original(self, record):
        return {"state": "unknown", "operation": record["operation"], "runs": []}

    def prepare(self, record):
        self.preparations += 1
        return {"state": "ready", "base": self.state["current"]["operation"] if self.state["current"] else None}

    def archive(self, record, candidate):
        self.archives += 1
        manifest = weekly.read(candidate / "manifest.json")
        packages.verify(candidate / "product.tar.gz", manifest, target=record["identity"]["target"])
        return {"id": manifest["id"]}

    def remember(self, record, package):
        pass

    def send(self, record, mode):
        self.sends += 1
        if self.timeout:
            raise OSError("response lost after send")
        self.state["current"] = {"operation": record["operation"], "package": record["progress"]["package"], "health": "passed"}
        return {"state": "passed"}


def task(tmp_path):
    site = tmp_path / "site"
    for name in packages.PROBES:
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
    reference = tmp_path / "accepted.json"
    reference.write_text('{"kind":"existing acceptance"}')
    record = tmp_path / "data.delivery.json"
    weekly.create_record(record, kind="reviewed_data", root=tmp_path, site=site,
        scope={"week": "2025-W02", "mtgo_formats": ["standard"]}, references=[reference], source="fixed",
        target="Jacelber/mtgo-data-governance-verification")
    return record


@pytest.mark.parametrize("adapter", [None, weekly.Remote()])
def test_missing_record_stops_before_remote_access(tmp_path, monkeypatch, adapter):
    def unexpected(*args, **kwargs):
        pytest.fail("Missing handoff must not access remote state")
    monkeypatch.setattr(weekly.Remote, "observe", unexpected)
    with pytest.raises(FileNotFoundError):
        weekly.continue_delivery(tmp_path / "absent.json", remote=adapter)
    assert not list(tmp_path.iterdir())


def test_isolated_delivery_without_verifier_cannot_archive_or_publish(tmp_path):
    record = task(tmp_path)
    remote = Remote()
    assert weekly.continue_delivery(record, remote=remote)["state"] == "repair_required"
    assert remote.archives == remote.sends == 0


def test_complete_local_data_candidate_never_generates_and_is_idempotent(tmp_path):
    record = task(tmp_path)
    remote = Remote()
    def no_generation(*args):
        pytest.fail("A complete local candidate must not run resource or content producers")
    before = record.read_bytes()
    assert weekly.inspect(record, remote=remote)["next"] == "package"
    assert record.read_bytes() == before and remote.preparations == 0
    checked = []
    first = weekly.continue_delivery(record, remote=remote, verify=lambda *a: checked.append('checked'), resources=no_generation)
    second = weekly.continue_delivery(record, remote=remote, verify=lambda *a: None, resources=no_generation)
    assert first == second
    assert first["kind"] == "reviewed_data" and first["weekly_completion"] == "not_implied"
    assert remote.sends == remote.archives == remote.preparations == 1
    assert checked == ['checked']
    assert [item['state'] for item in weekly.read(record)['history']
            if item['action'] == 'material_verification'] == ['executed', 'reused']


def test_lost_response_is_not_permission_to_send_again(tmp_path):
    record = task(tmp_path)
    remote = Remote()
    remote.timeout = True
    assert weekly.continue_delivery(record, remote=remote, verify=lambda *a: None)["state"] == "repair_required"
    original = weekly.read(record)["operation"]
    assert weekly.continue_delivery(record, remote=remote)["state"] == "unknown"
    assert remote.sends == 1 and weekly.read(record)["operation"] == original


def test_archive_failure_keeps_original_package_and_resumes(tmp_path):
    record = task(tmp_path)
    remote = Remote()
    def deny(*args):
        raise OSError("archive route unavailable")
    remote.archive, original = deny, remote.archive
    assert weekly.continue_delivery(record, remote=remote, verify=lambda *a: None)["state"] == "repair_required"
    candidate = Path(weekly.read(record)["progress"]["candidate"])
    original_bytes = (candidate / "product.tar.gz").read_bytes()
    remote.archive = original
    assert weekly.continue_delivery(record, remote=remote, verify=lambda *a: None)["state"] == "delivered"
    assert (candidate / "product.tar.gz").read_bytes() == original_bytes


def test_newer_product_requires_a_new_combination_not_rewriting_base(tmp_path):
    record = task(tmp_path)
    saved = weekly.read(record)
    saved["progress"]["base"] = "older"
    weekly.save(record, saved)
    remote = Remote()
    remote.state["current"] = {"operation": "newer", "package": "other", "health": "passed"}
    before = record.read_bytes()
    assert weekly.continue_delivery(record, remote=remote)["next"] == "composition_changed"
    assert record.read_bytes() == before and remote.sends == 0


def test_changed_acceptance_is_not_reused(tmp_path):
    record = task(tmp_path)
    (tmp_path / "accepted.json").write_text("changed")
    assert weekly.continue_delivery(record, remote=Remote())["next"] == "material_changed"


def test_live_adapter_calls_existing_interfaces_without_real_network(tmp_path, monkeypatch):
    from tools import pages_writer
    from tools.delivery import verification
    record = task(tmp_path)
    fake = Remote()
    calls = []
    class Archive:
        def private(self):
            calls.append("private")
        def archive(self, candidate, *, target):
            assert target == "Jacelber/mtgo-data-governance-verification"
            return fake.archive(weekly.read(record), candidate)
    monkeypatch.setattr(pages_writer, "context", lambda target: (Archive(), None))
    monkeypatch.setattr(weekly.commands, "status", lambda *a: {"control": fake.state})
    monkeypatch.setattr(weekly.commands, "preflight", lambda *a: fake.prepare(weekly.read(record)))
    monkeypatch.setattr(weekly.commands, "remember_candidate", lambda *a: calls.append("remember"))
    def dispatch(target, operation, package, base, mode, **kwargs):
        assert kwargs == {"preparation": operation, "automatic": True}
        return fake.send(weekly.read(record), mode)
    monkeypatch.setattr(weekly.commands, "dispatch", dispatch)
    monkeypatch.setattr(verification, "verify_material", lambda *a: calls.append("verify"))
    assert weekly.continue_delivery(record)["state"] == "delivered"
    assert fake.sends == fake.archives == fake.preparations == 1
    assert calls.index("verify") < calls.index("private") < calls.index("remember")


def test_registration_failure_reuses_already_archived_package(tmp_path):
    record, remote = task(tmp_path), Remote()
    def fail(*args):
        raise OSError("registration unavailable")
    remote.remember = fail
    checked = []
    assert weekly.continue_delivery(record, remote=remote, verify=lambda *a: checked.append('checked'))["state"] == "repair_required"
    remote.remember = lambda *a: None
    assert weekly.continue_delivery(record, remote=remote, verify=lambda *a: checked.append('checked'))["state"] == "delivered"
    assert remote.archives == remote.sends == 1
    assert checked == ['checked']


def test_changed_confirmation_after_archiving_still_blocks_send(tmp_path):
    record, remote = task(tmp_path), Remote()
    def pause(record, mode):
        return {"state": "publication_paused"}
    remote.send = pause
    assert weekly.continue_delivery(record, remote=remote, verify=lambda *a: None)["state"] == "publication_paused"
    (tmp_path / "accepted.json").write_text("new unaccepted scope")
    assert weekly.continue_delivery(record, remote=remote)["next"] == "material_changed"


def test_content_delivery_records_existing_acceptance_against_extracted_package(tmp_path, monkeypatch):
    from tools import review_submission
    from mtgmeta.mtgo import review_submission as submissions
    record, remote = task(tmp_path), Remote()
    packet = submissions.make_packet("preview", "standard", "2025-W02", {"final_page": {"copy": "accepted"}}, bindings={})
    receipt = submissions.record_decision(packet, None, ["final_page"], evidence="synthetic-owner",
        accepted_on="2025-01-07", entrypoint="http://localhost/test")
    accepted = tmp_path / "accepted.json"
    accepted.write_text(json.dumps({"submission": packet, "decisions": receipt}))
    value = weekly.read(record)
    value["identity"]["kind"] = "landing_content"
    value["identity"]["references"][0]["sha256"] = packages.sha256(accepted)
    weekly.save(record, value)
    def preview(extracted, fmt):
        assert (extracted / "index.html").read_text() == "{}"
        assert fmt == "standard"
        return packet
    monkeypatch.setattr(review_submission.review, "preview_packet", preview)
    assert weekly.continue_delivery(record, remote=remote, verify=lambda *a: None)["state"] == "delivered"
    result = weekly.read(record)
    completion = result["progress"]["content_completion"]["standard"]
    assert completion["decisions"] == receipt
    assert completion["publication"]["package"] == result["progress"]["package"]
    assert weekly.continue_delivery(record, remote=remote)["weekly_completion"] == "not_implied"
    assert remote.sends == 1
