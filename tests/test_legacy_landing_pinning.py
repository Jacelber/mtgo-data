"""A data advance must keep legacy Landing consumers on their accepted week."""
from hashlib import sha256
import json

import pytest

from mtgmeta.mtgo.publication import PublicationError, _restate_retained_landing


def _source(tmp_path):
    root, stage = tmp_path / "source", tmp_path / "stage"
    base = root / "stats/modern/mtgo"
    page = {"week": {"id": "2025-W02", "start": "2025-01-06", "end": "2025-01-12"},
            "classifier": {"digest": "accepted"}, "weekly_summary": {"items": ["keep this copy"]},
            "features": {"items": []}}
    (base / "landing").mkdir(parents=True)
    (base / "landing/current.json").write_text(json.dumps(page), encoding="utf-8")
    artifacts, originals = {}, {}
    for name, start, weeks in [("range_1w.json", "2025-01-06", 1),
                                ("decks_1w.json", "2025-01-06", 1),
                                ("decks_4w.json", "2024-12-16", 4),
                                ("completeness/1w.json", "2025-01-06", 1)]:
        data = {"format": "modern", "source": "mtgo", "classifier_digest": "accepted",
                "period": {"start": start, "end": "2025-01-12", "weeks": weeks}}
        payload = (json.dumps(data, indent=1) + "\n").encode()
        path = base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        artifacts[f"stats/modern/mtgo/{name}"] = sha256(payload).hexdigest()
        originals[name] = payload
    (base / "meta.json").write_text(json.dumps({"publication": {"artifacts": artifacts}}), encoding="utf-8")
    return root, stage, page, originals


def test_legacy_page_pins_exact_published_bytes_and_preserves_copy(tmp_path):
    root, stage, page, originals = _source(tmp_path)
    _restate_retained_landing(root, stage, "modern", "2025-W03")
    result = json.loads((stage / "stats/modern/mtgo/landing/current.json").read_text(encoding="utf-8"))
    files = result.pop("data_files")
    assert result == page
    for key, source in {"range": "range_1w.json", "environment_decks": "decks_1w.json",
                        "feature_decks": "decks_4w.json", "completeness": "completeness/1w.json"}.items():
        assert (stage / "stats/modern/mtgo/landing" / files[key]).read_bytes() == originals[source]


@pytest.mark.parametrize("bad_subject", ["changed_bytes", "later_week", "different_classifier"])
def test_legacy_page_rejects_unbound_or_wrong_subject_before_pinning(tmp_path, bad_subject):
    root, stage, _page, _originals = _source(tmp_path)
    path = root / "stats/modern/mtgo/decks_1w.json"
    data = json.loads(path.read_bytes())
    if bad_subject == "later_week":
        data["period"].update(start="2025-01-13", end="2025-01-19")
    elif bad_subject == "different_classifier":
        data["classifier_digest"] = "new"
    else:
        data["unexpected"] = True
    path.write_text(json.dumps(data), encoding="utf-8")
    if bad_subject != "changed_bytes":
        meta = root / "stats/modern/mtgo/meta.json"
        value = json.loads(meta.read_bytes())
        value["publication"]["artifacts"]["stats/modern/mtgo/decks_1w.json"] = sha256(path.read_bytes()).hexdigest()
        meta.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(PublicationError, match="published page's subject"):
        _restate_retained_landing(root, stage, "modern", "2025-W03")
    assert not list(stage.rglob("weeks/*/*.json"))
