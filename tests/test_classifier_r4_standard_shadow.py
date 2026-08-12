from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import yaml

from mtgmeta.classifier import classify_counts
from mtgmeta.classifier_features import load_semantic_feature_manifest
from mtgmeta.classifier_shadow_audit import (
    _record_counts,
    identity_signature,
    load_frozen_records,
    reordered_rule_set,
    rule_inventory,
)
from mtgmeta.config import load_rule_set, parse_rule_text
from mtgmeta.deck import deck_to_counts
from mtgmeta.mtgo import stats
from tools.build_classifier_r4_standard_shadow_rules import (
    AZORIUS_AURAS_FAMILY,
    AZORIUS_ESPER_CONTROL_FAMILY,
    AZORIUS_PROWESS_FAMILY,
    BANT_AIRBENDING_FAMILY,
    ESPER_PIXIE_FAMILY,
    FIVE_COLOR_HUMANS_FAMILY,
    GOLGARI_REANIMATOR_FAMILY,
    IZZET_BURN_FAMILY,
    MONO_GREEN_SQUIRREL_FAMILY,
    MONO_GREEN_MIGHTIEST_FAMILY,
    MONO_WHITE_TRIUMPH_FAMILY,
    ORZHOV_LIFEGAIN_FAMILY,
    PRODUCTION_STANDARD_SHA256,
    SIMIC_RHYTHM_SQUIRREL_FAMILY,
    SULTAI_CONTROL_FAMILY,
    SULTAI_MIDRANGE_FAMILY,
    TEMUR_HULK_RAMP_FAMILY,
    SINGLETON_DECISIONS,
    build_standard_shadow_rules,
    render_standard_shadow_rules,
)
from tools.build_classifier_r4_unknown_review import load_unknown_records


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_PATH = ROOT / "my_archetypes" / "standard.yaml"
SHADOW_PATH = (
    ROOT / "docs" / "audits" / "classifier-r4" / "shadow_rules" / "standard.yaml"
)
FROZEN_PATH = ROOT / "tests" / "fixtures" / "standard" / "frozen_legacy_corpus.json"
DISPOSITIONS_PATH = (
    ROOT / "docs" / "audits" / "classifier-r4" / "standard_dispositions.yaml"
)
QUEUE_PATH = ROOT / "docs" / "audits" / "classifier-r4" / "unknown_family_queue.json"

EXPECTED_FAMILIES = {
    ORZHOV_LIFEGAIN_FAMILY: ("orzhov-lifegain", "orzhov-lifegain-primary", 19),
    FIVE_COLOR_HUMANS_FAMILY: (
        "five-color-humans",
        "five-color-humans-primary",
        13,
    ),
    MONO_GREEN_MIGHTIEST_FAMILY: (
        "mono-green-mightiest",
        "mono-green-mightiest-primary",
        7,
    ),
    SULTAI_CONTROL_FAMILY: ("sultai-control", "sultai-control-consult", 6),
    AZORIUS_PROWESS_FAMILY: ("azorius-prowess", "azorius-prowess-primary", 3),
    GOLGARI_REANIMATOR_FAMILY: (
        "golgari-reanimator",
        "golgari-reanimator-faithful",
        3,
    ),
    ESPER_PIXIE_FAMILY: ("esper-pixie", "esper-pixie-primary", 2),
    SULTAI_MIDRANGE_FAMILY: (
        "sultai-midrange",
        "sultai-midrange-primary",
        2,
    ),
    MONO_WHITE_TRIUMPH_FAMILY: (
        "mono-white-triumph",
        "mono-white-triumph-primary",
        2,
    ),
    IZZET_BURN_FAMILY: ("izzet-burn", "izzet-burn-primary", 2),
    SIMIC_RHYTHM_SQUIRREL_FAMILY: (
        "simic-rhythm",
        "simic-rhythm-squirrel",
        2,
    ),
    MONO_GREEN_SQUIRREL_FAMILY: (
        "mono-green-squirrel-combo",
        "mono-green-squirrel-combo-primary",
        2,
    ),
    TEMUR_HULK_RAMP_FAMILY: (
        "temur-hulk-ramp",
        "temur-hulk-ramp-primary",
        2,
    ),
    AZORIUS_AURAS_FAMILY: ("azorius-auras", "azorius-auras-primary", 2),
    BANT_AIRBENDING_FAMILY: (
        "bant-airbending",
        "bant-airbending-primary",
        2,
    ),
}

