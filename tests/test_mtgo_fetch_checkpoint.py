import json

import mtgo_fetch_checkpoint as checkpoint


REPOSITORY = "Jacelber/mtgo-data"
COMMIT = "a" * 40
EVENT_FORMATS = "standard modern"
MATCH_FORMATS = "standard"


def run(path, *arguments):
    return checkpoint.main(
        [
            *arguments,
            "--checkpoint",
            str(path),
            "--repository",
            REPOSITORY,
            "--commit",
            COMMIT,
            "--event-formats",
            EVENT_FORMATS,
            "--match-formats",
            MATCH_FORMATS,
        ]
    )


def test_checkpoint_tracks_only_the_exact_configured_operations(tmp_path):
    path = tmp_path / "checkpoint.json"

    assert run(path, "initialize") == 0
    value = json.loads(path.read_text(encoding="utf-8"))

    assert value == {
        "schema_version": "1.0.0",
        "repository": REPOSITORY,
        "commit": COMMIT,
        "event_formats": ["standard", "modern"],
        "match_formats": ["standard"],
        "operations": {
            "events/standard": "pending",
            "events/modern": "pending",
            "matches/standard": "pending",
        },
    }


def test_checkpoint_marks_completed_work_and_skips_only_that_work(tmp_path):
    path = tmp_path / "checkpoint.json"
    assert run(path, "initialize") == 0

    assert run(path, "is-complete", "--operation", "events/standard") == 1
    assert run(path, "complete", "--operation", "events/standard") == 0
    assert run(path, "is-complete", "--operation", "events/standard") == 0
    assert run(path, "is-complete", "--operation", "events/modern") == 1


def test_checkpoint_rejects_any_different_commit_or_operation_plan(tmp_path):
    path = tmp_path / "checkpoint.json"
    assert run(path, "initialize") == 0

    assert (
        checkpoint.main(
            [
                "validate",
                "--checkpoint",
                str(path),
                "--repository",
                REPOSITORY,
                "--commit",
                "b" * 40,
                "--event-formats",
                EVENT_FORMATS,
                "--match-formats",
                MATCH_FORMATS,
            ]
        )
        == 2
    )
    assert (
        checkpoint.main(
            [
                "validate",
                "--checkpoint",
                str(path),
                "--repository",
                REPOSITORY,
                "--commit",
                COMMIT,
                "--event-formats",
                "standard",
                "--match-formats",
                MATCH_FORMATS,
            ]
        )
        == 2
    )


def test_checkpoint_rejects_unknown_operations_and_invalid_states(tmp_path):
    path = tmp_path / "checkpoint.json"
    assert run(path, "initialize") == 0
    assert run(path, "complete", "--operation", "events/pauper") == 2

    value = json.loads(path.read_text(encoding="utf-8"))
    value["operations"]["events/standard"] = "failed"
    path.write_text(json.dumps(value), encoding="utf-8")
    assert run(path, "validate") == 2
