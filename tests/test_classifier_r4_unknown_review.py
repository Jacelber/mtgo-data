from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import yaml

from tools.build_classifier_r4_unknown_review import (
    ALLOWED_DISPOSITIONS,
    R3_BASE_COMMIT,
    SIMILARITY_THRESHOLD,
    UnknownRecord,
    build_review,
    cluster_records,
    load_unknown_records,
    weighted_jaccard,
    write_review,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "docs" / "audits" / "classifier-r4"
R4_INPUT_ROOT = OUTPUT_ROOT / "baseline_unknown_inputs"


def _record(record_id: str, cards: dict[str, int]) -> UnknownRecord:
    return UnknownRecord(
        format_id="modern",
        source="mtgo",
        event_id=record_id,
        event_name=None,
        event_start=None,
        record_id=record_id,
        main=tuple(sorted(cards.items())),
        side=(),
    )


def test_weighted_jaccard_uses_main_deck_quantities() -> None:
    left = _record("left", {"Shared": 4, "Left": 2})
    right = _record("right", {"Shared": 3, "Right": 3})

    assert weighted_jaccard(left, left) == 1.0
    assert weighted_jaccard(left, right) == 3 / 9


def test_clustering_is_deterministic_and_transitive() -> None:
    first = _record("first", {"A": 4, "B": 4})
    bridge = _record("bridge", {"A": 4, "B": 2, "C": 2})
    last = _record("last", {"A": 4, "C": 4})
    isolated = _record("isolated", {"Z": 8})

    forward = cluster_records([first, bridge, last, isolated], threshold=0.5)
    reverse = cluster_records(
        [isolated, last, bridge, first], threshold=0.5
    )

    assert [[item.record_id for item in group] for group in forward] == [
        [item.record_id for item in group] for group in reverse
    ]
    assert sorted(len(group) for group in forward) == [1, 3]


def test_frozen_inputs_have_expected_deidentified_record_inventory() -> None:
    records = load_unknown_records(R4_INPUT_ROOT)

    assert len(records) == 305
    assert Counter((item.format_id, item.source) for item in records) == Counter(
        {
            ("modern", "mtgo"): 177,
            ("modern", "melee"): 11,
            ("standard", "mtgo"): 117,
        }
    )
    assert len({item.record_id for item in records}) == len(records)
    assert all(len(item.record_id) == 20 for item in records)


def test_review_queue_covers_every_record_without_assigning_archetypes() -> None:
    review = build_review(R4_INPUT_ROOT)

    assert review["base_commit"] == R3_BASE_COMMIT
    assert review["parameters"]["edge_threshold"] == SIMILARITY_THRESHOLD
    assert review["summary"] == {
        "records": 305,
        "families": 147,
        "formats": {
            "modern": {
                "records": 188,
                "families": 88,
                "recurring_families": 37,
                "multi_record_single_event_families": 0,
                "singleton_families": 51,
                "source_records": {"melee": 11, "mtgo": 177},
            },
            "standard": {
                "records": 117,
                "families": 59,
                "recurring_families": 16,
                "multi_record_single_event_families": 0,
                "singleton_families": 43,
                "source_records": {"mtgo": 117},
            },
        },
    }
    member_ids = [
        member["record_id"]
        for family in review["families"]
        for member in family["members"]
    ]
    assert len(member_ids) == len(set(member_ids)) == 305
    assert [item["review_rank"] for item in review["families"]] == list(
        range(1, 148)
    )
    assert all(item["review_status"] == "pending_owner_review" for item in review["families"])
    assert all(item["disposition"] is None for item in review["families"])
    assert all(
        item["allowed_dispositions"] == list(ALLOWED_DISPOSITIONS)
        for item in review["families"]
    )
    assert all(
        candidate["complete_matches"] == 0
        for family in review["families"]
        for candidate in family["nearest_production_rules"]
    )


def test_review_artifact_does_not_retain_source_identifiers() -> None:
    review_text = json.dumps(build_review(R4_INPUT_ROOT), ensure_ascii=False)
    for format_id in ("modern", "standard"):
        source = json.loads(
            (
                R4_INPUT_ROOT
                / "reports"
                / format_id
                / "mtgo"
                / "unknown_decks.json"
            ).read_text(encoding="utf-8")
        )
        assert all(item["deck_id"] not in review_text for item in source["records"])
    melee = json.loads(
        (
            R4_INPUT_ROOT
            / "data"
            / "modern"
            / "melee"
            / "classifications"
            / "434455.json"
        ).read_text(encoding="utf-8")
    )
    assert all(
        item["participant_id"] not in review_text
        for item in melee["records"]
        if item["classification_status"] == "unknown"
    )


def test_write_is_reproducible_and_preserves_owner_dispositions(tmp_path: Path) -> None:
    review = build_review(R4_INPUT_ROOT)
    first_hashes = write_review(review, tmp_path)
    first_bytes = {
        path.name: path.read_bytes() for path in sorted(tmp_path.iterdir())
    }
    disposition_path = tmp_path / "dispositions.yaml"
    dispositions = yaml.safe_load(disposition_path.read_text(encoding="utf-8"))
    dispositions["families"][0].update(
        {
            "review_status": "owner_accepted",
            "disposition": "intentional_unknown",
            "rationale": "synthetic owner-review preservation test",
            "owner_accepted": True,
        }
    )
    disposition_path.write_text(
        yaml.safe_dump(dispositions, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )

    second_hashes = write_review(review, tmp_path)

    assert first_hashes["unknown_family_queue.json"] == second_hashes["unknown_family_queue.json"]
    assert first_hashes["unknown_family_queue.md"] == second_hashes["unknown_family_queue.md"]
    assert first_bytes["unknown_family_queue.json"] == (
        tmp_path / "unknown_family_queue.json"
    ).read_bytes()
    assert first_bytes["unknown_family_queue.md"] == (
        tmp_path / "unknown_family_queue.md"
    ).read_bytes()
    preserved = yaml.safe_load(disposition_path.read_text(encoding="utf-8"))
    assert preserved["families"][0]["disposition"] == "intentional_unknown"


def test_committed_review_artifacts_are_reproducible(tmp_path: Path) -> None:
    disposition_path = tmp_path / "dispositions.yaml"
    disposition_path.write_bytes((OUTPUT_ROOT / "dispositions.yaml").read_bytes())
    write_review(build_review(R4_INPUT_ROOT), tmp_path)

    for name in (
        "unknown_family_queue.json",
        "unknown_family_queue.md",
        "dispositions.yaml",
    ):
        assert (tmp_path / name).read_bytes() == (OUTPUT_ROOT / name).read_bytes()