CONTROL_PARTITION = {
    "azorius-control-consult": {
        "192350fdc7842115d151",
        "4013686b0345d707a524",
        "4c7a6219bd602453c50a",
        "a81d2e98a005c843039a",
    },
    "esper-control-consult": {"135cf04f37022ed110b4"},
}

SINGLETON_RULES = {
    "standard-unknown-0857720282a4": "selesnya-ramp-primary",
    "standard-unknown-0cbae9644068": "boros-burn-boltwave",
    "standard-unknown-115a1eb783c9": "azorius-cage-primary",
    "standard-unknown-115bb2d40b87": "white-weenie-primary",
    "standard-unknown-14e962276abd": "boros-token-primary",
    "standard-unknown-18e903160e16": "golgari-sacrifice-primary",
    "standard-unknown-242b3816824a": "mono-blue-namor-primary",
    "standard-unknown-42ba8896c962": "boros-token-primary",
    "standard-unknown-465ced1c0787": "dimir-oculus-primary",
    "standard-unknown-546deaf24038": "sultai-oculus-primary",
    "standard-unknown-5488cd49501c": "temur-otters-vitality-floodcaller",
    "standard-unknown-54989a313da5": "azorius-token-control-primary",
    "standard-unknown-568d48ce3fef": None,
    "standard-unknown-5cb23228136a": "mono-black-aggro-corpses-banner",
    "standard-unknown-6b0bfc1c3537": "izzet-lessons-primary",
    "standard-unknown-71c89735d78a": "mono-black-demons-primary",
    "standard-unknown-79d9648ddef1": "gruul-monsters-primary",
    "standard-unknown-7aed5a7501d9": "izzet-iron-man-primary",
    "standard-unknown-7e295c544d07": "rakdos-ponza-primary",
    "standard-unknown-7f6bed1d356c": "golgari-midrange-badgermole-sentinel",
    "standard-unknown-830e01106c19": "orzhov-control-day-of-judgment",
    "standard-unknown-8524a65d8f73": "mono-black-demons-primary",
    "standard-unknown-867164f5dbc4": "sultai-midrange-hauntwoods-value",
    "standard-unknown-8784b67a44bd": "dimir-flash-primary",
    "standard-unknown-8d24e522f051": "orzhov-control-deadly-cover-up",
    "standard-unknown-9505d82a2ea3": "gruul-ramp-tablet",
    "standard-unknown-96321e1721cb": "dimir-oculus-primary",
    "standard-unknown-9c3d83efcf2a": "azorius-momo-primary",
    "standard-unknown-9efdb7d63014": "orzhov-demon-primary",
    "standard-unknown-ae068aea323a": "boros-token-primary",
    "standard-unknown-b05defd59bf9": "gruul-dinosaur-primary",
    "standard-unknown-b2752e143f9b": "temur-elementals-primary",
    "standard-unknown-b322d579e883": "golgari-crime-primary",
    "standard-unknown-b4dd6c01de05": "mono-white-auras-primary",
    "standard-unknown-be4503b245f3": "jeskai-equipment-primary",
    "standard-unknown-cb47b3fd754a": "white-sultai-control-hauntwoods",
    "standard-unknown-ce41fdb9a299": "orzhov-momo-primary",
    "standard-unknown-d35bb31f0714": "rakdos-discard-primary",
    "standard-unknown-dae51c5571ba": "golgari-crime-primary",
    "standard-unknown-ddce99be6026": "gruul-ramp-weather-maker",
    "standard-unknown-f283503ba493": "break-out-aggro-primary",
    "standard-unknown-f68bfee8c56f": "jeskai-control-consult-helix",
    "standard-unknown-fa7d763a076f": "mono-red-burn-primary",
}


