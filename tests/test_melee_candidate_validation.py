from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

import validate_melee_candidate as candidate
from validate_melee_candidate import Change, validate_candidate


FORMAT_ID = "modern"
SELECTED_EVENT_ID = "441441"
CATALOG_PATH = "stats/modern/melee/index.json"


def _event(event_id: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "name": f"Synthetic {event_id}",
        "meta": f"events/{event_id}/meta.json",
    }


def _catalog(event_ids: list[str]) -> dict[str, object]:
    return {
        "schema_version": "1.2.0",
        "document_type": "event_catalog",
        "source": "melee",
        "product": "tabletop-major-events",
        "format": FORMAT_ID,
        "active_taxonomy": {
            "schema_version": "1.0.0",
            "taxonomy_schema_version": "1.1.0",
            "taxonomy_sha256": "a" * 64,
        },
        "default_event_id": event_ids[0],
        "events": [_event(event_id) for event_id in event_ids],
    }


def _write_catalog(root: Path, catalog: dict[str, object]) -> None:
    path = root / CATALOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog), encoding="utf-8")


def _baseline(
    root: Path, monkeypatch: pytest.MonkeyPatch, catalog: dict[str, object]
) -> dict[str, object]:
    _write_catalog(root, catalog)
    monkeypatch.setattr(candidate, "_git", lambda *args: "base-head\n")
    return candidate.snapshot_state(root, SELECTED_EVENT_ID, FORMAT_ID)


def _validate(
    root: Path, baseline: dict[str, object]
) -> list[str]:
    _, failures = validate_candidate(
        root,
        baseline,
        [Change(" M", CATALOG_PATH)],
    )
    return failures


def test_candidate_catalog_allows_only_selected_event_addition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = _catalog(["434455"])
    baseline = _baseline(tmp_path, monkeypatch, existing)
    candidate_catalog = deepcopy(existing)
    candidate_catalog["events"].append(_event(SELECTED_EVENT_ID))  # type: ignore[union-attr]
    _write_catalog(tmp_path, candidate_catalog)

    assert not _validate(tmp_path, baseline)


def test_candidate_catalog_allows_selected_new_event_as_proposed_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = _catalog(["434455"])
    baseline = _baseline(tmp_path, monkeypatch, existing)
    candidate_catalog = deepcopy(existing)
    events = candidate_catalog["events"]
    assert isinstance(events, list)
    events.insert(0, _event(SELECTED_EVENT_ID))
    candidate_catalog["default_event_id"] = SELECTED_EVENT_ID
    _write_catalog(tmp_path, candidate_catalog)

    assert not _validate(tmp_path, baseline)


@pytest.mark.parametrize("mutation", ["delete", "rewrite", "unrelated"])
def test_candidate_catalog_rejects_existing_cohort_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    existing = _catalog(["434455"])
    baseline = _baseline(tmp_path, monkeypatch, existing)
    candidate_catalog = deepcopy(existing)
    events = candidate_catalog["events"]
    assert isinstance(events, list)
    if mutation == "delete":
        events.clear()
    elif mutation == "rewrite":
        events[0]["name"] = "Silently rewritten"  # type: ignore[index]
        events.append(_event(SELECTED_EVENT_ID))
    else:
        events.extend([_event(SELECTED_EVENT_ID), _event("999999")])
    _write_catalog(tmp_path, candidate_catalog)

    assert _validate(tmp_path, baseline)


def test_candidate_catalog_rejects_default_change_to_another_existing_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = _catalog(["434455", "400000"])
    baseline = _baseline(tmp_path, monkeypatch, existing)
    candidate_catalog = deepcopy(existing)
    events = candidate_catalog["events"]
    assert isinstance(events, list)
    events.append(_event(SELECTED_EVENT_ID))
    candidate_catalog["default_event_id"] = "400000"
    _write_catalog(tmp_path, candidate_catalog)

    failures = _validate(tmp_path, baseline)

    assert (
        "event catalog changed the default to an event other than the candidate"
        in failures
    )


def test_candidate_catalog_rejects_existing_candidate_as_new_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = _catalog(["434455", SELECTED_EVENT_ID])
    baseline = _baseline(tmp_path, monkeypatch, existing)
    candidate_catalog = deepcopy(existing)
    candidate_catalog["default_event_id"] = SELECTED_EVENT_ID
    _write_catalog(tmp_path, candidate_catalog)

    failures = _validate(tmp_path, baseline)

    assert "existing candidate event cannot become the proposed default" in failures


def test_candidate_catalog_rejects_nonleading_candidate_as_proposed_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = _catalog(["434455"])
    baseline = _baseline(tmp_path, monkeypatch, existing)
    candidate_catalog = deepcopy(existing)
    events = candidate_catalog["events"]
    assert isinstance(events, list)
    events.append(_event(SELECTED_EVENT_ID))
    candidate_catalog["default_event_id"] = SELECTED_EVENT_ID
    _write_catalog(tmp_path, candidate_catalog)

    failures = _validate(tmp_path, baseline)

    assert "proposed default event must be the first catalog event" in failures
