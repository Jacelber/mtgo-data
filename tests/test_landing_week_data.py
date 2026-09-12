from datetime import date
from pathlib import Path

import pytest

from mtgmeta.mtgo import landing


def test_week_snapshot_rejects_different_admitted_events_before_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(landing.stats, "load_all_events", lambda *a, **kw: [
        (date(2026, 8, 24), {"event_id": "123"}),
    ])
    document = {"week": {"id": "2026-W35", "start": "2026-08-24", "end": "2026-08-30"},
                "source_event_ids": ["456"]}
    with pytest.raises(landing.MTGOLandingError, match="admitted source events"):
        landing.generate_week_data(Path("."), "pauper", document, tmp_path)
    assert not list(tmp_path.iterdir())


def test_week_snapshot_rejects_classifier_change_before_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(landing.stats, "load_all_events", lambda *a, **kw: [
        (date(2026, 8, 24), {"event_id": "123"}),
    ])
    monkeypatch.setattr(landing, "load_rules_for_format", lambda *a, **kw: object())
    monkeypatch.setattr(landing, "classifier_digest", lambda _: "current")
    document = {"week": {"id": "2026-W35", "start": "2026-08-24", "end": "2026-08-30"},
                "source_event_ids": ["123"], "classifier": {"digest": "old"}}
    with pytest.raises(landing.MTGOLandingError, match="classifier"):
        landing.generate_week_data(Path("."), "pauper", document, tmp_path)
    assert not list(tmp_path.iterdir())