def _load_shadow_rules():
    rules = parse_rule_text(SHADOW_PATH.read_text(encoding="utf-8"))
    manifest_path = ROOT / "configs" / "classifier_semantic_features.yaml"
    assert (
        rules.semantic_feature_sha256 == sha256(manifest_path.read_bytes()).hexdigest()
    )
    return replace(
        rules,
        semantic_features=load_semantic_feature_manifest(manifest_path),
    )


def _family_record_ids() -> dict[str, set[str]]:
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    return {
        family["family_id"]: {member["record_id"] for member in family["members"]}
        for family in queue["families"]
        if family["family_id"] in EXPECTED_FAMILIES
    }


def test_standard_accepted_decisions_and_shadow_are_deterministic() -> None:
    dispositions = yaml.safe_load(DISPOSITIONS_PATH.read_text(encoding="utf-8"))
    assert dispositions["review"] == {
        "candidate_families": 59,
        "owner_accepted_families": 59,
        "pending_families": 0,
    }
    observed = {
        item["family_id"]: (item["disposition"], item["target_identity"])
        for item in dispositions["families"]
    }
    assert observed == {
        ORZHOV_LIFEGAIN_FAMILY: ("new_identity", "orzhov-lifegain"),
        FIVE_COLOR_HUMANS_FAMILY: ("new_identity", "five-color-humans"),
        MONO_GREEN_MIGHTIEST_FAMILY: (
            "new_identity",
            "mono-green-mightiest",
        ),
        SULTAI_CONTROL_FAMILY: ("map_existing", "sultai-control"),
        AZORIUS_ESPER_CONTROL_FAMILY: (
            "new_identity",
            "azorius-control|esper-control",
        ),
        GOLGARI_REANIMATOR_FAMILY: (
            "map_existing",
            "golgari-reanimator",
        ),
        AZORIUS_PROWESS_FAMILY: ("new_identity", "azorius-prowess"),
        ESPER_PIXIE_FAMILY: ("map_existing", "esper-pixie"),
        SULTAI_MIDRANGE_FAMILY: ("new_identity", "sultai-midrange"),
        MONO_WHITE_TRIUMPH_FAMILY: ("new_identity", "mono-white-triumph"),
        IZZET_BURN_FAMILY: ("new_identity", "izzet-burn"),
        SIMIC_RHYTHM_SQUIRREL_FAMILY: ("map_existing", "simic-rhythm"),
        MONO_GREEN_SQUIRREL_FAMILY: (
            "new_identity",
            "mono-green-squirrel-combo",
        ),
        TEMUR_HULK_RAMP_FAMILY: ("new_identity", "temur-hulk-ramp"),
        AZORIUS_AURAS_FAMILY: ("new_identity", "azorius-auras"),
        BANT_AIRBENDING_FAMILY: ("map_existing", "bant-airbending"),
        **SINGLETON_DECISIONS,
    }
    assert all(item["owner_accepted"] is True for item in dispositions["families"])
    control = next(
        item
        for item in dispositions["families"]
        if item["family_id"] == AZORIUS_ESPER_CONTROL_FAMILY
    )
    assert {
        partition["target_identity"]: set(partition["record_ids"])
        for partition in control["partition"]
    } == {
        "azorius-control": CONTROL_PARTITION["azorius-control-consult"],
        "esper-control": CONTROL_PARTITION["esper-control-consult"],
    }

    assert (
        sha256(PRODUCTION_PATH.read_bytes()).hexdigest() == PRODUCTION_STANDARD_SHA256
    )
    assert SHADOW_PATH.read_text(encoding="utf-8") == render_standard_shadow_rules(ROOT)
    assert yaml.safe_load(SHADOW_PATH.read_text(encoding="utf-8")) == (
        build_standard_shadow_rules(ROOT)
    )
    inventory = rule_inventory(_load_shadow_rules())
    assert inventory["parent_count"] == 102
    assert inventory["subtype_count"] == 11
    assert inventory["rule_count"] == 126
    assert inventory["rule_ids_unique"] is True
    assert inventory["numeric_priorities_globally_unique"] is True
    assert inventory["priority_collisions"] == []


