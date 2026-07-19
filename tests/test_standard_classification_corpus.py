"""Self-contained deterministic baseline for the legacy Standard classifier."""

import hashlib
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
repository_root_text = str(REPOSITORY_ROOT)
if repository_root_text not in sys.path:
    sys.path.insert(0, repository_root_text)

from classify_standard import load_rules, match_archetype


ROOT = REPOSITORY_ROOT
FIXTURE = ROOT / "tests" / "fixtures" / "standard" / "frozen_legacy_corpus.json"
EXPECTED_DIGEST = "af1b6af542c7185ba507994e8f666c89272dc67e00318fc9399b0a1c3623fe0b"


def load_records():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["records"]


def legacy_rules():
    return load_rules()


def digest(records):
    canonical = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_frozen_corpus_is_complete_deterministic_and_reclassified():
    records = load_records()
    identities = [tuple(record["id"]) for record in records]
    assert len(records) == 3936
    assert len(set(identities)) == 3936
    assert digest(records) == EXPECTED_DIGEST
    rules = legacy_rules()
    for record in records:
        main = dict(record["main"])
        side = dict(record["side"])
        actual = match_archetype(main, side, rules) or "Unknown"
        assert actual == record["expected"], record["id"]
    assert sum(record["expected"] == "Unknown" for record in records) == 71