def test_standard_batch_1_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    orzhov = {
        "Amalia Benavides Aguirre": 3,
        "Case of the Uneaten Feast": 3,
        "Hinterland Sanctifier": 3,
        "Lunar Convocation": 2,
        "Godless Shrine": 2,
    }
    assert classify_counts(shadow, orzhov, {}).selected_rule_id == (
        "orzhov-lifegain-primary"
    )
    below_orzhov = dict(orzhov)
    below_orzhov["Amalia Benavides Aguirre"] = 2
    assert classify_counts(shadow, below_orzhov, {}).selected_rule_id != (
        "orzhov-lifegain-primary"
    )

    humans = {
        "Cavern of Souls": 4,
        "Secluded Courtyard": 4,
        "Celestial Reunion": 3,
        "Cecil, Dark Knight": 3,
        "Spectacular Spider-Man": 2,
        "Arachne, Psionic Weaver": 2,
    }
    assert classify_counts(shadow, humans, {}).selected_rule_id == (
        "five-color-humans-primary"
    )
    allies = {
        **humans,
        "Earth King's Lieutenant": 4,
        "Jasmine Dragon Tea Shop": 3,
    }
    assert classify_counts(shadow, allies, {}).selected_rule_id == (
        "4-color-allies-primary"
    )

    mightiest = {
        "Earth's Mightiest Heroes": 3,
        "Craterhoof Behemoth": 3,
        "Ouroboroid": 3,
        "Spider Manifestation": 3,
        "Forest": 12,
        "Nature's Rhythm": 1,
    }
    assert classify_counts(shadow, mightiest, {}).selected_rule_id == (
        "mono-green-mightiest-primary"
    )
    rhythm = dict(mightiest)
    rhythm["Nature's Rhythm"] = 2
    assert classify_counts(shadow, rhythm, {}).selected_rule_id != (
        "mono-green-mightiest-primary"
    )

    sultai = {
        "Consult the Star Charts": 3,
        "Deadly Cover-Up": 3,
        "Professor Dellian Fel": 2,
        "Breeding Pool": 2,
        "Watery Grave": 2,
        "Overgrown Tomb": 1,
        "Unholy Annex // Ritual Chamber": 2,
        "Demolition Field": 2,
        "Three Steps Ahead": 2,
    }
    sultai_result = classify_counts(shadow, sultai, {})
    assert sultai_result.selected_rule_id == "sultai-control-consult"
    assert {item.rule_id for item in sultai_result.matched_rules} == {
        "dimir-control-primary",
        "sultai-control-consult",
    }
    demon = dict(sultai)
    demon["Unholy Annex // Ritual Chamber"] = 3
    demon.pop("Demolition Field")
    demon.pop("Three Steps Ahead")
    assert classify_counts(shadow, demon, {}).selected_rule_id == (
        "sultai-demon-primary"
    )


def test_standard_batch_2_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    azorius = {
        "Consult the Star Charts": 2,
        "Day of Judgment": 3,
        "Stock Up": 3,
        "No More Lies": 2,
        "Hallowed Fountain": 2,
    }
    assert classify_counts(shadow, azorius, {}).selected_rule_id == (
        "azorius-control-consult"
    )
    esper = {**azorius, "Swamp": 1}
    assert (
        classify_counts(
            shadow,
            esper,
            {"Ancient Vendetta": 1},
        ).selected_rule_id
        == "esper-control-consult"
    )
    assert classify_counts(
        shadow,
        azorius,
        {"Ancient Vendetta": 1},
    ).selected_rule_id not in {
        "azorius-control-consult",
        "esper-control-consult",
    }
    jeskai = {**azorius, "Jeskai Revelation": 1}
    assert classify_counts(shadow, jeskai, {}).selected_rule_id not in {
        "azorius-control-consult",
        "esper-control-consult",
    }

    reanimator = {
        "Valgavoth's Faithful": 3,
        "Broodheart Engine": 3,
        "Broodspinner": 3,
    }
    assert classify_counts(shadow, reanimator, {}).selected_rule_id == (
        "golgari-reanimator-faithful"
    )
    below_reanimator = dict(reanimator)
    below_reanimator["Valgavoth's Faithful"] = 2
    assert classify_counts(shadow, below_reanimator, {}).selected_rule_id != (
        "golgari-reanimator-faithful"
    )

    prowess = {
        "Elusive Otter": 3,
        "Stormchaser's Talent": 3,
        "Practiced Offense": 3,
        "Hallowed Fountain": 2,
    }
    assert classify_counts(shadow, prowess, {}).selected_rule_id == (
        "azorius-prowess-primary"
    )
    below_prowess = dict(prowess)
    below_prowess["Hallowed Fountain"] = 1
    assert classify_counts(shadow, below_prowess, {}).selected_rule_id != (
        "azorius-prowess-primary"
    )

    pixie = {
        "Nurturing Pixie": 3,
        "Stormchaser's Talent": 3,
        "Hallowed Fountain": 2,
        "Watery Grave": 2,
    }
    assert classify_counts(shadow, pixie, {}).selected_rule_id == (
        "esper-pixie-primary"
    )
    below_pixie = dict(pixie)
    below_pixie["Watery Grave"] = 1
    assert classify_counts(shadow, below_pixie, {}).selected_rule_id != (
        "esper-pixie-primary"
    )


def test_standard_batch_3_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()

    sultai = {
        "Badgermole Cub": 3,
        "Icetill Explorer": 3,
        "Overlord of the Balemurk": 3,
        "Esper Origins": 2,
        "Superior Spider-Man": 2,
        "Breeding Pool": 2,
    }
    assert classify_counts(shadow, sultai, {}).selected_rule_id == (
        "sultai-midrange-primary"
    )
    below_sultai = dict(sultai)
    below_sultai["Icetill Explorer"] = 2
    assert classify_counts(shadow, below_sultai, {}).selected_rule_id != (
        "sultai-midrange-primary"
    )

    triumph = {
        "Political Triumph": 3,
        "Cosmogrand Zenith": 3,
        "Enduring Innocence": 3,
        "Invasion Reinforcements": 3,
    }
    assert classify_counts(shadow, triumph, {}).selected_rule_id == (
        "mono-white-triumph-primary"
    )
    below_triumph = dict(triumph)
    below_triumph["Political Triumph"] = 2
    assert classify_counts(shadow, below_triumph, {}).selected_rule_id != (
        "mono-white-triumph-primary"
    )

    burn = {
        "Death to Our Enemies": 3,
        "Plasma Bolt": 3,
        "Boltwave": 3,
        "Steam Vents": 2,
    }
    assert classify_counts(shadow, burn, {}).selected_rule_id == "izzet-burn-primary"
    below_burn = dict(burn)
    below_burn["Steam Vents"] = 1
    assert classify_counts(shadow, below_burn, {}).selected_rule_id != (
        "izzet-burn-primary"
    )

    simic_squirrel = {
        "Badgermole Cub": 3,
        "Nature's Rhythm": 2,
        "Enduring Vitality": 3,
        "The Unbeatable Squirrel Girl": 3,
        "Shang-Chi, Master of Kung Fu": 3,
        "Breeding Pool": 2,
    }
    assert classify_counts(shadow, simic_squirrel, {}).selected_rule_id == (
        "simic-rhythm-squirrel"
    )
    below_simic = dict(simic_squirrel)
    below_simic["Breeding Pool"] = 1
    assert classify_counts(shadow, below_simic, {}).selected_rule_id != (
        "simic-rhythm-squirrel"
    )

    simic_primary = {
        "Badgermole Cub": 4,
        "Nature's Rhythm": 3,
        "Gene Pollinator": 3,
        "Llanowar Elves": 4,
        "Breeding Pool": 2,
    }
    assert classify_counts(shadow, simic_primary, {}).selected_rule_id == (
        "simic-rhythm-primary"
    )
    mono_green_primary = dict(simic_primary)
    mono_green_primary.pop("Breeding Pool")
    assert classify_counts(shadow, mono_green_primary, {}).selected_rule_id != (
        "simic-rhythm-primary"
    )

    mono_green_squirrel = {
        "Badgermole Cub": 3,
        "Nature's Rhythm": 3,
        "Enduring Vitality": 3,
        "The Unbeatable Squirrel Girl": 3,
        "Shang-Chi, Master of Kung Fu": 3,
        "Forest": 12,
    }
    assert classify_counts(shadow, mono_green_squirrel, {}).selected_rule_id == (
        "mono-green-squirrel-combo-primary"
    )
    splashed_squirrel = {**mono_green_squirrel, "Stomping Ground": 1}
    assert classify_counts(shadow, splashed_squirrel, {}).selected_rule_id != (
        "mono-green-squirrel-combo-primary"
    )

    hulk = {
        "World War Hulk": 3,
        "Shared Roots": 3,
        "Terror of the Peaks": 3,
        "Stomping Ground": 3,
        "Island": 1,
    }
    assert classify_counts(shadow, hulk, {}).selected_rule_id == (
        "temur-hulk-ramp-primary"
    )
    below_hulk = dict(hulk)
    below_hulk.pop("Island")
    assert classify_counts(shadow, below_hulk, {}).selected_rule_id != (
        "temur-hulk-ramp-primary"
    )

    auras = {
        "Ethereal Armor": 3,
        "Super Intelligence": 3,
        "Skyward Spider": 3,
        "Hallowed Fountain": 2,
    }
    assert classify_counts(shadow, auras, {}).selected_rule_id == (
        "azorius-auras-primary"
    )
    below_auras = dict(auras)
    below_auras["Super Intelligence"] = 2
    assert classify_counts(shadow, below_auras, {}).selected_rule_id != (
        "azorius-auras-primary"
    )

    airbending = {
        "Aang, Swift Savior": 3,
        "Appa, Steadfast Guardian": 3,
        "Doc Aurlock, Grizzled Genius": 3,
    }
    assert classify_counts(shadow, airbending, {}).selected_rule_id == (
        "bant-airbending-primary"
    )
    obsolete_airbending = {
        "Aang, at the Crossroads": 4,
        "Appa, Steadfast Guardian": 3,
        "Doc Aurlock, Grizzled Genius": 3,
    }
    assert classify_counts(shadow, obsolete_airbending, {}).selected_rule_id != (
        "bant-airbending-primary"
    )


def test_standard_non_partition_families_capture_only_accepted_records() -> None:
    production = load_rule_set(PRODUCTION_PATH)
    shadow = _load_shadow_rules()
    expected_ids = _family_record_ids()
    assert {family_id: len(ids) for family_id, ids in expected_ids.items()} == {
        family_id: expectation[2]
        for family_id, expectation in EXPECTED_FAMILIES.items()
    }

    selected: dict[str, set[str]] = {
        rule_id: set() for _identity, rule_id, _count in EXPECTED_FAMILIES.values()
    }
    for record in load_unknown_records(ROOT):
        if record.format_id != "standard":
            continue
        baseline = classify_counts(
            production, record.main_counts(), record.side_counts()
        )
        result = classify_counts(shadow, record.main_counts(), record.side_counts())
        assert baseline.status == "unknown"
        if result.selected_rule_id in selected:
            selected[result.selected_rule_id].add(record.record_id)

    for family_id, (identity, rule_id, _count) in EXPECTED_FAMILIES.items():
        assert selected[rule_id] == expected_ids[family_id]
        assert all(
            classify_counts(
                shadow, record.main_counts(), record.side_counts()
            ).archetype_id
            == identity
            for record in load_unknown_records(ROOT)
            if record.record_id in expected_ids[family_id]
        )


def test_standard_control_partition_captures_only_accepted_records() -> None:
    production = load_rule_set(PRODUCTION_PATH)
    shadow = _load_shadow_rules()
    selected = {rule_id: set() for rule_id in CONTROL_PARTITION}

    for record in load_unknown_records(ROOT):
        if record.format_id != "standard":
            continue
        baseline = classify_counts(
            production, record.main_counts(), record.side_counts()
        )
        result = classify_counts(shadow, record.main_counts(), record.side_counts())
        assert baseline.status == "unknown"
        if result.selected_rule_id in selected:
            selected[result.selected_rule_id].add(record.record_id)

    assert {
        rule_id: selected[rule_id] for rule_id in CONTROL_PARTITION
    } == CONTROL_PARTITION


def test_standard_singleton_owner_decisions_capture_each_reviewed_record() -> None:
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    family_records = {
        family["family_id"]: {member["record_id"] for member in family["members"]}
        for family in queue["families"]
        if family["family_id"] in SINGLETON_RULES
    }
    assert set(family_records) == set(SINGLETON_RULES)
    assert all(len(record_ids) == 1 for record_ids in family_records.values())

    records = {record.record_id: record for record in load_unknown_records(ROOT)}
    shadow = _load_shadow_rules()
    for family_id, rule_id in SINGLETON_RULES.items():
        record_id = next(iter(family_records[family_id]))
        record = records[record_id]
        result = classify_counts(shadow, record.main_counts(), record.side_counts())
        disposition, target_identity = SINGLETON_DECISIONS[family_id]
        if disposition == "intentional_unknown":
            assert result.status == "unknown"
            assert result.selected_rule_id is None
        else:
            assert result.status == "classified"
            assert result.archetype_id == target_identity
            assert result.selected_rule_id == rule_id


def test_standard_accepted_current_and_frozen_replays_are_stable() -> None:
    production = load_rule_set(PRODUCTION_PATH)
    shadow = _load_shadow_rules()
    reordered = reordered_rule_set(shadow)
    accepted_singleton_rule_ids = {
        rule_id for rule_id in SINGLETON_RULES.values() if rule_id is not None
    }
    accepted_classified_migrations = {
        (
            "classified",
            "simic-rhythm",
            "mono-green-squirrel-combo",
            "mono-green-squirrel-combo-primary",
        ),
        (
            "classified",
            "mono-white-momo",
            "orzhov-momo",
            "orzhov-momo-primary",
        ),
        (
            "classified",
            "mono-blue-spellementals",
            "mono-blue-namor",
            "mono-blue-namor-primary",
        ),
    }
    current_transitions: Counter[tuple[str, str | None, str | None, str | None]] = (
        Counter()
    )
    current_statuses: Counter[str] = Counter()
    for _day, event in stats.load_all_events(ROOT, "standard"):
        for player in event.get("players", []):
            main, side = deck_to_counts(
                {
                    "main_deck": player.get("main_deck", []),
                    "sideboard": player.get("sideboard", []),
                }
            )
            baseline = classify_counts(production, main, side)
            result = classify_counts(shadow, main, side)
            assert identity_signature(result) == identity_signature(
                classify_counts(reordered, main, side)
            )
            current_statuses[result.status] += 1
            if identity_signature(result) != identity_signature(baseline):
                if baseline.status != "unknown":
                    assert (
                        baseline.status,
                        baseline.archetype_id,
                        result.archetype_id,
                        result.selected_rule_id,
                    ) in accepted_classified_migrations
                current_transitions[
                    (
                        baseline.status,
                        baseline.archetype_id,
                        result.archetype_id,
                        result.selected_rule_id,
                    )
                ] += 1
    assert current_statuses == Counter(classified=4732, unknown=1)
    expected_current_transitions = Counter(
        {
            ("unknown", None, "orzhov-lifegain", "orzhov-lifegain-primary"): 19,
            ("unknown", None, "five-color-humans", "five-color-humans-primary"): 13,
            (
                "unknown",
                None,
                "mono-green-mightiest",
                "mono-green-mightiest-primary",
            ): 7,
            ("unknown", None, "sultai-control", "sultai-control-consult"): 6,
            ("unknown", None, "azorius-control", "azorius-control-consult"): 4,
            ("unknown", None, "esper-control", "esper-control-consult"): 1,
            (
                "unknown",
                None,
                "golgari-reanimator",
                "golgari-reanimator-faithful",
            ): 3,
            ("unknown", None, "azorius-prowess", "azorius-prowess-primary"): 3,
            ("unknown", None, "esper-pixie", "esper-pixie-primary"): 2,
            ("unknown", None, "sultai-midrange", "sultai-midrange-primary"): 2,
            (
                "unknown",
                None,
                "mono-white-triumph",
                "mono-white-triumph-primary",
            ): 2,
            ("unknown", None, "izzet-burn", "izzet-burn-primary"): 2,
            ("unknown", None, "simic-rhythm", "simic-rhythm-squirrel"): 2,
            (
                "unknown",
                None,
                "mono-green-squirrel-combo",
                "mono-green-squirrel-combo-primary",
            ): 2,
            (
                "classified",
                "simic-rhythm",
                "mono-green-squirrel-combo",
                "mono-green-squirrel-combo-primary",
            ): 5,
            (
                "unknown",
                None,
                "temur-hulk-ramp",
                "temur-hulk-ramp-primary",
            ): 2,
            ("unknown", None, "azorius-auras", "azorius-auras-primary"): 2,
            (
                "unknown",
                None,
                "bant-airbending",
                "bant-airbending-primary",
            ): 2,
        }
    )
    expected_current_transitions.update(
        {
            transition: count
            for transition, count in current_transitions.items()
            if transition[0] == "unknown"
            and transition[3] in accepted_singleton_rule_ids
        }
    )
    expected_current_transitions.update(
        {
            (
                "classified",
                "mono-white-momo",
                "orzhov-momo",
                "orzhov-momo-primary",
            ): 7,
            (
                "classified",
                "mono-blue-spellementals",
                "mono-blue-namor",
                "mono-blue-namor-primary",
            ): 1,
        }
    )
    assert current_transitions == expected_current_transitions

    frozen_statuses: Counter[str] = Counter()
    frozen_transitions: Counter[tuple[str, str | None, str | None, str | None]] = (
        Counter()
    )
    for record in load_frozen_records(FROZEN_PATH):
        main, side = _record_counts(record)
        baseline = classify_counts(production, main, side)
        result = classify_counts(shadow, main, side)
        assert identity_signature(result) == identity_signature(
            classify_counts(reordered, main, side)
        )
        frozen_statuses[result.status] += 1
        if identity_signature(result) != identity_signature(baseline):
            if baseline.status != "unknown":
                assert (
                    baseline.status,
                    baseline.archetype_id,
                    result.archetype_id,
                    result.selected_rule_id,
                ) in accepted_classified_migrations
            frozen_transitions[
                (
                    baseline.status,
                    baseline.archetype_id,
                    result.archetype_id,
                    result.selected_rule_id,
                )
            ] += 1
    assert frozen_statuses == Counter(classified=3928, unknown=8)
    expected_frozen_transitions = Counter(
        {
            ("unknown", None, "sultai-control", "sultai-control-consult"): 4,
            ("unknown", None, "orzhov-lifegain", "orzhov-lifegain-primary"): 1,
            ("unknown", None, "azorius-control", "azorius-control-consult"): 3,
            ("unknown", None, "esper-control", "esper-control-consult"): 1,
            (
                "unknown",
                None,
                "golgari-reanimator",
                "golgari-reanimator-faithful",
            ): 3,
            ("unknown", None, "azorius-prowess", "azorius-prowess-primary"): 3,
            ("unknown", None, "esper-pixie", "esper-pixie-primary"): 2,
            ("unknown", None, "sultai-midrange", "sultai-midrange-primary"): 2,
            (
                "unknown",
                None,
                "mono-white-triumph",
                "mono-white-triumph-primary",
            ): 2,
            ("unknown", None, "izzet-burn", "izzet-burn-primary"): 2,
            ("unknown", None, "simic-rhythm", "simic-rhythm-squirrel"): 1,
            (
                "unknown",
                None,
                "mono-green-squirrel-combo",
                "mono-green-squirrel-combo-primary",
            ): 2,
            (
                "classified",
                "simic-rhythm",
                "mono-green-squirrel-combo",
                "mono-green-squirrel-combo-primary",
            ): 5,
            (
                "unknown",
                None,
                "bant-airbending",
                "bant-airbending-primary",
            ): 2,
        }
    )
    expected_frozen_transitions.update(
        {
            transition: count
            for transition, count in frozen_transitions.items()
            if transition[0] == "unknown"
            and transition[3] in accepted_singleton_rule_ids
        }
    )
    expected_frozen_transitions.update(
        {
            (
                "classified",
                "mono-white-momo",
                "orzhov-momo",
                "orzhov-momo-primary",
            ): 7,
            (
                "classified",
                "mono-blue-spellementals",
                "mono-blue-namor",
                "mono-blue-namor-primary",
            ): 1,
        }
    )
    assert frozen_transitions == expected_frozen_transitions
