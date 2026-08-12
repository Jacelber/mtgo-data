from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import yaml

from mtgmeta.classifier import classify_counts
from mtgmeta.classifier_features import load_semantic_feature_manifest
from mtgmeta.classifier_shadow_audit import (
    identity_signature,
    load_frozen_records,
    reordered_rule_set,
    rule_inventory,
)
from mtgmeta.config import parse_rule_text
from mtgmeta.deck import deck_to_counts
from mtgmeta.mtgo import stats
from tools.build_classifier_r4_shadow_rules import (
    AGADEEM_PERSIST_REDUCED_CRYPT_FAMILY,
    AMULET_SCAPESHIFT_FAMILY,
    ASMO_PERSIST_FAMILY,
    AZORIUS_MIRACLES_FAMILY,
    BADGERMOLE_FAMILY,
    BADGERMOLE_LANDFALL_FAMILY,
    BOGLES_FAMILY,
    BOROS_PONZA_CLASSIC_FAMILY,
    BOROS_PONZA_WILDFIRE_FAMILY,
    CHEERIOS_FAMILY,
    COFFERS_DIMIR_FAMILY,
    COFFERS_GOLGARI_FAMILY,
    COSMOGOYF_NECRO_FAMILY,
    DARK_MAESTRO_UMORI_FAMILY,
    DIMIR_PERSIST_FAMILY,
    DIMIR_GORYOS_FAMILY,
    DIMIR_UNEARTH_DIMIR_FAMILY,
    DIMIR_UNEARTH_WHITE_SPLASH_FAMILY,
    DOMAIN_BLINK_FAMILY,
    DOMAIN_PERSIST_FAMILY,
    DREDGE_FAMILY,
    EIGHT_RACK_FAMILY,
    ELDRAZI_AGGRO_FAMILY,
    ELDRAZI_OUROBOROID_FAMILY,
    ESPER_VALUE_FAMILY,
    FIVE_COLOR_ELEMENTALS_FAMILY,
    FIVE_COLOR_HUMANS_FAMILY,
    FOUR_COLOR_RITUAL_FAMILY,
    GOLGARI_DELIRIUM_FAMILY,
    GOLGARI_GORYOS_FAMILY,
    GOLGARI_YAWGMOTH_FAMILY,
    GRUUL_BROODSCALE_FAMILY,
    GRUUL_CRAGGANWICK_FAMILY,
    GRIXIS_TEMPO_FAMILY,
    GRUUL_MIDRANGE_FAMILY,
    GRUUL_VALAKUT_FAMILY,
    GRIXIS_DRESS_DOWN_FAMILY,
    GRIXIS_GORYOS_EMPEROR_FAMILY,
    GRIXIS_DEATHS_SHADOW_FAMILY,
    GRIXIS_PERSIST_WIZARDS_FAMILY,
    GRIXIS_TEMPO_BOWMASTERS_FAMILY,
    GRIXIS_TEMPO_COUNTERSPELL_FAMILY,
    GRIXIS_TEMPO_DRC_FROG_FAMILY,
    GLIMPSE_OF_TOMORROW_FAMILY,
    HARDENED_SCALES_FAMILY,
    HAMMER_KELLAN_FAMILY,
    HAMMER_TRADITIONAL_FAMILY,
    IZZET_THROUGH_THE_BREACH_FAMILY,
    IZZET_PROWESS_FAMILY,
    IZZET_STORM_FAMILY,
    IZZET_TEMPO_FAMILY,
    IZZET_TWIN_FAMILY,
    IZZET_CAULDRON_FAMILY,
    IZZET_EXTRA_TURNS_FAMILY,
    IZZET_WIZARDS_FAMILY,
    IZZET_WIZARDS_REVIEWED_WHITE_SPELLS,
    JESKAI_BLINK_FAMILY,
    JESKAI_ENERGY_LOW_RIDDLER_FAMILY,
    JUND_GOBLINS_FAMILY,
    LEYLINE_FLING_FAMILY,
    MARDU_VIAL_FAMILY,
    NAYA_MIDRANGE_FAMILY,
    MONO_BLUE_NAMOR_FAMILY,
    MONO_BLACK_SAGA_FAMILY,
    MONO_GREEN_TRUDGE_FAMILY,
    MONO_GREEN_STOMPY_COMPANION_FAMILY,
    MONO_GREEN_STOMPY_FAMILY,
    MONO_WHITE_HUMANS_FAMILY,
    ORZHOV_BLINK_SPLASH_FAMILY,
    ORZHOV_SOULTRADER_FAMILY,
    PRODUCTION_MODERN_SHA256,
    PRIMAL_PRAYERS_RECRUITER_FAMILY,
    PRIMAL_PRAYERS_ZENITH_FAMILY,
    RECLAMATION_FAMILY,
    RAKDOS_PERSIST_FAMILY,
    RAKDOS_PROWESS_FAMILY,
    RAKDOS_THROUGH_THE_BREACH_FAMILY,
    RAKDOS_AGGRO_FAMILY,
    RAKDOS_DELIRIUM_CASEY_FAMILY,
    RAKDOS_DELIRIUM_PHOENIX_FAMILY,
    RAKDOS_MIDRANGE_FAMILY,
    SCAPESHIFT_FAMILY,
    SOLEMNITY_PRISON_FAMILY,
    SOLEMNITY_BLINK_FAMILY,
    SHAPE_ANEW_FAMILY,
    SULTAI_PERSIST_FAMILY,
    SULTAI_FLICKER_FAMILY,
    SULTAI_TEMPO_FAMILY,
    THOPTER_SWORD_BANT_FAMILY,
    YAWGMOTH_ENERGY_FAMILY,
    build_shadow_rules,
    render_shadow_rules,
)
from tools.build_classifier_r4_unknown_review import load_unknown_records


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_PATH = (
    ROOT / "docs" / "audits" / "classifier-r4" / "baseline_rules" / "modern.yaml"
)
SHADOW_PATH = (
    ROOT / "docs" / "audits" / "classifier-r4" / "shadow_rules" / "modern.yaml"
)
FROZEN_PATH = ROOT / "tests" / "fixtures" / "modern" / "frozen_j6e_corpus.json"
CLOSEOUT_PATH = (
    ROOT / "docs" / "audits" / "classifier-r4" / "modern_closeout.yaml"
)
R4_INPUT_ROOT = (
    ROOT / "docs" / "audits" / "classifier-r4" / "baseline_unknown_inputs"
)


def _load_shadow_rules():
    rules = parse_rule_text(SHADOW_PATH.read_text(encoding="utf-8"))
    manifest = load_semantic_feature_manifest(
        ROOT / "configs" / "classifier_semantic_features.yaml"
    )
    assert (
        rules.semantic_feature_sha256
        == sha256(
            (ROOT / "configs" / "classifier_semantic_features.yaml").read_bytes()
        ).hexdigest()
    )
    return replace(rules, semantic_features=manifest)


def _load_baseline_rules():
    rules = parse_rule_text(PRODUCTION_PATH.read_text(encoding="utf-8"))
    manifest = load_semantic_feature_manifest(
        ROOT / "configs" / "classifier_semantic_features.yaml"
    )
    return replace(rules, semantic_features=manifest)


def _reproduction_root(tmp_path: Path) -> Path:
    root = tmp_path / "r4-modern-reproduction"
    (root / "my_archetypes").mkdir(parents=True)
    (root / "docs" / "audits" / "classifier-r4").mkdir(parents=True)
    (root / "my_archetypes" / "modern.yaml").write_bytes(PRODUCTION_PATH.read_bytes())
    (root / "docs" / "audits" / "classifier-r4" / "dispositions.yaml").write_bytes(
        (ROOT / "docs" / "audits" / "classifier-r4" / "dispositions.yaml").read_bytes()
    )
    return root


def _load_shadow_without_owner_bulk_batch1():
    document = yaml.safe_load(SHADOW_PATH.read_text(encoding="utf-8"))
    batch1_rule_ids = {
        "deaths-shadow-grixis-frog",
        "five-color-ritual-omnath",
        "boros-land-destruction-boom-wildfire",
        "boros-land-destruction-boom-classic",
        "grixis-persist-wizards",
        "grixis-tempo-bowmasters",
        "grixis-tempo-counterspell",
        "grixis-tempo-drc-frog",
        "prowess-rakdos",
    }
    for archetype in document["archetypes"]:
        archetype["rules"] = [
            rule for rule in archetype["rules"] if rule["id"] not in batch1_rule_ids
        ]
        if archetype["id"] == "five-color-ritual":
            archetype["priority"] = 324000
        if archetype["id"] == "prowess":
            archetype["subtypes"] = [
                subtype
                for subtype in archetype["subtypes"]
                if subtype["id"] != "rakdos"
            ]
    rules = parse_rule_text(yaml.safe_dump(document, sort_keys=False))
    manifest = load_semantic_feature_manifest(
        ROOT / "configs" / "classifier_semantic_features.yaml"
    )
    return replace(rules, semantic_features=manifest)


def _load_shadow_without_owner_bulk_batch2():
    document = yaml.safe_load(SHADOW_PATH.read_text(encoding="utf-8"))
    batch2_parent_ids = {
        "cheerios",
        "five-color-elementals",
        "glimpse-of-tomorrow",
        "izzet-cauldron",
        "izzet-extra-turns",
        "jund-goblins",
        "naya-midrange",
        "primal-prayers-combo",
        "rakdos-aggro",
        "shape-anew",
        "thopter-sword",
    }
    document["archetypes"] = [
        archetype
        for archetype in document["archetypes"]
        if archetype["id"] not in batch2_parent_ids
    ]
    rules = parse_rule_text(yaml.safe_dump(document, sort_keys=False))
    manifest = load_semantic_feature_manifest(
        ROOT / "configs" / "classifier_semantic_features.yaml"
    )
    return replace(rules, semantic_features=manifest)


def _load_shadow_without_owner_bulk_batch3():
    document = yaml.safe_load(SHADOW_PATH.read_text(encoding="utf-8"))
    batch3_parent_ids = {
        "azorius-miracles",
        "dimir-persist",
        "domain-blink",
        "domain-persist",
        "five-color-humans",
        "rakdos-delirium",
        "sultai-flicker",
    }
    document["archetypes"] = [
        archetype
        for archetype in document["archetypes"]
        if archetype["id"] not in batch3_parent_ids
    ]
    rules = parse_rule_text(yaml.safe_dump(document, sort_keys=False))
    manifest = load_semantic_feature_manifest(
        ROOT / "configs" / "classifier_semantic_features.yaml"
    )
    return replace(rules, semantic_features=manifest)


def _load_shadow_without_owner_bulk_batch4():
    document = yaml.safe_load(SHADOW_PATH.read_text(encoding="utf-8"))
    batch4_parent_ids = {
        "dimir-goryos",
        "dimir-unearth",
        "izzet-tempo",
        "mono-black-saga",
        "rakdos-midrange",
        "solemnity-blink",
        "sultai-tempo",
        "yawgmoth-energy",
    }
    document["archetypes"] = [
        archetype
        for archetype in document["archetypes"]
        if archetype["id"] not in batch4_parent_ids
    ]
    rules = parse_rule_text(yaml.safe_dump(document, sort_keys=False))
    manifest = load_semantic_feature_manifest(
        ROOT / "configs" / "classifier_semantic_features.yaml"
    )
    return replace(rules, semantic_features=manifest)


def _rakdos_hit(main: dict[str, int]) -> bool:
    return (
        main.get("Persist", 0) >= 3
        and main.get("Archon of Cruelty", 0) >= 3
        and main.get("Faithless Looting", 0) >= 3
        and main.get("Bloodghast", 0) >= 3
        and main.get("Stitcher's Supplier", 0) >= 3
        and main.get("Abhorrent Oculus", 0) == 0
    )


def _family_record_ids(family_id: str) -> set[str]:
    review = json.loads(
        (
            ROOT / "docs" / "audits" / "classifier-r4" / "unknown_family_queue.json"
        ).read_text(encoding="utf-8")
    )
    family = next(item for item in review["families"] if item["family_id"] == family_id)
    return {item["record_id"] for item in family["members"]}


def _partition_record_ids(family_id: str) -> dict[str, set[str]]:
    review = yaml.safe_load(
        (ROOT / "docs" / "audits" / "classifier-r4" / "dispositions.yaml").read_text(
            encoding="utf-8"
        )
    )
    family = next(item for item in review["families"] if item["family_id"] == family_id)
    return {
        item["target_identity"]: set(item["record_ids"]) for item in family["partition"]
    }


def test_modern_owner_closeout_is_complete_and_hash_locked() -> None:
    closeout = yaml.safe_load(CLOSEOUT_PATH.read_text(encoding="utf-8"))
    assert closeout["status"] == "owner_accepted_local_shadow_closed"
    assert closeout["format"] == "modern"
    assert closeout["scope"] == "non_production_shadow"
    assert closeout["review"] == {
        "candidate_families": 88,
        "owner_accepted_families": 88,
        "pending_families": 0,
        "disposition_counts": {
            "map_existing": 27,
            "new_identity": 61,
            "intentional_unknown": 0,
            "defer_insufficient_evidence": 0,
        },
        "current_corpus": {"records": 6784, "classified": 6784, "unknown": 0},
        "frozen_corpus": {"records": 5792, "classified": 5792, "unknown": 0},
        "tabletop_event_434455": {
            "records": 362,
            "batch_4_identity_changes": 0,
        },
    }

    dispositions = yaml.safe_load(
        (ROOT / "docs" / "audits" / "classifier-r4" / "dispositions.yaml").read_text(
            encoding="utf-8"
        )
    )
    modern = [
        family
        for family in dispositions["families"]
        if family["family_id"].startswith("modern-")
    ]
    standard = [
        family
        for family in dispositions["families"]
        if family["family_id"].startswith("standard-")
    ]
    assert len(modern) == 88
    assert all(family["review_status"] == "owner_accepted" for family in modern)
    assert Counter(family["disposition"] for family in modern) == Counter(
        {"new_identity": 61, "map_existing": 27}
    )
    assert len(standard) == 59
    assert all(
        family["review_status"] == "pending_owner_review" for family in standard
    )

    locked = {
        **closeout["accepted_artifacts"],
        "frozen_review_queue": closeout["source_evidence"]["frozen_review_queue"],
        **closeout["protected_evidence"],
    }
    for artifact in locked.values():
        path = ROOT / artifact["path"]
        if artifact["path"] == "my_archetypes/modern.yaml":
            path = PRODUCTION_PATH
        assert sha256(path.read_bytes()).hexdigest() == artifact["sha256"]

    assert closeout["next_format_boundary"] == {
        "standard_review_started": False,
        "standard_candidate_families": 59,
        "standard_pending_families": 59,
    }
    assert closeout["authorization"] == {
        "modern_closeout_local_commit": "owner_authorized_once_on_2026-08-12",
        "standard_development": False,
        "standard_commit": False,
        "production_promotion": False,
        "remote_publication": False,
        "landing_shadow": False,
        "p12_10": False,
    }


def test_shadow_is_deterministic_and_production_is_unchanged(tmp_path: Path) -> None:
    assert sha256(PRODUCTION_PATH.read_bytes()).hexdigest() == PRODUCTION_MODERN_SHA256
    reproduction_root = _reproduction_root(tmp_path)
    assert SHADOW_PATH.read_text(encoding="utf-8") == render_shadow_rules(
        reproduction_root
    )
    shadow_document = yaml.safe_load(SHADOW_PATH.read_text(encoding="utf-8"))
    assert shadow_document == build_shadow_rules(reproduction_root)

    production_document = yaml.safe_load(PRODUCTION_PATH.read_text(encoding="utf-8"))
    added_ids = {
        "asmo-persist",
        "azorius-miracles",
        "badgermole-combo",
        "bant-reclamation",
        "bogles",
        "cheerios",
        "coffers",
        "dark-maestro",
        "dimir-goryos",
        "dimir-persist",
        "dimir-unearth",
        "domain-blink",
        "domain-persist",
        "eight-rack",
        "eldrazi-ouroboroid",
        "golgari-goryos",
        "five-color-elementals",
        "five-color-humans",
        "glimpse-of-tomorrow",
        "grixis-dress-down",
        "grixis-tempo",
        "gruul-cragganwick",
        "gruul-midrange",
        "gruul-valakut",
        "golgari-delirium",
        "hardened-scales",
        "izzet-through-the-breach",
        "izzet-cauldron",
        "izzet-extra-turns",
        "izzet-storm",
        "izzet-tempo",
        "izzet-twin",
        "jund-goblins",
        "leyline-fling",
        "mardu-vial",
        "mono-black-saga",
        "mono-blue-namor",
        "mono-green-trudge",
        "mono-green-stompy",
        "mono-white-humans",
        "naya-midrange",
        "primal-prayers-combo",
        "rakdos-aggro",
        "rakdos-delirium",
        "rakdos-midrange",
        "rakdos-persist",
        "rakdos-through-the-breach",
        "scapeshift",
        "shape-anew",
        "solemnity-blink",
        "solemnity-prison",
        "sultai-persist",
        "sultai-flicker",
        "sultai-tempo",
        "temur-reclamation",
        "thopter-sword",
        "yawgmoth-energy",
    }
    assert {
        item["id"] for item in shadow_document["archetypes"] if item["id"] in added_ids
    } == added_ids
    shadow_without_added = deepcopy(shadow_document)
    shadow_without_added["archetypes"] = [
        item for item in shadow_document["archetypes"] if item["id"] not in added_ids
    ]
    gruul_rule = next(
        rule
        for archetype in shadow_without_added["archetypes"]
        if archetype["id"] == "broodscale-combo"
        for rule in archetype["rules"]
        if rule["id"] == "broodscale-combo-gruul"
    )
    blade = next(
        item
        for item in gruul_rule["conditions"]["all"]
        if item["card"] == "Blade of the Bloodchief"
    )
    assert blade["min_count"] == 2
    blade["min_count"] = 3
    for archetype in shadow_without_added["archetypes"]:
        if archetype["id"] == "esper-ketramose":
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"] != "esper-ketramose-low-count"
            ]
        elif archetype["id"] == "esper-blink":
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"] != "esper-blink-ephemerate"
            ]
        elif archetype["id"] == "amulet-titan":
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"] != "amulet-titan-scapeshift"
            ]
        elif archetype["id"] == "necrodominance":
            archetype["priority"] = 636000
            archetype["subtypes"] = [
                item for item in archetype["subtypes"] if item["id"] != "cosmogoyf"
            ]
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"] != "necrodominance-cosmogoyf"
            ]
        elif archetype["id"] == "soultrader":
            archetype["priority"] = 619000
            archetype["subtypes"] = [
                item for item in archetype["subtypes"] if item["id"] != "orzhov"
            ]
            archetype["rules"] = [
                item for item in archetype["rules"] if item["id"] != "soultrader-orzhov"
            ]
        elif archetype["id"] == "devoted-druid-combo":
            del archetype["subtypes"]
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"] == "devoted-druid-combo-primary"
            ]
            archetype["rules"][0]["subtype_id"] = None
            archetype["rules"][0]["conditions"]["all"] = [
                item
                for item in archetype["rules"][0]["conditions"]["all"]
                if not item["card"].startswith("__classifier-semantic-")
            ]
        elif archetype["id"] == "orzhov-blink":
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"] != "orzhov-blink-splash"
            ]
        elif archetype["id"] == "eldrazi-aggro":
            archetype["rules"][0]["conditions"]["all"] = [
                {
                    "card": "Eldrazi Linebreaker",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "It That Heralds the End",
                    "zone": "main",
                    "min_count": 3,
                },
            ]
        elif archetype["id"] == "dredge":
            archetype["rules"][0]["conditions"]["all"].append(
                {
                    "card": "Burning Inquiry",
                    "zone": "main",
                    "min_count": 3,
                }
            )
        elif archetype["id"] == "izzet-wizards":
            archetype["rules"][0]["conditions"]["all"] = [
                {
                    "card": "Snapcaster Mage",
                    "zone": "main",
                    "min_count": 2,
                },
                {
                    "card": "Flame of Anor",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Lightning Bolt",
                    "zone": "main",
                    "min_count": 2,
                },
            ]
        elif archetype["id"] == "prowess":
            archetype["subtypes"] = [
                item for item in archetype["subtypes"] if item["id"] != "rakdos"
            ]
            archetype["rules"] = [
                item for item in archetype["rules"] if item["id"] != "prowess-rakdos"
            ]
            izzet_rule = next(
                item for item in archetype["rules"] if item["id"] == "prowess-izzet"
            )
            conditions = izzet_rule["conditions"]["all"]
            assert conditions[2] == {
                "card": "Monastery Swiftspear",
                "zone": "main",
                "min_count": 2,
            }
            conditions[2]["min_count"] = 3
            conditions.insert(
                2,
                {
                    "card": "Dragon's Rage Channeler",
                    "zone": "main",
                    "min_count": 3,
                },
            )
        elif archetype["id"] == "jeskai-energy":
            assert archetype["rules"][0]["conditions"]["all"] == [
                {
                    "card": "Ajani, Nacatl Pariah",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Guide of Souls",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Ocelot Pride",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Quantum Riddler",
                    "zone": "main",
                    "min_count": 1,
                },
                {
                    "card": "__classifier-semantic-main-red-source__",
                    "zone": "main",
                    "min_count": 1,
                },
            ]
            archetype["rules"][0]["conditions"]["all"] = [
                {
                    "card": "Ajani, Nacatl Pariah",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Guide of Souls",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Quantum Riddler",
                    "zone": "main",
                    "min_count": 3,
                },
            ]
        elif archetype["id"] == "jeskai-blink":
            phelia = next(
                item
                for item in archetype["rules"][0]["conditions"]["all"]
                if item["card"] == "Phelia, Exuberant Shepherd"
            )
            assert phelia["min_count"] == 2
            phelia["min_count"] = 3
        elif archetype["id"] == "agadeem-persist":
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"] != "agadeem-persist-reduced-crypt"
            ]
        elif archetype["id"] == "golgari-yawgmoth":
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"] == "golgari-yawgmoth-primary"
            ]
        elif archetype["id"] == "grixis-goryos":
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"] == "grixis-goryos-primary"
            ]
        elif archetype["id"] == "dimir-tempo":
            archetype["subtypes"] = [
                {"id": "dimir", "name": "Dimir"},
                {"id": "grixis", "name": "Grixis"},
                {"id": "esper", "name": "Esper"},
            ]
            grixis_rule = next(
                item
                for item in archetype["rules"]
                if item["id"] == "dimir-tempo-grixis"
            )
            ragavan = grixis_rule["conditions"]["all"].pop()
            assert ragavan == {
                "card": "Ragavan, Nimble Pilferer",
                "zone": "main",
                "max_count": 2,
            }
        elif archetype["id"] == "hammer-time":
            production_hammer = deepcopy(
                next(
                    item
                    for item in production_document["archetypes"]
                    if item["id"] == "hammer-time"
                )
            )
            archetype.clear()
            archetype.update(production_hammer)
        elif archetype["id"] == "omnath-midrange":
            archetype["priority"] = 307000
            archetype["rules"][0]["priority"] = 307000
        elif archetype["id"] == "deaths-shadow":
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"] != "deaths-shadow-grixis-frog"
            ]
        elif archetype["id"] == "five-color-ritual":
            archetype["priority"] = 324000
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"] != "five-color-ritual-omnath"
            ]
        elif archetype["id"] == "boros-land-destruction":
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"]
                not in {
                    "boros-land-destruction-boom-wildfire",
                    "boros-land-destruction-boom-classic",
                }
            ]
        elif archetype["id"] == "grixis-persist":
            archetype["rules"] = [
                item
                for item in archetype["rules"]
                if item["id"] != "grixis-persist-wizards"
            ]
    assert shadow_without_added == production_document

    inventory = rule_inventory(_load_shadow_rules())
    assert (inventory["parent_count"], inventory["rule_count"]) == (127, 205)
    assert inventory["rule_ids_unique"] is True
    assert inventory["numeric_priorities_globally_unique"] is True


def test_owner_accepted_families_and_no_other_current_unknown_are_captured() -> None:
    production = _load_baseline_rules()
    shadow = _load_shadow_rules()
    modern_unknown = [
        item
        for item in load_unknown_records(R4_INPUT_ROOT)
        if item.format_id == "modern"
    ]
    rakdos_ids = _family_record_ids(RAKDOS_PERSIST_FAMILY)
    asmo_persist_ids = _family_record_ids(ASMO_PERSIST_FAMILY)
    izzet_storm_ids = _family_record_ids(IZZET_STORM_FAMILY)
    broodscale_ids = _family_record_ids(GRUUL_BROODSCALE_FAMILY)
    esper_partition = _partition_record_ids(ESPER_VALUE_FAMILY)
    ketramose_ids = esper_partition["esper-ketramose"]
    blink_ids = esper_partition["esper-blink"]
    scapeshift_partition = _partition_record_ids(SCAPESHIFT_FAMILY)
    naya_scapeshift_ids = scapeshift_partition["scapeshift/naya"]
    four_color_scapeshift_ids = scapeshift_partition["scapeshift/four-color"]
    gruul_valakut_ids = _family_record_ids(GRUUL_VALAKUT_FAMILY)
    gruul_midrange_ids = _family_record_ids(GRUUL_MIDRANGE_FAMILY)
    mono_blue_namor_ids = _family_record_ids(MONO_BLUE_NAMOR_FAMILY)
    golgari_goryos_ids = _family_record_ids(GOLGARI_GORYOS_FAMILY)
    izzet_prowess_ids = _family_record_ids(IZZET_PROWESS_FAMILY)
    solemnity_prison_ids = _family_record_ids(SOLEMNITY_PRISON_FAMILY)
    mono_green_trudge_ids = _family_record_ids(MONO_GREEN_TRUDGE_FAMILY)
    grixis_tempo_ids = _family_record_ids(GRIXIS_TEMPO_FAMILY)
    orzhov_soultrader_ids = _family_record_ids(ORZHOV_SOULTRADER_FAMILY)
    grixis_dress_down_ids = _family_record_ids(GRIXIS_DRESS_DOWN_FAMILY)
    grixis_goryos_emperor_ids = _family_record_ids(GRIXIS_GORYOS_EMPEROR_FAMILY)
    mono_white_humans_ids = _family_record_ids(MONO_WHITE_HUMANS_FAMILY)
    gruul_cragganwick_ids = _family_record_ids(GRUUL_CRAGGANWICK_FAMILY)
    hammer_kellan_ids = _family_record_ids(HAMMER_KELLAN_FAMILY)
    hammer_traditional_ids = _family_record_ids(HAMMER_TRADITIONAL_FAMILY)
    izzet_twin_ids = _family_record_ids(IZZET_TWIN_FAMILY)
    amulet_scapeshift_ids = _family_record_ids(AMULET_SCAPESHIFT_FAMILY)
    izzet_breach_ids = _family_record_ids(IZZET_THROUGH_THE_BREACH_FAMILY)
    rakdos_breach_ids = _family_record_ids(RAKDOS_THROUGH_THE_BREACH_FAMILY)
    cosmogoyf_necro_ids = _family_record_ids(COSMOGOYF_NECRO_FAMILY)
    badgermole_partition = _partition_record_ids(BADGERMOLE_FAMILY)
    badgermole_golgari_ids = badgermole_partition["badgermole-combo/golgari"]
    badgermole_mono_green_ids = badgermole_partition["badgermole-combo/mono-green"]
    badgermole_landfall_ids = _family_record_ids(BADGERMOLE_LANDFALL_FAMILY)
    coffers_partition = _partition_record_ids(DARK_MAESTRO_UMORI_FAMILY)
    dark_maestro_ids = coffers_partition["dark-maestro"]
    umori_coffers_ids = coffers_partition["coffers/umori"]
    dimir_coffers_ids = _family_record_ids(COFFERS_DIMIR_FAMILY)
    golgari_coffers_ids = _family_record_ids(COFFERS_GOLGARI_FAMILY)
    eight_rack_ids = _family_record_ids(EIGHT_RACK_FAMILY)
    leyline_fling_ids = _family_record_ids(LEYLINE_FLING_FAMILY)
    orzhov_blink_splash_ids = _family_record_ids(ORZHOV_BLINK_SPLASH_FAMILY)
    eldrazi_aggro_ids = _family_record_ids(ELDRAZI_AGGRO_FAMILY)
    eldrazi_ouroboroid_ids = _family_record_ids(ELDRAZI_OUROBOROID_FAMILY)
    sultai_persist_ids = _family_record_ids(SULTAI_PERSIST_FAMILY)
    golgari_delirium_ids = _family_record_ids(GOLGARI_DELIRIUM_FAMILY)
    bogles_ids = _family_record_ids(BOGLES_FAMILY)
    reclamation_ids = _family_record_ids(RECLAMATION_FAMILY)
    jeskai_blink_ids = _family_record_ids(JESKAI_BLINK_FAMILY)
    mardu_vial_ids = _family_record_ids(MARDU_VIAL_FAMILY)
    agadeem_reduced_crypt_ids = _family_record_ids(AGADEEM_PERSIST_REDUCED_CRYPT_FAMILY)
    jeskai_energy_ids = _family_record_ids(JESKAI_ENERGY_LOW_RIDDLER_FAMILY)
    mono_green_stompy_ids = _family_record_ids(MONO_GREEN_STOMPY_FAMILY)
    mono_green_stompy_companion_ids = _family_record_ids(
        MONO_GREEN_STOMPY_COMPANION_FAMILY
    )
    dredge_ids = _family_record_ids(DREDGE_FAMILY)
    hardened_scales_ids = _family_record_ids(HARDENED_SCALES_FAMILY)
    izzet_wizards_ids = _family_record_ids(IZZET_WIZARDS_FAMILY)
    golgari_yawgmoth_ids = _family_record_ids(GOLGARI_YAWGMOTH_FAMILY)
    batch1_expectations = {
        GRIXIS_DEATHS_SHADOW_FAMILY: (
            "deaths-shadow",
            "grixis",
            "deaths-shadow-grixis-frog",
        ),
        FOUR_COLOR_RITUAL_FAMILY: (
            "five-color-ritual",
            None,
            "five-color-ritual-omnath",
        ),
        BOROS_PONZA_WILDFIRE_FAMILY: (
            "boros-land-destruction",
            None,
            "boros-land-destruction-boom-wildfire",
        ),
        GRIXIS_PERSIST_WIZARDS_FAMILY: (
            "grixis-persist",
            None,
            "grixis-persist-wizards",
        ),
        GRIXIS_TEMPO_BOWMASTERS_FAMILY: (
            "grixis-tempo",
            None,
            "grixis-tempo-bowmasters",
        ),
        RAKDOS_PROWESS_FAMILY: ("prowess", "rakdos", "prowess-rakdos"),
        BOROS_PONZA_CLASSIC_FAMILY: (
            "boros-land-destruction",
            None,
            "boros-land-destruction-boom-classic",
        ),
        GRIXIS_TEMPO_COUNTERSPELL_FAMILY: (
            "grixis-tempo",
            None,
            "grixis-tempo-counterspell",
        ),
        GRIXIS_TEMPO_DRC_FROG_FAMILY: (
            "grixis-tempo",
            None,
            "grixis-tempo-drc-frog",
        ),
    }
    batch1_ids = {
        family_id: _family_record_ids(family_id) for family_id in batch1_expectations
    }
    batch1_by_record = {
        record_id: expectation
        for family_id, expectation in batch1_expectations.items()
        for record_id in batch1_ids[family_id]
    }
    batch2_expectations = {
        IZZET_EXTRA_TURNS_FAMILY: (
            "izzet-extra-turns",
            None,
            "izzet-extra-turns-primary",
        ),
        JUND_GOBLINS_FAMILY: ("jund-goblins", None, "jund-goblins-primary"),
        THOPTER_SWORD_BANT_FAMILY: (
            "thopter-sword",
            "bant",
            "thopter-sword-bant",
        ),
        RAKDOS_AGGRO_FAMILY: ("rakdos-aggro", None, "rakdos-aggro-primary"),
        PRIMAL_PRAYERS_RECRUITER_FAMILY: (
            "primal-prayers-combo",
            None,
            "primal-prayers-combo-primary",
        ),
        NAYA_MIDRANGE_FAMILY: ("naya-midrange", None, "naya-midrange-primary"),
        FIVE_COLOR_ELEMENTALS_FAMILY: (
            "five-color-elementals",
            None,
            "five-color-elementals-primary",
        ),
        CHEERIOS_FAMILY: ("cheerios", None, "cheerios-primary"),
        SHAPE_ANEW_FAMILY: ("shape-anew", None, "shape-anew-primary"),
        GLIMPSE_OF_TOMORROW_FAMILY: (
            "glimpse-of-tomorrow",
            None,
            "glimpse-of-tomorrow-primary",
        ),
        PRIMAL_PRAYERS_ZENITH_FAMILY: (
            "primal-prayers-combo",
            None,
            "primal-prayers-combo-primary",
        ),
        IZZET_CAULDRON_FAMILY: (
            "izzet-cauldron",
            None,
            "izzet-cauldron-primary",
        ),
    }
    batch2_ids = {
        family_id: _family_record_ids(family_id) for family_id in batch2_expectations
    }
    batch2_by_record = {
        record_id: expectation
        for family_id, expectation in batch2_expectations.items()
        for record_id in batch2_ids[family_id]
    }
    batch3_expectations = {
        DIMIR_PERSIST_FAMILY: (
            "dimir-persist",
            None,
            "dimir-persist-primary",
        ),
        DOMAIN_PERSIST_FAMILY: (
            "domain-persist",
            None,
            "domain-persist-primary",
        ),
        SULTAI_FLICKER_FAMILY: (
            "sultai-flicker",
            None,
            "sultai-flicker-primary",
        ),
        AZORIUS_MIRACLES_FAMILY: (
            "azorius-miracles",
            None,
            "azorius-miracles-primary",
        ),
        DOMAIN_BLINK_FAMILY: ("domain-blink", None, "domain-blink-primary"),
        RAKDOS_DELIRIUM_PHOENIX_FAMILY: (
            "rakdos-delirium",
            None,
            "rakdos-delirium-primary",
        ),
        FIVE_COLOR_HUMANS_FAMILY: (
            "five-color-humans",
            None,
            "five-color-humans-primary",
        ),
        RAKDOS_DELIRIUM_CASEY_FAMILY: (
            "rakdos-delirium",
            None,
            "rakdos-delirium-primary",
        ),
    }
    batch3_ids = {
        family_id: _family_record_ids(family_id) for family_id in batch3_expectations
    }
    batch3_by_record = {
        record_id: expectation
        for family_id, expectation in batch3_expectations.items()
        for record_id in batch3_ids[family_id]
    }
    batch4_expectations = {
        DIMIR_UNEARTH_WHITE_SPLASH_FAMILY: (
            "dimir-unearth",
            None,
            "dimir-unearth-primary",
        ),
        DIMIR_UNEARTH_DIMIR_FAMILY: (
            "dimir-unearth",
            None,
            "dimir-unearth-primary",
        ),
        DIMIR_GORYOS_FAMILY: ("dimir-goryos", None, "dimir-goryos-primary"),
        IZZET_TEMPO_FAMILY: ("izzet-tempo", None, "izzet-tempo-primary"),
        RAKDOS_MIDRANGE_FAMILY: (
            "rakdos-midrange",
            None,
            "rakdos-midrange-primary",
        ),
        YAWGMOTH_ENERGY_FAMILY: (
            "yawgmoth-energy",
            None,
            "yawgmoth-energy-primary",
        ),
        SULTAI_TEMPO_FAMILY: ("sultai-tempo", None, "sultai-tempo-primary"),
        SOLEMNITY_BLINK_FAMILY: (
            "solemnity-blink",
            None,
            "solemnity-blink-primary",
        ),
        MONO_BLACK_SAGA_FAMILY: (
            "mono-black-saga",
            None,
            "mono-black-saga-primary",
        ),
    }
    batch4_ids = {
        family_id: _family_record_ids(family_id) for family_id in batch4_expectations
    }
    batch4_by_record = {
        record_id: expectation
        for family_id, expectation in batch4_expectations.items()
        for record_id in batch4_ids[family_id]
    }
    selected_ids: dict[str, tuple[str | None, str | None]] = {}
    for record in modern_unknown:
        baseline = classify_counts(
            production, record.main_counts(), record.side_counts()
        )
        result = classify_counts(shadow, record.main_counts(), record.side_counts())
        assert baseline.status == "unknown"
        if record.record_id in rakdos_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("rakdos-persist", None)
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in asmo_persist_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("asmo-persist", None)
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in izzet_storm_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("izzet-storm", None)
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in broodscale_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "broodscale-combo",
                "gruul",
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in ketramose_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "esper-ketramose",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in blink_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("esper-blink", None)
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in naya_scapeshift_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("scapeshift", "naya")
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in four_color_scapeshift_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "scapeshift",
                "four-color",
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in gruul_valakut_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("gruul-valakut", None)
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in gruul_midrange_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("gruul-midrange", None)
            assert result.selected_rule_id == "gruul-midrange-primary"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in mono_blue_namor_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "mono-blue-namor",
                None,
            )
            assert result.selected_rule_id == "mono-blue-namor-primary"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in golgari_goryos_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "golgari-goryos",
                None,
            )
            assert result.selected_rule_id == "golgari-goryos-primary"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in izzet_prowess_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "prowess",
                "izzet",
            )
            assert result.selected_rule_id == "prowess-izzet"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in solemnity_prison_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "solemnity-prison",
                None,
            )
            assert result.selected_rule_id == "solemnity-prison-nine-lives"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in mono_green_trudge_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "mono-green-trudge",
                None,
            )
            assert result.selected_rule_id == "mono-green-trudge-primary"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in grixis_tempo_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "grixis-tempo",
                None,
            )
            assert result.selected_rule_id == "grixis-tempo-ragavan"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in orzhov_soultrader_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "soultrader",
                "orzhov",
            )
            assert result.selected_rule_id == "soultrader-orzhov"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in grixis_dress_down_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "grixis-dress-down",
                None,
            )
            assert result.selected_rule_id == "grixis-dress-down-primary"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in grixis_goryos_emperor_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "grixis-goryos",
                None,
            )
            assert result.selected_rule_id == "grixis-goryos-emperor"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in mono_white_humans_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "mono-white-humans",
                None,
            )
            assert result.selected_rule_id == "mono-white-humans-primary"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in gruul_cragganwick_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "gruul-cragganwick",
                None,
            )
            assert result.selected_rule_id == "gruul-cragganwick-primary"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in hammer_kellan_ids | hammer_traditional_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "hammer-time",
                "jeskai",
            )
            assert result.selected_rule_id in {
                "hammer-time-jeskai-kellan",
                "hammer-time-jeskai-red-spell",
            }
            assert (
                len(
                    [
                        item
                        for item in result.matched_rules
                        if item.archetype_id == "hammer-time"
                    ]
                )
                == 1
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in izzet_twin_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("izzet-twin", None)
            assert result.selected_rule_id == "izzet-twin-primary"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in amulet_scapeshift_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("amulet-titan", None)
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in izzet_breach_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "izzet-through-the-breach",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in rakdos_breach_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "rakdos-through-the-breach",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in cosmogoyf_necro_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "necrodominance",
                "cosmogoyf",
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in badgermole_golgari_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "badgermole-combo",
                "golgari",
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in badgermole_mono_green_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "badgermole-combo",
                "mono-green",
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in badgermole_landfall_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "badgermole-combo",
                "landfall",
            )
            assert result.selected_rule_id == "badgermole-combo-landfall"
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in dark_maestro_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "dark-maestro",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in umori_coffers_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("coffers", "umori")
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in dimir_coffers_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("coffers", "dimir")
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in golgari_coffers_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "coffers",
                "golgari",
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in eight_rack_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("eight-rack", None)
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in leyline_fling_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "leyline-fling",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in orzhov_blink_splash_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "orzhov-blink",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in eldrazi_aggro_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "eldrazi-aggro",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in eldrazi_ouroboroid_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "eldrazi-ouroboroid",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in sultai_persist_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "sultai-persist",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in golgari_delirium_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "golgari-delirium",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in bogles_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("bogles", None)
            assert result.selected_rule_id == "bogles-primary"
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in reclamation_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "temur-reclamation",
                None,
            )
            assert result.selected_rule_id == "temur-reclamation-primary"
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in jeskai_blink_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "jeskai-blink",
                None,
            )
            assert result.selected_rule_id == "jeskai-blink-primary"
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in mardu_vial_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "mardu-vial",
                None,
            )
            assert result.selected_rule_id == "mardu-vial-primary"
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in agadeem_reduced_crypt_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "agadeem-persist",
                None,
            )
            assert result.selected_rule_id == "agadeem-persist-reduced-crypt"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in jeskai_energy_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "jeskai-energy",
                None,
            )
            assert result.selected_rule_id == "jeskai-energy-primary"
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in (
            mono_green_stompy_ids | mono_green_stompy_companion_ids
        ):
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "mono-green-stompy",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in dredge_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == ("dredge", None)
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in hardened_scales_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "hardened-scales",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in izzet_wizards_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "izzet-wizards",
                None,
            )
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in golgari_yawgmoth_ids:
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                "golgari-yawgmoth",
                None,
            )
            assert result.selected_rule_id == "golgari-yawgmoth-young-wolf"
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in batch1_by_record:
            archetype_id, subtype_id, rule_id = batch1_by_record[record.record_id]
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                archetype_id,
                subtype_id,
            )
            assert result.selected_rule_id == rule_id
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in batch2_by_record:
            archetype_id, subtype_id, rule_id = batch2_by_record[record.record_id]
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                archetype_id,
                subtype_id,
            )
            assert result.selected_rule_id == rule_id
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in batch3_by_record:
            archetype_id, subtype_id, rule_id = batch3_by_record[record.record_id]
            assert result.status == "classified", (
                record.record_id,
                archetype_id,
                rule_id,
                result.status,
                result.selected_rule_id,
            )
            assert (result.archetype_id, result.subtype_id) == (
                archetype_id,
                subtype_id,
            )
            assert result.selected_rule_id == rule_id
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        elif record.record_id in batch4_by_record:
            archetype_id, subtype_id, rule_id = batch4_by_record[record.record_id]
            assert result.status == "classified"
            assert (result.archetype_id, result.subtype_id) == (
                archetype_id,
                subtype_id,
            )
            assert result.selected_rule_id == rule_id
            assert len(result.matched_rules) == 1
            selected_ids[record.record_id] = (result.archetype_id, result.subtype_id)
        else:
            assert result.status == "unknown", (
                record.record_id,
                result.archetype_id,
                result.subtype_id,
                result.selected_rule_id,
            )
    assert len(modern_unknown) == 188
    assert len(rakdos_ids) == 13
    assert len(asmo_persist_ids) == 3
    assert len(izzet_storm_ids) == 3
    assert len(broodscale_ids) == 12
    assert len(ketramose_ids) == 4
    assert len(blink_ids) == 3
    assert len(naya_scapeshift_ids) == 6
    assert len(four_color_scapeshift_ids) == 1
    assert len(gruul_valakut_ids) == 5
    assert len(gruul_midrange_ids) == 2
    assert len(mono_blue_namor_ids) == 2
    assert len(golgari_goryos_ids) == 2
    assert len(izzet_prowess_ids) == 2
    assert len(solemnity_prison_ids) == 2
    assert len(mono_green_trudge_ids) == 2
    assert len(grixis_tempo_ids) == 2
    assert len(orzhov_soultrader_ids) == 1
    assert len(grixis_dress_down_ids) == 1
    assert len(grixis_goryos_emperor_ids) == 1
    assert len(mono_white_humans_ids) == 1
    assert len(amulet_scapeshift_ids) == 1
    assert len(izzet_breach_ids) == 6
    assert len(rakdos_breach_ids) == 1
    assert len(cosmogoyf_necro_ids) == 6
    assert len(badgermole_golgari_ids) == 3
    assert len(badgermole_mono_green_ids) == 2
    assert len(badgermole_landfall_ids) == 2
    assert len(dark_maestro_ids) == 3
    assert len(umori_coffers_ids) == 2
    assert len(dimir_coffers_ids) == 1
    assert len(golgari_coffers_ids) == 1
    assert len(eight_rack_ids) == 5
    assert len(leyline_fling_ids) == 4
    assert len(orzhov_blink_splash_ids) == 4
    assert len(eldrazi_aggro_ids) == 3
    assert len(eldrazi_ouroboroid_ids) == 2
    assert len(sultai_persist_ids) == 2
    assert len(golgari_delirium_ids) == 2
    assert len(bogles_ids) == 2
    assert len(reclamation_ids) == 2
    assert len(jeskai_blink_ids) == 2
    assert len(mardu_vial_ids) == 2
    assert len(agadeem_reduced_crypt_ids) == 2
    assert len(mono_green_stompy_ids) == 3
    assert len(mono_green_stompy_companion_ids) == 1
    assert len(dredge_ids) == 3
    assert len(hardened_scales_ids) == 3
    assert len(izzet_wizards_ids) == 3
    assert len(golgari_yawgmoth_ids) == 3
    assert len(hammer_kellan_ids) == 1
    assert len(hammer_traditional_ids) == 1
    assert len(izzet_twin_ids) == 1
    assert {family_id: len(ids) for family_id, ids in batch1_ids.items()} == {
        family_id: 1 for family_id in batch1_expectations
    }
    assert {family_id: len(ids) for family_id, ids in batch2_ids.items()} == {
        family_id: 1 for family_id in batch2_expectations
    }
    assert {family_id: len(ids) for family_id, ids in batch3_ids.items()} == {
        family_id: 1 for family_id in batch3_expectations
    }
    assert {family_id: len(ids) for family_id, ids in batch4_ids.items()} == {
        family_id: 1 for family_id in batch4_expectations
    }
    assert set(selected_ids) == (
        rakdos_ids
        | asmo_persist_ids
        | izzet_storm_ids
        | broodscale_ids
        | ketramose_ids
        | blink_ids
        | naya_scapeshift_ids
        | four_color_scapeshift_ids
        | gruul_valakut_ids
        | gruul_midrange_ids
        | mono_blue_namor_ids
        | golgari_goryos_ids
        | izzet_prowess_ids
        | solemnity_prison_ids
        | mono_green_trudge_ids
        | grixis_tempo_ids
        | orzhov_soultrader_ids
        | grixis_dress_down_ids
        | grixis_goryos_emperor_ids
        | mono_white_humans_ids
        | gruul_cragganwick_ids
        | hammer_kellan_ids
        | hammer_traditional_ids
        | izzet_twin_ids
        | amulet_scapeshift_ids
        | izzet_breach_ids
        | rakdos_breach_ids
        | cosmogoyf_necro_ids
        | badgermole_golgari_ids
        | badgermole_mono_green_ids
        | badgermole_landfall_ids
        | dark_maestro_ids
        | umori_coffers_ids
        | dimir_coffers_ids
        | golgari_coffers_ids
        | eight_rack_ids
        | leyline_fling_ids
        | orzhov_blink_splash_ids
        | eldrazi_aggro_ids
        | eldrazi_ouroboroid_ids
        | sultai_persist_ids
        | golgari_delirium_ids
        | bogles_ids
        | reclamation_ids
        | jeskai_blink_ids
        | mardu_vial_ids
        | agadeem_reduced_crypt_ids
        | jeskai_energy_ids
        | mono_green_stompy_ids
        | mono_green_stompy_companion_ids
        | dredge_ids
        | hardened_scales_ids
        | izzet_wizards_ids
        | golgari_yawgmoth_ids
        | set(batch1_by_record)
        | set(batch2_by_record)
        | set(batch3_by_record)
        | set(batch4_by_record)
    )

    current_reclamation_hits: dict[
        str, set[tuple[str, int, str | None, str | None]]
    ] = {
        "temur-reclamation": set(),
        "bant-reclamation": set(),
    }
    current_landfall_hits: set[tuple[str, int, str, str | None, str | None]] = set()
    current_jeskai_blink_migrations: set[
        tuple[str, int, str, str | None, str | None]
    ] = set()
    current_agadeem_reduced_crypt_hits: set[
        tuple[str, int, str | None, str | None, int]
    ] = set()
    current_jeskai_energy_migrations: set[
        tuple[str, int, str, str | None, str | None, int]
    ] = set()
    current_gruul_midrange_hits: set[tuple[str, int, str | None, str | None, int]] = (
        set()
    )
    current_mono_blue_namor_hits: set[tuple[str, int, str | None, str | None, int]] = (
        set()
    )
    current_golgari_goryos_hits: set[tuple[str, int, str | None, str | None, int]] = (
        set()
    )
    current_izzet_prowess_migrations: set[
        tuple[str, int, str | None, str | None, int]
    ] = set()
    current_solemnity_prison_hits: set[
        tuple[str, int, str, str | None, str | None, int]
    ] = set()
    current_mono_green_trudge_hits: set[
        tuple[str, int, str, str | None, str | None, int]
    ] = set()
    current_grixis_tempo_hits: set[
        tuple[str, int, str, str | None, str | None, int]
    ] = set()
    current_orzhov_soultrader_hits: set[
        tuple[str, int, str, str | None, str | None, int]
    ] = set()
    current_grixis_dress_down_hits: set[
        tuple[str, int, str, str | None, str | None, int]
    ] = set()
    current_grixis_goryos_emperor_hits: set[
        tuple[str, int, str, str | None, str | None, int]
    ] = set()
    current_mono_white_humans_hits: set[
        tuple[str, str, str | None, str | None, str, int]
    ] = set()
    current_gruul_cragganwick_hits: set[
        tuple[str, int, str, str | None, str | None, str, int]
    ] = set()
    current_hammer_selected: Counter[str] = Counter()
    current_hammer_migrations: set[
        tuple[str, int, str | None, str | None, str, str]
    ] = set()
    current_izzet_twin_hits: set[tuple[str, int, str, str | None, str | None, int]] = (
        set()
    )
    batch1_rule_ids = {expectation[2] for expectation in batch1_expectations.values()}
    current_batch1_rule_hits: Counter[str] = Counter()
    batch2_rule_ids = {expectation[2] for expectation in batch2_expectations.values()}
    current_batch2_rule_hits: Counter[str] = Counter()
    batch3_rule_ids = {expectation[2] for expectation in batch3_expectations.values()}
    current_batch3_rule_hits: Counter[str] = Counter()
    batch4_rule_ids = {expectation[2] for expectation in batch4_expectations.values()}
    current_batch4_rule_hits: Counter[str] = Counter()
    current_energy_selected: Counter[str] = Counter()
    current_statuses: Counter[str] = Counter()
    for _day, event in stats.load_all_events(ROOT, "modern"):
        for index, player in enumerate(event.get("players", [])):
            main, side = deck_to_counts(
                {
                    "main_deck": player.get("main_deck", []),
                    "sideboard": player.get("sideboard", []),
                }
            )
            result = classify_counts(shadow, main, side)
            current_statuses[result.status] += 1
            if result.selected_rule_id in batch1_rule_ids:
                baseline = classify_counts(production, main, side)
                assert baseline.status == "unknown"
                current_batch1_rule_hits[result.selected_rule_id] += 1
            if result.selected_rule_id in batch2_rule_ids:
                baseline = classify_counts(production, main, side)
                assert baseline.status == "unknown"
                assert len(result.matched_rules) == 1
                current_batch2_rule_hits[result.selected_rule_id] += 1
            if result.selected_rule_id in batch3_rule_ids:
                current_batch3_rule_hits[result.selected_rule_id] += 1
            if result.selected_rule_id in batch4_rule_ids:
                current_batch4_rule_hits[result.selected_rule_id] += 1
            if result.archetype_id in {"boros-energy", "jeskai-energy"}:
                current_energy_selected[result.archetype_id] += 1
            if result.selected_rule_id == "agadeem-persist-reduced-crypt":
                baseline = classify_counts(production, main, side)
                current_agadeem_reduced_crypt_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        baseline.archetype_id,
                        baseline.subtype_id,
                        len(result.matched_rules),
                    )
                )
            if result.archetype_id == "jeskai-energy":
                baseline = classify_counts(production, main, side)
                if baseline.archetype_id != "jeskai-energy":
                    current_jeskai_energy_migrations.add(
                        (
                            str(event.get("event_id")),
                            index,
                            result.selected_rule_id or "",
                            baseline.archetype_id,
                            baseline.subtype_id,
                            len(result.matched_rules),
                        )
                    )
            if result.archetype_id == "gruul-midrange":
                baseline = classify_counts(production, main, side)
                current_gruul_midrange_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        baseline.archetype_id,
                        baseline.subtype_id,
                        len(result.matched_rules),
                    )
                )
            if result.archetype_id == "mono-blue-namor":
                baseline = classify_counts(production, main, side)
                current_mono_blue_namor_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        baseline.archetype_id,
                        baseline.subtype_id,
                        len(result.matched_rules),
                    )
                )
            if result.archetype_id == "golgari-goryos":
                baseline = classify_counts(production, main, side)
                current_golgari_goryos_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        baseline.archetype_id,
                        baseline.subtype_id,
                        len(result.matched_rules),
                    )
                )
            if (result.archetype_id, result.subtype_id) == ("prowess", "izzet"):
                baseline = classify_counts(production, main, side)
                if (baseline.archetype_id, baseline.subtype_id) != (
                    "prowess",
                    "izzet",
                ):
                    current_izzet_prowess_migrations.add(
                        (
                            str(event.get("event_id")),
                            index,
                            baseline.archetype_id,
                            baseline.subtype_id,
                            len(result.matched_rules),
                        )
                    )
            if result.archetype_id == "solemnity-prison":
                baseline = classify_counts(production, main, side)
                current_solemnity_prison_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        result.selected_rule_id or "",
                        baseline.archetype_id,
                        baseline.subtype_id,
                        len(result.matched_rules),
                    )
                )
            if result.archetype_id == "mono-green-trudge":
                baseline = classify_counts(production, main, side)
                current_mono_green_trudge_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        result.selected_rule_id or "",
                        baseline.archetype_id,
                        baseline.subtype_id,
                        len(result.matched_rules),
                    )
                )
            if result.archetype_id == "grixis-tempo":
                baseline = classify_counts(production, main, side)
                current_grixis_tempo_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        result.selected_rule_id or "",
                        baseline.archetype_id,
                        baseline.subtype_id,
                        len(result.matched_rules),
                    )
                )
            if (result.archetype_id, result.subtype_id) == (
                "soultrader",
                "orzhov",
            ):
                baseline = classify_counts(production, main, side)
                current_orzhov_soultrader_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        result.selected_rule_id or "",
                        baseline.archetype_id,
                        baseline.subtype_id,
                        len(result.matched_rules),
                    )
                )
            if result.archetype_id == "grixis-dress-down":
                baseline = classify_counts(production, main, side)
                current_grixis_dress_down_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        result.selected_rule_id or "",
                        baseline.archetype_id,
                        baseline.subtype_id,
                        len(result.matched_rules),
                    )
                )
            if result.selected_rule_id == "grixis-goryos-emperor":
                baseline = classify_counts(production, main, side)
                current_grixis_goryos_emperor_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        result.selected_rule_id,
                        baseline.archetype_id,
                        baseline.subtype_id,
                        len(result.matched_rules),
                    )
                )
            if result.selected_rule_id == "mono-white-humans-primary":
                baseline = classify_counts(production, main, side)
                current_mono_white_humans_hits.add(
                    (
                        str(event.get("event_id")),
                        baseline.status,
                        baseline.archetype_id,
                        baseline.subtype_id,
                        result.selected_rule_id,
                        len(result.matched_rules),
                    )
                )
            if result.selected_rule_id == "gruul-cragganwick-primary":
                baseline = classify_counts(production, main, side)
                current_gruul_cragganwick_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        baseline.status,
                        baseline.archetype_id,
                        baseline.subtype_id,
                        result.selected_rule_id,
                        len(result.matched_rules),
                    )
                )
            if result.archetype_id == "hammer-time":
                baseline = classify_counts(production, main, side)
                current_hammer_selected[result.subtype_id or "missing"] += 1
                assert (
                    len(
                        [
                            item
                            for item in result.matched_rules
                            if item.archetype_id == "hammer-time"
                        ]
                    )
                    == 1
                )
                if (baseline.archetype_id, baseline.subtype_id) != (
                    result.archetype_id,
                    result.subtype_id,
                ):
                    current_hammer_migrations.add(
                        (
                            str(event.get("event_id")),
                            index,
                            baseline.archetype_id,
                            baseline.subtype_id,
                            result.subtype_id or "missing",
                            result.selected_rule_id or "",
                        )
                    )
            if result.selected_rule_id == "izzet-twin-primary":
                baseline = classify_counts(production, main, side)
                current_izzet_twin_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        baseline.status,
                        baseline.archetype_id,
                        baseline.subtype_id,
                        len(result.matched_rules),
                    )
                )
            if result.archetype_id == "jeskai-blink":
                baseline = classify_counts(production, main, side)
                if baseline.archetype_id != "jeskai-blink":
                    current_jeskai_blink_migrations.add(
                        (
                            str(event.get("event_id")),
                            index,
                            result.selected_rule_id or "",
                            baseline.archetype_id,
                            baseline.subtype_id,
                        )
                    )
            if (result.archetype_id, result.subtype_id) == (
                "badgermole-combo",
                "landfall",
            ):
                baseline = classify_counts(production, main, side)
                current_landfall_hits.add(
                    (
                        str(event.get("event_id")),
                        index,
                        result.selected_rule_id or "",
                        baseline.archetype_id,
                        baseline.subtype_id,
                    )
                )
            if result.archetype_id not in current_reclamation_hits:
                continue
            baseline = classify_counts(production, main, side)
            current_reclamation_hits[result.archetype_id].add(
                (
                    str(event.get("event_id")),
                    index,
                    baseline.archetype_id,
                    baseline.subtype_id,
                )
            )
    assert current_reclamation_hits == {
        "temur-reclamation": {
            ("12842082", 9, None, None),
            ("12842096", 11, None, None),
        },
        "bant-reclamation": {
            ("12847691", 20, "chant-control", "azorius"),
            ("12847721", 15, "chant-control", "azorius"),
            ("12849488", 4, "chant-control", "azorius"),
        },
    }
    assert current_landfall_hits == {
        ("12843812", 9, "badgermole-combo-landfall", None, None),
        ("12843826", 2, "badgermole-combo-landfall", None, None),
    }
    assert current_jeskai_blink_migrations == {
        ("12839683", 24, "jeskai-blink-primary", None, None),
        ("12841352", 22, "jeskai-blink-primary", None, None),
    }
    assert current_agadeem_reduced_crypt_hits == {
        ("12844290", 0, None, None, 1),
        ("12847089", 0, None, None, 1),
    }
    assert current_jeskai_energy_migrations == {
        ("12842084", 22, "jeskai-energy-primary", None, None, 1),
        ("12842925", 26, "jeskai-energy-primary", None, None, 1),
    }
    assert current_gruul_midrange_hits == {
        ("12843416", 10, None, None, 1),
        ("12843794", 7, None, None, 1),
    }
    assert current_mono_blue_namor_hits == {
        ("12846509", 25, None, None, 1),
        ("12848199", 0, None, None, 1),
    }
    assert current_golgari_goryos_hits == {
        ("12840562", 9, None, None, 1),
        ("12840576", 9, None, None, 1),
    }
    assert current_izzet_prowess_migrations == {
        ("12841370", 22, None, None, 1),
    }
    assert current_solemnity_prison_hits == {
        ("12842082", 3, "solemnity-prison-nine-lives", None, None, 1),
        ("12842096", 4, "solemnity-prison-nine-lives", None, None, 1),
    }
    assert current_mono_green_trudge_hits == {
        ("12840523", 6, "mono-green-trudge-primary", None, None, 1),
        ("12841359", 21, "mono-green-trudge-primary", None, None, 1),
    }
    assert current_grixis_tempo_hits == {
        ("12840566", 31, "grixis-tempo-drc-frog", None, None, 1),
        ("12842914", 11, "grixis-tempo-bowmasters", None, None, 1),
        ("12847141", 25, "grixis-tempo-ragavan", "dimir-tempo", "grixis", 1),
        ("12848246", 4, "grixis-tempo-ragavan", None, None, 1),
        ("12848246", 22, "grixis-tempo-ragavan", "dimir-tempo", "grixis", 1),
        ("12848257", 5, "grixis-tempo-ragavan", None, None, 1),
        ("12850868", 14, "grixis-tempo-counterspell", None, None, 1),
    }
    assert current_orzhov_soultrader_hits == {
        ("12846455", 30, "soultrader-orzhov", None, None, 1),
    }
    assert current_grixis_dress_down_hits == {
        ("12849462", 22, "grixis-dress-down-primary", None, None, 1),
    }
    assert current_grixis_goryos_emperor_hits == {
        ("12843394", 24, "grixis-goryos-emperor", None, None, 1),
    }
    assert current_mono_white_humans_hits == {
        ("12847171", "unknown", None, None, "mono-white-humans-primary", 1),
    }
    assert current_gruul_cragganwick_hits == {
        (
            "12838154",
            19,
            "unknown",
            None,
            None,
            "gruul-cragganwick-primary",
            1,
        ),
    }
    assert current_hammer_selected == Counter(
        {"azorius": 17, "jeskai": 3, "boros": 2, "mono-white": 1}
    )
    assert current_hammer_migrations == {
        (
            "12840562",
            24,
            "hammer-time",
            "mono-white",
            "boros",
            "hammer-time-boros",
        ),
        (
            "12842929",
            24,
            "hammer-time",
            "mono-white",
            "boros",
            "hammer-time-boros",
        ),
        (
            "12844316",
            27,
            None,
            None,
            "jeskai",
            "hammer-time-jeskai-red-spell",
        ),
        (
            "12847137",
            20,
            "hammer-time",
            "azorius",
            "jeskai",
            "hammer-time-jeskai-red-source",
        ),
        (
            "12847739",
            20,
            None,
            None,
            "jeskai",
            "hammer-time-jeskai-kellan",
        ),
    }
    assert current_izzet_twin_hits == {
        ("12841352", 6, "unknown", None, None, 1),
    }
    assert current_batch1_rule_hits == Counter(
        {
            "grixis-persist-wizards": 1,
            "grixis-tempo-drc-frog": 1,
            "boros-land-destruction-boom-classic": 1,
            "grixis-tempo-bowmasters": 1,
            "prowess-rakdos": 1,
            "grixis-tempo-counterspell": 1,
            "five-color-ritual-omnath": 1,
            "boros-land-destruction-boom-wildfire": 1,
        }
    )
    assert current_batch2_rule_hits == Counter(
        {
            "primal-prayers-combo-primary": 2,
            "rakdos-aggro-primary": 1,
            "glimpse-of-tomorrow-primary": 1,
            "thopter-sword-bant": 1,
            "jund-goblins-primary": 1,
            "naya-midrange-primary": 1,
            "izzet-extra-turns-primary": 1,
            "cheerios-primary": 1,
            "izzet-cauldron-primary": 1,
            "shape-anew-primary": 1,
            "five-color-elementals-primary": 1,
        }
    )
    assert current_batch3_rule_hits == Counter(
        {
            "azorius-miracles-primary": 8,
            "domain-persist-primary": 3,
            "rakdos-delirium-primary": 2,
            "dimir-persist-primary": 1,
            "five-color-humans-primary": 1,
            "domain-blink-primary": 1,
            "sultai-flicker-primary": 1,
        }
    )
    assert current_batch4_rule_hits == Counter(
        {
            "dimir-unearth-primary": 9,
            "dimir-goryos-primary": 1,
            "izzet-tempo-primary": 1,
            "mono-black-saga-primary": 1,
            "rakdos-midrange-primary": 1,
            "solemnity-blink-primary": 1,
            "sultai-tempo-primary": 1,
            "yawgmoth-energy-primary": 1,
        }
    )
    assert current_statuses == Counter(classified=6784)
    assert current_energy_selected == Counter(
        {"boros-energy": 928, "jeskai-energy": 29}
    )

    review = yaml.safe_load(
        (ROOT / "docs" / "audits" / "classifier-r4" / "dispositions.yaml").read_text(
            encoding="utf-8"
        )
    )
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == RAKDOS_PERSIST_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "rakdos-persist"
    accepted = next(
        item for item in review["families"] if item["family_id"] == ASMO_PERSIST_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "asmo-persist"
    accepted = next(
        item for item in review["families"] if item["family_id"] == IZZET_STORM_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "izzet-storm"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == GRUUL_BROODSCALE_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "broodscale-combo/gruul"
    accepted = next(
        item for item in review["families"] if item["family_id"] == ESPER_VALUE_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "esper-ketramose|esper-blink"
    accepted = next(
        item for item in review["families"] if item["family_id"] == SCAPESHIFT_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "scapeshift/naya|scapeshift/four-color"
    accepted = next(
        item for item in review["families"] if item["family_id"] == GRUUL_VALAKUT_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "gruul-valakut"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == AMULET_SCAPESHIFT_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "amulet-titan"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == IZZET_THROUGH_THE_BREACH_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "izzet-through-the-breach"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == RAKDOS_THROUGH_THE_BREACH_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "rakdos-through-the-breach"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == COSMOGOYF_NECRO_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "necrodominance/cosmogoyf"
    accepted = next(
        item for item in review["families"] if item["family_id"] == BADGERMOLE_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == (
        "badgermole-combo/golgari|badgermole-combo/mono-green"
    )
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == BADGERMOLE_LANDFALL_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "badgermole-combo/landfall"
    accepted = next(
        item for item in review["families"] if item["family_id"] == JESKAI_BLINK_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "jeskai-blink"
    accepted = next(
        item for item in review["families"] if item["family_id"] == MARDU_VIAL_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "mardu-vial"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == AGADEEM_PERSIST_REDUCED_CRYPT_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "agadeem-persist"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == JESKAI_ENERGY_LOW_RIDDLER_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "jeskai-energy"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == GRUUL_MIDRANGE_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "gruul-midrange"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == MONO_BLUE_NAMOR_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "mono-blue-namor"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == GOLGARI_GORYOS_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "golgari-goryos"
    accepted = next(
        item for item in review["families"] if item["family_id"] == IZZET_PROWESS_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "prowess/izzet"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == SOLEMNITY_PRISON_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "solemnity-prison"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == MONO_GREEN_TRUDGE_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "mono-green-trudge"
    accepted = next(
        item for item in review["families"] if item["family_id"] == GRIXIS_TEMPO_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "grixis-tempo"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == ORZHOV_SOULTRADER_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "soultrader/orzhov"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == GRIXIS_DRESS_DOWN_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "grixis-dress-down"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == GRIXIS_GORYOS_EMPEROR_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "grixis-goryos"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == MONO_WHITE_HUMANS_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "mono-white-humans"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == GRUUL_CRAGGANWICK_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "gruul-cragganwick"
    accepted = next(
        item for item in review["families"] if item["family_id"] == HAMMER_KELLAN_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "hammer-time/jeskai"
    accepted = next(
        item for item in review["families"] if item["family_id"] == IZZET_TWIN_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "izzet-twin"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == HAMMER_TRADITIONAL_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "hammer-time/jeskai"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == DARK_MAESTRO_UMORI_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "dark-maestro|coffers/umori"
    accepted = next(
        item for item in review["families"] if item["family_id"] == COFFERS_DIMIR_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "coffers/dimir"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == COFFERS_GOLGARI_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "coffers/golgari"
    accepted = next(
        item for item in review["families"] if item["family_id"] == EIGHT_RACK_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "eight-rack"
    accepted = next(
        item for item in review["families"] if item["family_id"] == LEYLINE_FLING_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "leyline-fling"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == ORZHOV_BLINK_SPLASH_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "orzhov-blink"
    accepted = next(
        item for item in review["families"] if item["family_id"] == ELDRAZI_AGGRO_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "eldrazi-aggro"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == ELDRAZI_OUROBOROID_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "eldrazi-ouroboroid"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == SULTAI_PERSIST_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "sultai-persist"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == GOLGARI_DELIRIUM_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "golgari-delirium"
    accepted = next(
        item for item in review["families"] if item["family_id"] == BOGLES_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "bogles"
    accepted = next(
        item for item in review["families"] if item["family_id"] == RECLAMATION_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == ("temur-reclamation|bant-reclamation")
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == MONO_GREEN_STOMPY_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "mono-green-stompy"
    accepted = next(
        item for item in review["families"] if item["family_id"] == DREDGE_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "dredge"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == HARDENED_SCALES_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "hardened-scales"
    accepted = next(
        item for item in review["families"] if item["family_id"] == IZZET_WIZARDS_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "izzet-wizards"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == GOLGARI_YAWGMOTH_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "golgari-yawgmoth"
    accepted = next(
        item
        for item in review["families"]
        if item["family_id"] == MONO_GREEN_STOMPY_COMPANION_FAMILY
    )
    assert accepted["owner_accepted"] is True
    assert accepted["target_identity"] == "mono-green-stompy"


def test_frozen_corpus_has_only_expected_unknown_transitions_and_is_order_stable() -> (
    None
):
    production = _load_baseline_rules()
    shadow = _load_shadow_rules()
    reordered = reordered_rule_set(shadow)
    records = load_frozen_records(FROZEN_PATH)
    statuses: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    selected_rule_hits: Counter[str] = Counter()
    expected_jeskai_migrations = {
        "modern-baseline-1079",
        "modern-baseline-1208",
        "modern-baseline-5419",
    }
    observed_jeskai_migrations: set[str] = set()
    expected_bant_reclamation_migrations = {
        "modern-baseline-5205",
        "modern-baseline-5552",
    }
    observed_bant_reclamation_migrations: set[str] = set()
    expected_agadeem_reduced_crypt = {
        "modern-baseline-4129",
        "modern-baseline-5761",
    }
    observed_agadeem_reduced_crypt: set[str] = set()
    expected_jeskai_energy = {
        "modern-baseline-0983",
        "modern-baseline-1371",
    }
    observed_jeskai_energy: set[str] = set()
    expected_gruul_midrange = {
        "modern-baseline-1515",
        "modern-baseline-1608",
    }
    observed_gruul_midrange: set[str] = set()
    expected_mono_blue_namor = {"modern-baseline-4858"}
    observed_mono_blue_namor: set[str] = set()
    expected_golgari_goryos = {
        "modern-baseline-0682",
        "modern-baseline-0746",
    }
    observed_golgari_goryos: set[str] = set()
    expected_izzet_prowess = {"modern-baseline-0919"}
    observed_izzet_prowess: set[str] = set()
    expected_solemnity_prison = {
        "modern-baseline-0932",
        "modern-baseline-1029",
    }
    observed_solemnity_prison: set[str] = set()
    expected_mono_green_trudge = {
        "modern-baseline-2919",
        "modern-baseline-3126",
    }
    observed_mono_green_trudge: set[str] = set()
    expected_grixis_tempo_migrations = {"modern-baseline-2362"}
    observed_grixis_tempo_migrations: set[str] = set()
    expected_orzhov_soultrader = {"modern-baseline-4703"}
    observed_orzhov_soultrader: set[str] = set()
    observed_grixis_dress_down: set[str] = set()
    expected_grixis_goryos_emperor = {"modern-baseline-3801"}
    observed_grixis_goryos_emperor: set[str] = set()
    expected_mono_white_humans = {"modern-baseline-2386"}
    observed_mono_white_humans: set[str] = set()
    expected_gruul_cragganwick = {"modern-baseline-0212"}
    observed_gruul_cragganwick: set[str] = set()
    expected_hammer_migrations = {
        "modern-baseline-0697": (
            "hammer-time",
            "mono-white",
            "boros",
            "hammer-time-boros",
        ),
        "modern-baseline-1401": (
            "hammer-time",
            "mono-white",
            "boros",
            "hammer-time-boros",
        ),
        "modern-baseline-1788": (
            None,
            None,
            "jeskai",
            "hammer-time-jeskai-red-spell",
        ),
        "modern-baseline-5045": (
            "hammer-time",
            "azorius",
            "jeskai",
            "hammer-time-jeskai-red-source",
        ),
    }
    observed_hammer_migrations: set[str] = set()
    expected_izzet_twin = {"modern-baseline-0807"}
    observed_izzet_twin: set[str] = set()
    expected_batch1_unknown_rules = {
        "grixis-persist-wizards": "modern-baseline-0726",
        "grixis-tempo-drc-frog": "modern-baseline-0736",
        "boros-land-destruction-boom-classic": "modern-baseline-0758",
        "grixis-tempo-bowmasters": "modern-baseline-1324",
        "prowess-rakdos": "modern-baseline-2314",
        "five-color-ritual-omnath": "modern-baseline-2838",
        "boros-land-destruction-boom-wildfire": "modern-baseline-3076",
    }
    observed_batch1_unknown_rules: dict[str, str] = {}
    expected_batch2_unknown_rules = {
        "rakdos-aggro-primary": {"modern-baseline-1025"},
        "primal-prayers-combo-primary": {
            "modern-baseline-1137",
            "modern-baseline-4113",
        },
        "glimpse-of-tomorrow-primary": {"modern-baseline-1317"},
        "thopter-sword-bant": {"modern-baseline-2357"},
        "jund-goblins-primary": {"modern-baseline-3102"},
        "naya-midrange-primary": {"modern-baseline-3136"},
        "izzet-extra-turns-primary": {"modern-baseline-3815"},
        "cheerios-primary": {"modern-baseline-4876"},
    }
    observed_batch2_unknown_rules: dict[str, set[str]] = {
        rule_id: set() for rule_id in expected_batch2_unknown_rules
    }
    expected_batch3_unknown_rules = {
        "rakdos-delirium-primary": {
            "modern-baseline-0452",
            "modern-baseline-5177",
        },
        "dimir-persist-primary": {"modern-baseline-0668"},
        "domain-persist-primary": {"modern-baseline-0796"},
        "five-color-humans-primary": {"modern-baseline-1536"},
        "domain-blink-primary": {"modern-baseline-3145"},
        "sultai-flicker-primary": {"modern-baseline-4268"},
        "azorius-miracles-primary": {"modern-baseline-5335"},
    }
    observed_batch3_unknown_rules: dict[str, set[str]] = {
        rule_id: set() for rule_id in expected_batch3_unknown_rules
    }
    expected_batch4_unknown_rules = {
        "dimir-unearth-primary": {
            "modern-baseline-4244",
            "modern-baseline-5059",
        },
        "izzet-tempo-primary": {"modern-baseline-4123"},
        "mono-black-saga-primary": {"modern-baseline-2041"},
        "rakdos-midrange-primary": {"modern-baseline-2422"},
        "sultai-tempo-primary": {"modern-baseline-0692"},
    }
    observed_batch4_unknown_rules: dict[str, set[str]] = {
        rule_id: set() for rule_id in expected_batch4_unknown_rules
    }
    expected_dimir_unearth_migrations = {
        "modern-baseline-1111",
        "modern-baseline-3343",
    }
    observed_dimir_unearth_migrations: set[str] = set()
    expected_domain_persist_migrations = {
        "modern-baseline-0633",
        "modern-baseline-1560",
    }
    observed_domain_persist_migrations: set[str] = set()
    expected_azorius_miracles_migrations = {
        "modern-baseline-1010",
        "modern-baseline-1377",
        "modern-baseline-3809",
        "modern-baseline-5135",
    }
    observed_azorius_miracles_migrations: set[str] = set()

    for record in records:
        main = dict(record["main"])
        side = dict(record["side"])
        baseline = classify_counts(production, main, side)
        result = classify_counts(shadow, main, side)
        shuffled = classify_counts(reordered, main, side)
        assert identity_signature(result) == identity_signature(shuffled)
        statuses[result.status] += 1
        transitions[
            f"{baseline.archetype_id or baseline.status} -> "
            f"{result.archetype_id or result.status}"
        ] += 1
        if result.selected_rule_id in expected_batch1_unknown_rules:
            assert baseline.status == "unknown"
            assert (
                record["id"] == expected_batch1_unknown_rules[result.selected_rule_id]
            )
            assert len(result.matched_rules) == 1
            observed_batch1_unknown_rules[result.selected_rule_id] = record["id"]
        if result.selected_rule_id in expected_batch2_unknown_rules:
            assert baseline.status == "unknown"
            assert (
                record["id"] in expected_batch2_unknown_rules[result.selected_rule_id]
            )
            assert len(result.matched_rules) == 1
            observed_batch2_unknown_rules[result.selected_rule_id].add(record["id"])
        if (
            result.selected_rule_id in expected_batch3_unknown_rules
            and baseline.status == "unknown"
        ):
            assert (
                record["id"] in expected_batch3_unknown_rules[result.selected_rule_id]
            )
            assert len(result.matched_rules) == 1
            observed_batch3_unknown_rules[result.selected_rule_id].add(record["id"])
        if (
            result.selected_rule_id in expected_batch4_unknown_rules
            and baseline.status == "unknown"
        ):
            assert (
                record["id"] in expected_batch4_unknown_rules[result.selected_rule_id]
            )
            assert len(result.matched_rules) == 1
            observed_batch4_unknown_rules[result.selected_rule_id].add(record["id"])
        if (
            result.selected_rule_id == "dimir-unearth-primary"
            and baseline.status == "classified"
        ):
            assert record["id"] in expected_dimir_unearth_migrations
            assert (baseline.archetype_id, baseline.subtype_id) == (
                "dimir-tempo",
                "dimir",
            )
            assert len(result.matched_rules) == 2
            observed_dimir_unearth_migrations.add(record["id"])
        if result.selected_rule_id == "agadeem-persist-reduced-crypt":
            assert baseline.status == "unknown"
            assert record["id"] in expected_agadeem_reduced_crypt
            assert len(result.matched_rules) == 1
            observed_agadeem_reduced_crypt.add(record["id"])
        if (
            result.selected_rule_id == "jeskai-energy-primary"
            and baseline.status == "unknown"
        ):
            assert record["id"] in expected_jeskai_energy
            assert (result.archetype_id, result.subtype_id) == (
                "jeskai-energy",
                None,
            )
            assert len(result.matched_rules) == 1
            observed_jeskai_energy.add(record["id"])
        if result.selected_rule_id == "gruul-midrange-primary":
            assert baseline.status == "unknown"
            assert record["id"] in expected_gruul_midrange
            assert (result.archetype_id, result.subtype_id) == (
                "gruul-midrange",
                None,
            )
            assert len(result.matched_rules) == 1
            observed_gruul_midrange.add(record["id"])
        if result.selected_rule_id == "mono-blue-namor-primary":
            assert baseline.status == "unknown"
            assert record["id"] in expected_mono_blue_namor
            assert (result.archetype_id, result.subtype_id) == (
                "mono-blue-namor",
                None,
            )
            assert len(result.matched_rules) == 1
            observed_mono_blue_namor.add(record["id"])
        if result.selected_rule_id == "golgari-goryos-primary":
            assert baseline.status == "unknown"
            assert record["id"] in expected_golgari_goryos
            assert (result.archetype_id, result.subtype_id) == (
                "golgari-goryos",
                None,
            )
            assert len(result.matched_rules) == 1
            observed_golgari_goryos.add(record["id"])
        if result.selected_rule_id == "prowess-izzet" and baseline.status == "unknown":
            assert record["id"] in expected_izzet_prowess
            assert (result.archetype_id, result.subtype_id) == (
                "prowess",
                "izzet",
            )
            assert len(result.matched_rules) == 1
            observed_izzet_prowess.add(record["id"])
        if result.selected_rule_id == "solemnity-prison-nine-lives":
            assert baseline.status == "unknown"
            assert record["id"] in expected_solemnity_prison
            assert (result.archetype_id, result.subtype_id) == (
                "solemnity-prison",
                None,
            )
            assert len(result.matched_rules) == 1
            observed_solemnity_prison.add(record["id"])
        if result.selected_rule_id == "mono-green-trudge-primary":
            assert baseline.status == "unknown"
            assert record["id"] in expected_mono_green_trudge
            assert (result.archetype_id, result.subtype_id) == (
                "mono-green-trudge",
                None,
            )
            assert len(result.matched_rules) == 1
            observed_mono_green_trudge.add(record["id"])
        if result.selected_rule_id == "grixis-tempo-ragavan":
            assert record["id"] in expected_grixis_tempo_migrations
            assert (baseline.archetype_id, baseline.subtype_id) == (
                "dimir-tempo",
                "grixis",
            )
            assert (result.archetype_id, result.subtype_id) == (
                "grixis-tempo",
                None,
            )
            assert len(result.matched_rules) == 1
            observed_grixis_tempo_migrations.add(record["id"])
        if result.selected_rule_id == "soultrader-orzhov":
            assert baseline.status == "unknown"
            assert record["id"] in expected_orzhov_soultrader
            assert (result.archetype_id, result.subtype_id) == (
                "soultrader",
                "orzhov",
            )
            assert len(result.matched_rules) == 1
            observed_orzhov_soultrader.add(record["id"])
        if result.selected_rule_id == "grixis-dress-down-primary":
            assert baseline.status == "unknown"
            assert (result.archetype_id, result.subtype_id) == (
                "grixis-dress-down",
                None,
            )
            assert len(result.matched_rules) == 1
            observed_grixis_dress_down.add(record["id"])
        if result.selected_rule_id == "grixis-goryos-emperor":
            assert baseline.status == "unknown"
            assert record["id"] in expected_grixis_goryos_emperor
            assert (result.archetype_id, result.subtype_id) == (
                "grixis-goryos",
                None,
            )
            assert len(result.matched_rules) == 1
            observed_grixis_goryos_emperor.add(record["id"])
        if result.selected_rule_id == "mono-white-humans-primary":
            assert baseline.status == "unknown"
            assert record["id"] in expected_mono_white_humans
            assert (result.archetype_id, result.subtype_id) == (
                "mono-white-humans",
                None,
            )
            assert len(result.matched_rules) == 1
            observed_mono_white_humans.add(record["id"])
        if result.selected_rule_id == "gruul-cragganwick-primary":
            assert baseline.status == "unknown"
            assert record["id"] in expected_gruul_cragganwick
            assert (result.archetype_id, result.subtype_id) == (
                "gruul-cragganwick",
                None,
            )
            assert len(result.matched_rules) == 1
            observed_gruul_cragganwick.add(record["id"])
        if record["id"] in expected_hammer_migrations:
            assert (
                baseline.archetype_id,
                baseline.subtype_id,
                result.subtype_id,
                result.selected_rule_id,
            ) == expected_hammer_migrations[record["id"]]
            assert result.archetype_id == "hammer-time"
            assert (
                len(
                    [
                        item
                        for item in result.matched_rules
                        if item.archetype_id == "hammer-time"
                    ]
                )
                == 1
            )
            observed_hammer_migrations.add(record["id"])
        if result.selected_rule_id == "izzet-twin-primary":
            assert baseline.status == "unknown"
            assert record["id"] in expected_izzet_twin
            assert (result.archetype_id, result.subtype_id) == ("izzet-twin", None)
            assert len(result.matched_rules) == 1
            observed_izzet_twin.add(record["id"])
        if _rakdos_hit(main):
            selected_rule_hits[result.archetype_id or result.status] += 1
        if baseline.status == "classified":
            if record["id"] in expected_jeskai_migrations:
                assert baseline.archetype_id == "izzet-wizards"
                assert (result.archetype_id, result.subtype_id) == (
                    "jeskai-control",
                    None,
                )
                assert result.selected_rule_id == "jeskai-control-primary"
                observed_jeskai_migrations.add(record["id"])
            elif record["id"] in expected_bant_reclamation_migrations:
                assert (baseline.archetype_id, baseline.subtype_id) == (
                    "chant-control",
                    "azorius",
                )
                assert (result.archetype_id, result.subtype_id) == (
                    "bant-reclamation",
                    None,
                )
                assert result.selected_rule_id == "bant-reclamation-primary"
                observed_bant_reclamation_migrations.add(record["id"])
            elif record["id"] in expected_grixis_tempo_migrations:
                assert (baseline.archetype_id, baseline.subtype_id) == (
                    "dimir-tempo",
                    "grixis",
                )
                assert (result.archetype_id, result.subtype_id) == (
                    "grixis-tempo",
                    None,
                )
                assert result.selected_rule_id == "grixis-tempo-ragavan"
            elif record["id"] in expected_hammer_migrations:
                assert expected_hammer_migrations[record["id"]][0] == "hammer-time"
            elif record["id"] in expected_domain_persist_migrations:
                assert baseline.archetype_id == "domain-zoo"
                assert (result.archetype_id, result.subtype_id) == (
                    "domain-persist",
                    None,
                )
                assert result.selected_rule_id == "domain-persist-primary"
                assert len(result.matched_rules) == 2
                observed_domain_persist_migrations.add(record["id"])
            elif record["id"] in expected_azorius_miracles_migrations:
                assert baseline.archetype_id == "chant-control"
                assert baseline.subtype_id in {"azorius", "jeskai"}
                assert (result.archetype_id, result.subtype_id) == (
                    "azorius-miracles",
                    None,
                )
                assert result.selected_rule_id == "azorius-miracles-primary"
                assert len(result.matched_rules) == 2
                observed_azorius_miracles_migrations.add(record["id"])
            elif record["id"] in expected_dimir_unearth_migrations:
                assert (baseline.archetype_id, baseline.subtype_id) == (
                    "dimir-tempo",
                    "dimir",
                )
                assert (result.archetype_id, result.subtype_id) == (
                    "dimir-unearth",
                    None,
                )
                assert result.selected_rule_id == "dimir-unearth-primary"
                assert len(result.matched_rules) == 2
            elif baseline.archetype_id == "omnath-midrange":
                assert (result.archetype_id, result.subtype_id) == (
                    "omnath-midrange",
                    None,
                )
                assert result.selected_rule_id == "omnath-midrange-primary"
                assert result.selected_priority == 623700
            elif baseline.archetype_id == "devoted-druid-combo":
                assert (result.archetype_id, result.subtype_id) == (
                    "devoted-druid-combo",
                    "abzan",
                )
                assert result.selected_rule_id == "devoted-druid-combo-primary"
            else:
                assert identity_signature(result) == identity_signature(baseline)
        elif result.status == "classified":
            assert result.archetype_id in {
                "amulet-titan",
                "agadeem-persist",
                "asmo-persist",
                "badgermole-combo",
                "bant-reclamation",
                "bogles",
                "cheerios",
                "azorius-miracles",
                "rakdos-persist",
                "broodscale-combo",
                "coffers",
                "dark-maestro",
                "dimir-goryos",
                "dimir-persist",
                "dimir-unearth",
                "domain-blink",
                "domain-persist",
                "dredge",
                "eight-rack",
                "eldrazi-aggro",
                "eldrazi-ouroboroid",
                "esper-ketramose",
                "five-color-elementals",
                "five-color-humans",
                "glimpse-of-tomorrow",
                "golgari-delirium",
                "golgari-goryos",
                "golgari-yawgmoth",
                "grixis-dress-down",
                "grixis-goryos",
                "grixis-persist",
                "grixis-tempo",
                "gruul-cragganwick",
                "gruul-midrange",
                "gruul-valakut",
                "hardened-scales",
                "hammer-time",
                "five-color-ritual",
                "izzet-storm",
                "izzet-tempo",
                "izzet-through-the-breach",
                "izzet-twin",
                "izzet-wizards",
                "izzet-extra-turns",
                "jund-goblins",
                "jeskai-blink",
                "jeskai-energy",
                "leyline-fling",
                "mardu-vial",
                "mono-black-saga",
                "mono-blue-namor",
                "mono-green-trudge",
                "mono-green-stompy",
                "mono-white-humans",
                "naya-midrange",
                "orzhov-blink",
                "prowess",
                "primal-prayers-combo",
                "rakdos-aggro",
                "rakdos-delirium",
                "rakdos-midrange",
                "boros-land-destruction",
                "rakdos-through-the-breach",
                "scapeshift",
                "shape-anew",
                "solemnity-blink",
                "solemnity-prison",
                "soultrader",
                "sultai-persist",
                "sultai-flicker",
                "sultai-tempo",
                "temur-reclamation",
                "thopter-sword",
                "yawgmoth-energy",
            }

    assert len(records) == 5792
    assert statuses == Counter(classified=5792)
    assert observed_jeskai_migrations == expected_jeskai_migrations
    assert observed_bant_reclamation_migrations == expected_bant_reclamation_migrations
    assert observed_agadeem_reduced_crypt == expected_agadeem_reduced_crypt
    assert observed_jeskai_energy == expected_jeskai_energy
    assert observed_gruul_midrange == expected_gruul_midrange
    assert observed_mono_blue_namor == expected_mono_blue_namor
    assert observed_golgari_goryos == expected_golgari_goryos
    assert observed_izzet_prowess == expected_izzet_prowess
    assert observed_solemnity_prison == expected_solemnity_prison
    assert observed_mono_green_trudge == expected_mono_green_trudge
    assert observed_grixis_tempo_migrations == expected_grixis_tempo_migrations
    assert observed_orzhov_soultrader == expected_orzhov_soultrader
    assert observed_grixis_dress_down == set()
    assert observed_grixis_goryos_emperor == expected_grixis_goryos_emperor
    assert observed_mono_white_humans == expected_mono_white_humans
    assert observed_gruul_cragganwick == expected_gruul_cragganwick
    assert observed_hammer_migrations == set(expected_hammer_migrations)
    assert observed_izzet_twin == expected_izzet_twin
    assert observed_batch1_unknown_rules == expected_batch1_unknown_rules
    assert observed_batch2_unknown_rules == expected_batch2_unknown_rules
    assert observed_batch3_unknown_rules == expected_batch3_unknown_rules
    assert observed_batch4_unknown_rules == expected_batch4_unknown_rules
    assert observed_dimir_unearth_migrations == expected_dimir_unearth_migrations
    assert observed_domain_persist_migrations == expected_domain_persist_migrations
    assert observed_azorius_miracles_migrations == expected_azorius_miracles_migrations
    assert transitions["unknown -> rakdos-persist"] == 13
    assert transitions["unknown -> asmo-persist"] == 3
    assert transitions["unknown -> izzet-storm"] == 3
    assert transitions["unknown -> broodscale-combo"] == 2
    assert transitions["unknown -> esper-ketramose"] == 4
    assert transitions["unknown -> scapeshift"] == 7
    assert transitions["unknown -> gruul-valakut"] == 5
    assert transitions["unknown -> amulet-titan"] == 1
    assert transitions["unknown -> izzet-through-the-breach"] == 5
    assert transitions["unknown -> rakdos-through-the-breach"] == 1
    assert transitions["unknown -> badgermole-combo"] == 5
    assert transitions["unknown -> coffers"] == 4
    assert transitions["unknown -> dark-maestro"] == 3
    assert transitions["unknown -> eight-rack"] == 1
    assert transitions["unknown -> leyline-fling"] == 4
    assert transitions["unknown -> orzhov-blink"] == 3
    assert transitions["unknown -> eldrazi-aggro"] == 3
    assert transitions["unknown -> eldrazi-ouroboroid"] == 2
    assert transitions["unknown -> mono-green-stompy"] == 4
    assert transitions["unknown -> dredge"] == 3
    assert transitions["unknown -> hardened-scales"] == 3
    assert transitions["unknown -> izzet-wizards"] == 1
    assert transitions["unknown -> golgari-yawgmoth"] == 3
    assert transitions["unknown -> golgari-delirium"] == 2
    assert transitions["unknown -> bogles"] == 1
    assert transitions["unknown -> temur-reclamation"] == 2
    assert transitions["unknown -> jeskai-blink"] == 2
    assert transitions["unknown -> mardu-vial"] == 2
    assert transitions["unknown -> agadeem-persist"] == 2
    assert transitions["unknown -> jeskai-energy"] == 2
    assert transitions["unknown -> gruul-midrange"] == 2
    assert transitions["unknown -> mono-blue-namor"] == 1
    assert transitions["unknown -> golgari-goryos"] == 2
    assert transitions["unknown -> grixis-goryos"] == 1
    assert transitions["unknown -> prowess"] == 2
    assert transitions["unknown -> solemnity-prison"] == 2
    assert transitions["unknown -> mono-green-trudge"] == 2
    assert transitions["unknown -> soultrader"] == 1
    assert transitions["unknown -> grixis-dress-down"] == 0
    assert transitions["unknown -> mono-white-humans"] == 1
    assert transitions["unknown -> gruul-cragganwick"] == 1
    assert transitions["unknown -> hammer-time"] == 1
    assert transitions["unknown -> izzet-twin"] == 1
    assert transitions["unknown -> boros-land-destruction"] == 2
    assert transitions["unknown -> five-color-ritual"] == 1
    assert transitions["unknown -> grixis-persist"] == 1
    assert transitions["unknown -> grixis-tempo"] == 2
    assert transitions["unknown -> rakdos-aggro"] == 1
    assert transitions["unknown -> primal-prayers-combo"] == 2
    assert transitions["unknown -> glimpse-of-tomorrow"] == 1
    assert transitions["unknown -> thopter-sword"] == 1
    assert transitions["unknown -> jund-goblins"] == 1
    assert transitions["unknown -> naya-midrange"] == 1
    assert transitions["unknown -> izzet-extra-turns"] == 1
    assert transitions["unknown -> cheerios"] == 1
    assert transitions["unknown -> dimir-persist"] == 1
    assert transitions["unknown -> domain-persist"] == 1
    assert transitions["unknown -> sultai-flicker"] == 1
    assert transitions["unknown -> azorius-miracles"] == 1
    assert transitions["unknown -> domain-blink"] == 1
    assert transitions["unknown -> rakdos-delirium"] == 2
    assert transitions["unknown -> five-color-humans"] == 1
    assert transitions["unknown -> dimir-unearth"] == 2
    assert transitions["unknown -> izzet-tempo"] == 1
    assert transitions["unknown -> mono-black-saga"] == 1
    assert transitions["unknown -> rakdos-midrange"] == 1
    assert transitions["unknown -> sultai-tempo"] == 1
    assert transitions["dimir-tempo -> dimir-unearth"] == 2
    assert transitions["domain-zoo -> domain-persist"] == 2
    assert transitions["chant-control -> azorius-miracles"] == 4
    assert transitions["dimir-tempo -> grixis-tempo"] == 1
    assert transitions["unknown -> sultai-persist"] == 0
    assert transitions["chant-control -> bant-reclamation"] == 2
    assert transitions["izzet-wizards -> jeskai-control"] == 3
    assert (
        sum(
            count
            for transition, count in transitions.items()
            if transition.startswith("unknown -> ")
            and transition != "unknown -> unknown"
        )
        == 142
    )
    assert selected_rule_hits == Counter({"rakdos-persist": 13, "living-end": 2})


def test_owner_bulk_batch1_paths_boundaries_and_tabletop_transition() -> None:
    before_batch1 = _load_shadow_without_owner_bulk_batch1()
    shadow = _load_shadow_rules()
    positive_decks = {
        "deaths-shadow-grixis-frog": {
            "Death's Shadow": 3,
            "Thoughtseize": 3,
            "Street Wraith": 3,
            "Psychic Frog": 3,
            "Blood Crypt": 1,
            "Watery Grave": 1,
            "Steam Vents": 1,
        },
        "five-color-ritual-omnath": {
            "Birthing Ritual": 3,
            "Shardless Agent": 3,
            "Omnath, Locus of Creation": 3,
            "Elesh Norn, Mother of Machines": 1,
        },
        "boros-land-destruction-boom-wildfire": {
            "Boom/Bust": 3,
            "Flagstones of Trokair": 3,
            "Cleansing Wildfire": 3,
            "Price of Freedom": 3,
        },
        "boros-land-destruction-boom-classic": {
            "Boom/Bust": 3,
            "Flagstones of Trokair": 3,
            "Pillage": 3,
            "Stone Rain": 3,
        },
        "grixis-persist-wizards": {
            "Persist": 3,
            "Thundertrap Trainer": 3,
            "Traumatic Critique": 3,
            "Tamiyo, Inquisitive Student": 3,
            "Watery Grave": 1,
            "Steam Vents": 1,
        },
        "grixis-tempo-bowmasters": {
            "Dragon's Rage Channeler": 3,
            "Expressive Iteration": 3,
            "Orcish Bowmasters": 2,
            "Thoughtseize": 3,
            "Watery Grave": 1,
            "Steam Vents": 1,
        },
        "grixis-tempo-counterspell": {
            "Psychic Frog": 3,
            "Ragavan, Nimble Pilferer": 3,
            "Counterspell": 3,
            "Watery Grave": 1,
            "Steam Vents": 1,
        },
        "grixis-tempo-drc-frog": {
            "Psychic Frog": 3,
            "Dragon's Rage Channeler": 3,
            "Fatal Push": 3,
            "Watery Grave": 1,
            "Steam Vents": 1,
        },
        "prowess-rakdos": {
            "Cori-Steel Cutter": 3,
            "Lava Dart": 3,
            "Dragon's Rage Channeler": 3,
            "Monastery Swiftspear": 3,
            "Blood Crypt": 1,
            "Thoughtseize": 1,
        },
    }
    for rule_id, main in positive_decks.items():
        result = classify_counts(shadow, main, {})
        assert result.status == "classified", rule_id
        assert result.selected_rule_id == rule_id
        assert len(result.matched_rules) == 1

    stubborn = dict(
        positive_decks["deaths-shadow-grixis-frog"], **{"Stubborn Denial": 2}
    )
    assert (
        classify_counts(shadow, stubborn, {}).selected_rule_id == "deaths-shadow-grixis"
    )
    hellkite = dict(
        positive_decks["five-color-ritual-omnath"], **{"Magmatic Hellkite": 3}
    )
    assert (
        classify_counts(shadow, hellkite, {}).selected_rule_id
        == "five-color-ritual-primary"
    )
    goryos = dict(positive_decks["grixis-persist-wizards"], **{"Goryo's Vengeance": 1})
    assert (
        classify_counts(shadow, goryos, {}).selected_rule_id != "grixis-persist-wizards"
    )
    counter_push = dict(
        positive_decks["grixis-tempo-counterspell"], **{"Fatal Push": 3}
    )
    assert classify_counts(shadow, counter_push, {}).selected_rule_id != (
        "grixis-tempo-counterspell"
    )
    drc_ragavan = dict(
        positive_decks["grixis-tempo-drc-frog"],
        **{"Ragavan, Nimble Pilferer": 3},
    )
    assert classify_counts(shadow, drc_ragavan, {}).selected_rule_id == (
        "grixis-tempo-ragavan"
    )
    off_color = dict(
        positive_decks["grixis-tempo-bowmasters"], **{"Hallowed Fountain": 1}
    )
    assert classify_counts(shadow, off_color, {}).selected_rule_id != (
        "grixis-tempo-bowmasters"
    )
    steel_cutter = dict(positive_decks["prowess-rakdos"], Nethergoyf=3)
    steel_result = classify_counts(shadow, steel_cutter, {})
    assert steel_result.archetype_id == "rakdos-steel-cutter"

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_transitions: list[tuple[int, str, str, str | None, str | None, str]] = []
    for index, deck in enumerate(event["decklists"]):
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        baseline = classify_counts(before_batch1, dict(main), dict(side))
        result = classify_counts(shadow, dict(main), dict(side))
        if identity_signature(result) != identity_signature(baseline):
            tabletop_transitions.append(
                (
                    index,
                    baseline.status,
                    result.status,
                    result.archetype_id,
                    result.subtype_id,
                    result.selected_rule_id or "",
                )
            )
    assert len(event["decklists"]) == 362
    assert tabletop_transitions == [
        (
            279,
            "unknown",
            "classified",
            "deaths-shadow",
            "grixis",
            "deaths-shadow-grixis-frog",
        )
    ]


def test_owner_bulk_batch2_paths_boundaries_priority_and_tabletop_regression() -> None:
    before_batch2 = _load_shadow_without_owner_bulk_batch2()
    shadow = _load_shadow_rules()
    positive_decks = {
        "izzet-extra-turns-primary": {
            "Tablet of Discovery": 3,
            "Time Warp": 3,
            "Temporal Mastery": 3,
            "Steam Vents": 1,
        },
        "jund-goblins-primary": {
            "Birthing Ritual": 3,
            "Ignoble Hierarch": 3,
            "Conspicuous Snoop": 3,
            "Blood Crypt": 1,
            "Stomping Ground": 1,
        },
        "thopter-sword-bant": {
            "Thopter Foundry": 3,
            "Sword of the Meek": 2,
            "Malevolent Rumble": 3,
            "Breeding Pool": 1,
            "Hallowed Fountain": 1,
        },
        "rakdos-aggro-primary": {
            "Super Shredder": 3,
            "Moonshadow": 3,
            "Ragavan, Nimble Pilferer": 3,
            "Blood Crypt": 1,
        },
        "primal-prayers-combo-primary": {
            "Primal Prayers": 3,
            "Guide of Souls": 3,
            "Ocelot Pride": 3,
        },
        "naya-midrange-primary": {
            "Ragavan, Nimble Pilferer": 3,
            "Phlage, Titan of Fire's Fury": 3,
            "Wrenn and Six": 2,
            "Sacred Foundry": 1,
            "Stomping Ground": 1,
            "Temple Garden": 1,
        },
        "five-color-elementals-primary": {
            "Birthing Ritual": 3,
            "Omnath, Locus of Creation": 3,
            "Risen Reef": 3,
        },
        "cheerios-primary": {
            "Sram, Senior Edificer": 3,
            "Bone Saw": 3,
            "Kite Shield": 3,
        },
        "shape-anew-primary": {"Shape Anew": 3},
        "glimpse-of-tomorrow-primary": {"Glimpse of Tomorrow": 3},
        "izzet-cauldron-primary": {
            "Vivi Ornitier": 3,
            "Agatha's Soul Cauldron": 3,
        },
    }
    for rule_id, main in positive_decks.items():
        result = classify_counts(shadow, main, {})
        assert result.status == "classified", rule_id
        assert result.selected_rule_id == rule_id

    threshold_cards = {
        "izzet-extra-turns-primary": ("Tablet of Discovery", 2),
        "jund-goblins-primary": ("Birthing Ritual", 2),
        "thopter-sword-bant": ("Sword of the Meek", 1),
        "rakdos-aggro-primary": ("Super Shredder", 2),
        "primal-prayers-combo-primary": ("Primal Prayers", 2),
        "naya-midrange-primary": ("Wrenn and Six", 1),
        "five-color-elementals-primary": ("Risen Reef", 2),
        "cheerios-primary": ("Sram, Senior Edificer", 2),
        "shape-anew-primary": ("Shape Anew", 2),
        "glimpse-of-tomorrow-primary": ("Glimpse of Tomorrow", 2),
        "izzet-cauldron-primary": ("Vivi Ornitier", 2),
    }
    for rule_id, (card_name, count) in threshold_cards.items():
        below = dict(positive_decks[rule_id])
        below[card_name] = count
        assert classify_counts(shadow, below, {}).selected_rule_id != rule_id

    off_color_source = dict(positive_decks["izzet-extra-turns-primary"])
    off_color_source["Hallowed Fountain"] = 1
    assert classify_counts(shadow, off_color_source, {}).selected_rule_id != (
        "izzet-extra-turns-primary"
    )
    off_color_spell = classify_counts(
        shadow,
        positive_decks["izzet-extra-turns-primary"],
        {"Thoughtseize": 1},
    )
    assert off_color_spell.selected_rule_id != "izzet-extra-turns-primary"

    primal_energy = dict(
        positive_decks["primal-prayers-combo-primary"],
        **{"Ajani, Nacatl Pariah": 3},
    )
    primal_result = classify_counts(shadow, primal_energy, {})
    assert primal_result.selected_rule_id == "primal-prayers-combo-primary"
    assert {item.rule_id for item in primal_result.matched_rules} == {
        "primal-prayers-combo-primary",
        "boros-energy-primary",
    }

    ritual = dict(
        positive_decks["five-color-elementals-primary"],
        **{"Shardless Agent": 1},
    )
    assert classify_counts(shadow, ritual, {}).selected_rule_id != (
        "five-color-elementals-primary"
    )

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_transitions: list[tuple[int, str, str, str | None, str | None, str]] = []
    for index, deck in enumerate(event["decklists"]):
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        baseline = classify_counts(before_batch2, dict(main), dict(side))
        result = classify_counts(shadow, dict(main), dict(side))
        if identity_signature(result) != identity_signature(baseline):
            tabletop_transitions.append(
                (
                    index,
                    baseline.status,
                    result.status,
                    result.archetype_id,
                    result.subtype_id,
                    result.selected_rule_id or "",
                )
            )
    assert len(event["decklists"]) == 362
    assert tabletop_transitions == []


def test_owner_bulk_batch3_paths_boundaries_migrations_and_tabletop() -> None:
    before_batch3 = _load_shadow_without_owner_bulk_batch3()
    shadow = _load_shadow_rules()
    positive_decks = {
        "domain-persist-primary": {
            "Persist": 3,
            "Archon of Cruelty": 3,
            "Leyline of the Guildpact": 3,
            "Scion of Draco": 3,
        },
        "dimir-persist-primary": {
            "Persist": 3,
            "Archon of Cruelty": 3,
            "Psychic Frog": 3,
            "Watery Grave": 1,
        },
        "azorius-miracles-primary": {
            "Brainsurge": 3,
            "Terminus": 3,
            "Hallowed Fountain": 1,
        },
        "sultai-flicker-primary": {
            "Ghostly Flicker": 3,
            "Drowner of Truth": 3,
            "Psychic Frog": 3,
            "Breeding Pool": 1,
            "Watery Grave": 1,
        },
        "domain-blink-primary": {
            "Phelia, Exuberant Shepherd": 3,
            "Leyline Binding": 3,
            "Overlord of the Balemurk": 3,
        },
        "rakdos-delirium-primary": {
            "Nethergoyf": 3,
            "Dragon's Rage Channeler": 3,
            "Fear of Missing Out": 3,
            "Moonshadow": 3,
            "Detective's Phoenix": 2,
            "Mishra's Bauble": 3,
            "Blood Crypt": 1,
        },
        "five-color-humans-primary": {
            "Aether Vial": 3,
            "Champion of the Parish": 3,
            "Thalia's Lieutenant": 3,
            "Cavern of Souls": 3,
            "Secluded Courtyard": 3,
            "Meddling Mage": 3,
        },
    }
    for rule_id, main in positive_decks.items():
        result = classify_counts(shadow, main, {})
        assert result.status == "classified", rule_id
        assert result.selected_rule_id == rule_id

    threshold_cards = {
        "domain-persist-primary": ("Persist", 2),
        "dimir-persist-primary": ("Psychic Frog", 2),
        "azorius-miracles-primary": ("Terminus", 2),
        "sultai-flicker-primary": ("Ghostly Flicker", 2),
        "domain-blink-primary": ("Phelia, Exuberant Shepherd", 2),
        "rakdos-delirium-primary": ("Detective's Phoenix", 1),
        "five-color-humans-primary": ("Meddling Mage", 2),
    }
    for rule_id, (card_name, count) in threshold_cards.items():
        below = dict(positive_decks[rule_id])
        below[card_name] = count
        assert classify_counts(shadow, below, {}).selected_rule_id != rule_id

    domain_zoo = dict(
        positive_decks["domain-persist-primary"],
        **{"Leyline Binding": 3},
    )
    domain_result = classify_counts(shadow, domain_zoo, {})
    assert domain_result.selected_rule_id == "domain-persist-primary"
    assert {item.rule_id for item in domain_result.matched_rules} == {
        "domain-persist-primary",
        "domain-zoo-primary",
    }

    chant = dict(
        positive_decks["azorius-miracles-primary"],
        **{"Orim's Chant": 3, "Isochron Scepter": 1},
    )
    chant_result = classify_counts(shadow, chant, {})
    assert chant_result.selected_rule_id == "azorius-miracles-primary"
    assert {item.rule_id for item in chant_result.matched_rules} == {
        "azorius-miracles-primary",
        "chant-control-azorius",
    }

    dimir_red = classify_counts(
        shadow,
        positive_decks["dimir-persist-primary"],
        {"Galvanic Discharge": 1},
    )
    assert dimir_red.selected_rule_id != "dimir-persist-primary"
    sultai_white = classify_counts(
        shadow,
        positive_decks["sultai-flicker-primary"],
        {"Prismatic Ending": 1},
    )
    assert sultai_white.selected_rule_id != "sultai-flicker-primary"
    for exclusion in ("Hollow One", "Cori-Steel Cutter", "Death's Shadow"):
        excluded = dict(positive_decks["rakdos-delirium-primary"])
        excluded[exclusion] = 1
        assert classify_counts(shadow, excluded, {}).selected_rule_id != (
            "rakdos-delirium-primary"
        )

    current_transitions: set[tuple[str, int, str, str | None, str, str, int]] = set()
    for _day, event in stats.load_all_events(ROOT, "modern"):
        for index, player in enumerate(event.get("players", [])):
            main, side = deck_to_counts(
                {
                    "main_deck": player.get("main_deck", []),
                    "sideboard": player.get("sideboard", []),
                }
            )
            baseline = classify_counts(before_batch3, main, side)
            result = classify_counts(shadow, main, side)
            if identity_signature(result) != identity_signature(baseline):
                current_transitions.add(
                    (
                        str(event.get("event_id")),
                        index,
                        baseline.status,
                        baseline.archetype_id,
                        result.archetype_id or "",
                        result.selected_rule_id or "",
                        len(result.matched_rules),
                    )
                )
    assert current_transitions == {
        (
            "12839695",
            3,
            "unknown",
            None,
            "rakdos-delirium",
            "rakdos-delirium-primary",
            1,
        ),
        (
            "12840550",
            24,
            "classified",
            "domain-zoo",
            "domain-persist",
            "domain-persist-primary",
            2,
        ),
        ("12840556", 27, "unknown", None, "dimir-persist", "dimir-persist-primary", 1),
        (
            "12840631",
            27,
            "unknown",
            None,
            "domain-persist",
            "domain-persist-primary",
            1,
        ),
        (
            "12842090",
            17,
            "classified",
            "chant-control",
            "azorius-miracles",
            "azorius-miracles-primary",
            2,
        ),
        (
            "12842929",
            0,
            "classified",
            "chant-control",
            "azorius-miracles",
            "azorius-miracles-primary",
            2,
        ),
        (
            "12843416",
            31,
            "unknown",
            None,
            "five-color-humans",
            "five-color-humans-primary",
            1,
        ),
        (
            "12843420",
            23,
            "classified",
            "domain-zoo",
            "domain-persist",
            "domain-persist-primary",
            2,
        ),
        ("12841384", 8, "unknown", None, "domain-blink", "domain-blink-primary", 1),
        (
            "12843409",
            0,
            "classified",
            "chant-control",
            "azorius-miracles",
            "azorius-miracles-primary",
            2,
        ),
        (
            "12844826",
            11,
            "unknown",
            None,
            "sultai-flicker",
            "sultai-flicker-primary",
            1,
        ),
        (
            "12847674",
            14,
            "classified",
            "chant-control",
            "azorius-miracles",
            "azorius-miracles-primary",
            2,
        ),
        (
            "12847683",
            24,
            "unknown",
            None,
            "rakdos-delirium",
            "rakdos-delirium-primary",
            1,
        ),
        (
            "12848199",
            14,
            "classified",
            "chant-control",
            "azorius-miracles",
            "azorius-miracles-primary",
            2,
        ),
        (
            "12845628",
            22,
            "unknown",
            None,
            "azorius-miracles",
            "azorius-miracles-primary",
            1,
        ),
        (
            "12848164",
            19,
            "classified",
            "chant-control",
            "azorius-miracles",
            "azorius-miracles-primary",
            2,
        ),
        (
            "12848257",
            19,
            "classified",
            "chant-control",
            "azorius-miracles",
            "azorius-miracles-primary",
            2,
        ),
    }

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_transitions: list[int] = []
    for index, deck in enumerate(event["decklists"]):
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        baseline = classify_counts(before_batch3, dict(main), dict(side))
        result = classify_counts(shadow, dict(main), dict(side))
        if identity_signature(result) != identity_signature(baseline):
            tabletop_transitions.append(index)
    assert len(event["decklists"]) == 362
    assert tabletop_transitions == []


def test_owner_bulk_batch4_paths_boundaries_migrations_and_tabletop() -> None:
    before_batch4 = _load_shadow_without_owner_bulk_batch4()
    shadow = _load_shadow_rules()
    positive_decks = {
        "dimir-unearth-primary": {
            "Abhorrent Oculus": 3,
            "Unearth": 3,
            "Thought Scour": 3,
            "Psychic Frog": 3,
            "Watery Grave": 1,
        },
        "dimir-goryos-primary": {
            "Goryo's Vengeance": 3,
            "Atraxa, Grand Unifier": 3,
            "Psychic Frog": 3,
            "Watery Grave": 1,
        },
        "izzet-tempo-primary": {
            "Ragavan, Nimble Pilferer": 3,
            "Counterspell": 3,
            "Tamiyo, Inquisitive Student": 3,
            "Steam Vents": 1,
        },
        "rakdos-midrange-primary": {
            "Ragavan, Nimble Pilferer": 3,
            "Dauthi Voidwalker": 3,
            "Orcish Bowmasters": 3,
            "Seasoned Pyromancer": 3,
            "Thoughtseize": 3,
            "Blood Crypt": 1,
        },
        "yawgmoth-energy-primary": {
            "Yawgmoth, Thran Physician": 2,
            "Guide of Souls": 3,
            "Ocelot Pride": 3,
            "Young Wolf": 3,
            "Birthing Ritual": 3,
        },
        "sultai-tempo-primary": {
            "Ice-Fang Coatl": 3,
            "Counterspell": 3,
            "Fatal Push": 3,
            "Breeding Pool": 1,
            "Watery Grave": 1,
        },
        "solemnity-blink-primary": {
            "Solemnity": 3,
            "Overlord of the Balemurk": 3,
            "Phelia, Exuberant Shepherd": 2,
            "Solitude": 3,
        },
        "mono-black-saga-primary": {
            "Urza's Saga": 3,
            "Nethergoyf": 3,
            "Mishra's Bauble": 3,
            "Thoughtseize": 3,
            "Swamp": 4,
        },
    }
    for rule_id, main in positive_decks.items():
        result = classify_counts(shadow, main, {})
        assert result.status == "classified", rule_id
        assert result.selected_rule_id == rule_id

    threshold_cards = {
        "dimir-unearth-primary": ("Unearth", 2),
        "dimir-goryos-primary": ("Atraxa, Grand Unifier", 2),
        "izzet-tempo-primary": ("Tamiyo, Inquisitive Student", 2),
        "rakdos-midrange-primary": ("Dauthi Voidwalker", 2),
        "yawgmoth-energy-primary": ("Yawgmoth, Thran Physician", 1),
        "sultai-tempo-primary": ("Ice-Fang Coatl", 2),
        "solemnity-blink-primary": ("Phelia, Exuberant Shepherd", 1),
        "mono-black-saga-primary": ("Urza's Saga", 2),
    }
    for rule_id, (card_name, count) in threshold_cards.items():
        below = dict(positive_decks[rule_id])
        below[card_name] = count
        assert classify_counts(shadow, below, {}).selected_rule_id != rule_id
        assert classify_counts(shadow, {}, positive_decks[rule_id]).selected_rule_id != (
            rule_id
        )

    white_splash = dict(
        positive_decks["dimir-unearth-primary"],
        **{"Hallowed Fountain": 1},
    )
    assert (
        classify_counts(shadow, white_splash, {"Prismatic Ending": 1}).selected_rule_id
        == "dimir-unearth-primary"
    )
    for exclusion in ("Birthing Ritual", "Goryo's Vengeance", "Persist"):
        excluded = dict(positive_decks["dimir-unearth-primary"])
        excluded[exclusion] = 1
        assert classify_counts(shadow, excluded, {}).selected_rule_id != (
            "dimir-unearth-primary"
        )

    dimir_goryos_white = dict(
        positive_decks["dimir-goryos-primary"],
        **{"Hallowed Fountain": 1},
    )
    assert classify_counts(shadow, dimir_goryos_white, {}).selected_rule_id != (
        "dimir-goryos-primary"
    )

    for main_delta, side in (
        ({"Psychic Frog": 1}, {}),
        ({"Watery Grave": 1}, {}),
        ({}, {"Thoughtseize": 1}),
    ):
        excluded = dict(positive_decks["izzet-tempo-primary"], **main_delta)
        assert classify_counts(shadow, excluded, side).selected_rule_id != (
            "izzet-tempo-primary"
        )

    energy_overlap = dict(
        positive_decks["yawgmoth-energy-primary"],
        **{"Yawgmoth, Thran Physician": 3, "Grist, the Hunger Tide": 1},
    )
    energy_result = classify_counts(shadow, energy_overlap, {})
    assert energy_result.selected_rule_id == "yawgmoth-energy-primary"
    assert {item.rule_id for item in energy_result.matched_rules} == {
        "golgari-yawgmoth-primary",
        "golgari-yawgmoth-young-wolf",
        "yawgmoth-energy-primary",
    }

    for main_delta, side in (
        ({"Abhorrent Oculus": 1}, {}),
        ({"Birthing Ritual": 1}, {}),
        ({"Hallowed Fountain": 1}, {}),
        ({}, {"Fire Magic": 1}),
    ):
        excluded = dict(positive_decks["sultai-tempo-primary"], **main_delta)
        assert classify_counts(shadow, excluded, side).selected_rule_id != (
            "sultai-tempo-primary"
        )

    prison_overlap = dict(
        positive_decks["solemnity-blink-primary"],
        **{"Nine Lives": 3},
    )
    assert classify_counts(shadow, prison_overlap, {}).selected_rule_id == (
        "solemnity-prison-nine-lives"
    )

    black_fetch_targets = dict(
        positive_decks["mono-black-saga-primary"],
        **{
            "Overgrown Tomb": 1,
            "Shadowy Backstreet": 1,
            "Underground Mortuary": 1,
        },
    )
    assert (
        classify_counts(shadow, black_fetch_targets, {"Haywire Mite": 2}).selected_rule_id
        == "mono-black-saga-primary"
    )
    assert classify_counts(
        shadow,
        positive_decks["mono-black-saga-primary"],
        {"Pick Your Poison": 1},
    ).selected_rule_id != "mono-black-saga-primary"
    rack_overlap = dict(
        positive_decks["mono-black-saga-primary"],
        **{"The Rack": 3, "Raven's Crime": 2},
    )
    rack_result = classify_counts(shadow, rack_overlap, {})
    assert rack_result.selected_rule_id == "eight-rack-primary"
    assert {item.rule_id for item in rack_result.matched_rules} == {
        "eight-rack-primary",
        "mono-black-saga-primary",
    }

    current_transitions: set[
        tuple[
            str,
            int,
            str,
            str | None,
            str | None,
            str,
            str,
            int,
        ]
    ] = set()
    before_statuses: Counter[str] = Counter()
    after_statuses: Counter[str] = Counter()
    for _day, event in stats.load_all_events(ROOT, "modern"):
        for index, player in enumerate(event.get("players", [])):
            main, side = deck_to_counts(
                {
                    "main_deck": player.get("main_deck", []),
                    "sideboard": player.get("sideboard", []),
                }
            )
            baseline = classify_counts(before_batch4, main, side)
            result = classify_counts(shadow, main, side)
            before_statuses[baseline.status] += 1
            after_statuses[result.status] += 1
            if identity_signature(result) != identity_signature(baseline):
                current_transitions.add(
                    (
                        str(event.get("event_id")),
                        index,
                        baseline.status,
                        baseline.archetype_id,
                        baseline.subtype_id,
                        result.archetype_id or "",
                        result.selected_rule_id or "",
                        len(result.matched_rules),
                    )
                )
    assert before_statuses == Counter(classified=6775, unknown=9)
    assert after_statuses == Counter(classified=6784)
    assert current_transitions == {
        ("12840562", 19, "unknown", None, None, "sultai-tempo", "sultai-tempo-primary", 1),
        ("12842110", 22, "classified", "dimir-tempo", "dimir", "dimir-unearth", "dimir-unearth-primary", 2),
        ("12842139", 14, "classified", "dimir-tempo", "dimir", "dimir-unearth", "dimir-unearth-primary", 2),
        ("12843851", 26, "unknown", None, None, "izzet-tempo", "izzet-tempo-primary", 1),
        ("12844817", 19, "unknown", None, None, "dimir-unearth", "dimir-unearth-primary", 1),
        ("12844870", 24, "unknown", None, None, "mono-black-saga", "mono-black-saga-primary", 1),
        ("12847150", 2, "unknown", None, None, "dimir-unearth", "dimir-unearth-primary", 1),
        ("12847693", 21, "unknown", None, None, "rakdos-midrange", "rakdos-midrange-primary", 1),
        ("12848257", 16, "classified", "dimir-tempo", "dimir", "dimir-unearth", "dimir-unearth-primary", 2),
        ("12849434", 11, "classified", "dimir-tempo", "dimir", "dimir-unearth", "dimir-unearth-primary", 2),
        ("12849460", 2, "classified", "dimir-tempo", "dimir", "dimir-unearth", "dimir-unearth-primary", 2),
        ("12849467", 17, "classified", "dimir-tempo", "dimir", "dimir-unearth", "dimir-unearth-primary", 2),
        ("12849467", 30, "unknown", None, None, "yawgmoth-energy", "yawgmoth-energy-primary", 1),
        ("12849474", 9, "unknown", None, None, "dimir-goryos", "dimir-goryos-primary", 1),
        ("12849474", 10, "classified", "dimir-tempo", "dimir", "dimir-unearth", "dimir-unearth-primary", 2),
        ("12850696", 4, "unknown", None, None, "solemnity-blink", "solemnity-blink-primary", 1),
    }

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_transitions: list[int] = []
    for index, deck in enumerate(event["decklists"]):
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        baseline = classify_counts(before_batch4, dict(main), dict(side))
        result = classify_counts(shadow, dict(main), dict(side))
        if identity_signature(result) != identity_signature(baseline):
            tabletop_transitions.append(index)
    assert len(event["decklists"]) == 362
    assert tabletop_transitions == []


def test_mono_white_humans_boundaries_and_tabletop_regression() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Aether Vial": 3,
        "Champion of the Parish": 3,
        "Thalia's Lieutenant": 3,
        "Coppercoat Vanguard": 3,
        "Plains": 5,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "mono-white-humans",
        None,
    )
    assert result.selected_rule_id == "mono-white-humans-primary"
    assert result.selected_priority == 683500
    assert len(result.matched_rules) == 1

    for card, threshold in base.items():
        below_threshold = dict(base, **{card: threshold - 1})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown", card
    assert classify_counts(shadow, {}, base).status == "unknown"

    construction_cards = dict(
        base,
        **{
            "Adeline, Resplendent Cathar": 3,
            "Guide of Souls": 4,
            "Esper Sentinel": 4,
            "Ranger-Captain of Eos": 4,
            "Voice of Victory": 2,
            "Witch Enchanter": 4,
        },
    )
    result = classify_counts(shadow, construction_cards, {})
    assert result.selected_rule_id == "mono-white-humans-primary"

    for source in ("Island", "Swamp", "Mountain", "Forest"):
        assert classify_counts(shadow, dict(base, **{source: 1}), {}).status == (
            "unknown"
        )
    for spell in (
        "Preordain",
        "Thoughtseize",
        "Galvanic Discharge",
        "Pick Your Poison",
    ):
        assert classify_counts(shadow, base, {spell: 1}).status == "unknown"

    energy_hybrid = dict(
        base,
        **{
            "Ajani, Nacatl Pariah": 3,
            "Guide of Souls": 3,
            "Ocelot Pride": 3,
        },
    )
    result = classify_counts(shadow, energy_hybrid, {})
    assert (result.archetype_id, result.subtype_id) == ("boros-energy", None)
    assert result.selected_rule_id == "boros-energy-primary"

    five_color_ids = _family_record_ids("modern-unknown-c588af306ed2")
    five_color_records = [
        record
        for record in load_unknown_records(R4_INPUT_ROOT)
        if record.record_id in five_color_ids
    ]
    assert len(five_color_records) == 1
    five_color = five_color_records[0]
    five_color_result = classify_counts(
        shadow,
        five_color.main_counts(),
        five_color.side_counts(),
    )
    assert (five_color_result.archetype_id, five_color_result.subtype_id) == (
        "five-color-humans",
        None,
    )
    assert five_color_result.selected_rule_id == "five-color-humans-primary"

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_hits: list[str] = []
    for deck in event["decklists"]:
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        result = classify_counts(shadow, dict(main), dict(side))
        if result.archetype_id == "mono-white-humans":
            tabletop_hits.append(deck["participant_id"])
    assert len(event["decklists"]) == 362
    assert tabletop_hits == []


def test_gruul_cragganwick_boundaries_and_tabletop_regression() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Cragganwick Cremator": 3,
        "Yargle and Multani": 3,
        "Badgermole Cub": 3,
        "Blood Moon": 3,
        "Mountain": 1,
        "Forest": 1,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "gruul-cragganwick",
        None,
    )
    assert result.selected_rule_id == "gruul-cragganwick-primary"
    assert result.selected_priority == 641310
    assert len(result.matched_rules) == 1

    for card, threshold in base.items():
        below_threshold = dict(base, **{card: threshold - 1})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown", card
    assert classify_counts(shadow, {}, base).status == "unknown"

    construction_cards = dict(
        base,
        **{
            "Formidable Speaker": 2,
            "Monstrous Emergence": 2,
            "Screaming Nemesis": 3,
            "The Underworld Cookbook": 1,
            "Urza's Saga": 4,
        },
    )
    result = classify_counts(shadow, construction_cards, {})
    assert result.selected_rule_id == "gruul-cragganwick-primary"

    for source in ("Plains", "Island", "Swamp"):
        result = classify_counts(shadow, dict(base, **{source: 1}), {})
        assert result.selected_rule_id != "gruul-cragganwick-primary"
    for excluded in ("Goryo's Vengeance", "Emrakul, the Aeons Torn"):
        result = classify_counts(shadow, dict(base, **{excluded: 1}), {})
        assert result.selected_rule_id != "gruul-cragganwick-primary"

    goryos_hybrid = dict(
        base,
        **{
            "Goryo's Vengeance": 3,
            "Emrakul, the Aeons Torn": 3,
        },
    )
    result = classify_counts(shadow, goryos_hybrid, {})
    assert (result.archetype_id, result.subtype_id) == ("cremator-goryos", None)
    assert result.selected_rule_id == "cremator-goryos-primary"
    assert len(result.matched_rules) == 1

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_hits: list[str] = []
    for deck in event["decklists"]:
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        result = classify_counts(shadow, dict(main), dict(side))
        if result.archetype_id == "gruul-cragganwick":
            tabletop_hits.append(deck["participant_id"])
    assert len(event["decklists"]) == 362
    assert tabletop_hits == []


def test_hammer_time_full_parent_refactor_and_tabletop_regression() -> None:
    shadow = _load_shadow_rules()
    hammer = next(item for item in shadow.archetypes if item.id == "hammer-time")
    assert [(item.id, item.name) for item in hammer.subtypes] == [
        ("azorius", "Azorius"),
        ("boros", "Boros"),
        ("jeskai", "Jeskai"),
        ("mono-white", "Mono-White"),
    ]
    assert {item.id for item in hammer.rules} == {
        "hammer-time-azorius",
        "hammer-time-boros",
        "hammer-time-jeskai-kellan",
        "hammer-time-jeskai-red-source",
        "hammer-time-jeskai-red-spell",
        "hammer-time-mono-white",
    }

    traditional = {"Colossus Hammer": 3, "Puresteel Paladin": 3}
    cases = [
        (
            "mono-white",
            dict(traditional, Plains=1),
            {},
            "hammer-time-mono-white",
        ),
        (
            "azorius",
            dict(traditional, **{"Hallowed Fountain": 1}),
            {},
            "hammer-time-azorius",
        ),
        (
            "boros",
            dict(traditional, **{"Sacred Foundry": 1}),
            {},
            "hammer-time-boros",
        ),
        (
            "jeskai",
            dict(
                traditional,
                **{"Hallowed Fountain": 1, "Sacred Foundry": 1},
            ),
            {},
            "hammer-time-jeskai-red-source",
        ),
        (
            "jeskai",
            dict(traditional, **{"Hallowed Fountain": 1}),
            {"Wear/Tear": 1},
            "hammer-time-jeskai-red-spell",
        ),
        (
            "jeskai",
            {
                "Colossus Hammer": 3,
                "Kellan, the Fae-Blooded": 3,
                "Super-Soldier Serum": 2,
                "Hallowed Fountain": 1,
                "Sacred Foundry": 1,
            },
            {},
            "hammer-time-jeskai-kellan",
        ),
    ]
    for subtype, main, side, rule_id in cases:
        result = classify_counts(shadow, main, side)
        assert (result.status, result.archetype_id, result.subtype_id) == (
            "classified",
            "hammer-time",
            subtype,
        )
        assert result.selected_rule_id == rule_id
        assert (
            len(
                [
                    item
                    for item in result.matched_rules
                    if item.archetype_id == "hammer-time"
                ]
            )
            == 1
        )

    azorius = dict(traditional, **{"Hallowed Fountain": 1})
    for card, count in (("Colossus Hammer", 2), ("Puresteel Paladin", 2)):
        below_threshold = dict(azorius, **{card: count})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    assert classify_counts(shadow, {}, azorius).status == "unknown"

    kellan = {
        "Colossus Hammer": 3,
        "Kellan, the Fae-Blooded": 3,
        "Super-Soldier Serum": 2,
        "Hallowed Fountain": 1,
        "Sacred Foundry": 1,
    }
    for card, count in (
        ("Colossus Hammer", 2),
        ("Kellan, the Fae-Blooded", 2),
        ("Super-Soldier Serum", 1),
    ):
        below_threshold = dict(kellan, **{card: count})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    traditional_kellan = dict(kellan, **{"Puresteel Paladin": 3})
    result = classify_counts(shadow, traditional_kellan, {})
    assert (result.archetype_id, result.subtype_id, result.selected_rule_id) == (
        "hammer-time",
        "jeskai",
        "hammer-time-jeskai-red-source",
    )

    construction_cards = dict(
        azorius,
        **{
            "Metallic Rebuke": 4,
            "Stoneforge Mystic": 2,
            "Sigarda's Aid": 4,
            "Leyline Axe": 4,
            "Battlefield Improvisation": 2,
        },
    )
    assert classify_counts(shadow, construction_cards, {}).selected_rule_id == (
        "hammer-time-azorius"
    )
    assert classify_counts(shadow, azorius, {"Fire Magic": 1}).selected_rule_id == (
        "hammer-time-jeskai-red-spell"
    )

    for excluded_main in ("Swamp", "Forest"):
        result = classify_counts(shadow, dict(kellan, **{excluded_main: 1}), {})
        assert result.archetype_id != "hammer-time"
    for excluded_side in ("Thoughtseize", "Pick Your Poison"):
        result = classify_counts(shadow, kellan, {excluded_side: 1})
        assert result.archetype_id != "hammer-time"

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_hits: list[str] = []
    for deck in event["decklists"]:
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        result = classify_counts(shadow, dict(main), dict(side))
        if result.archetype_id == "hammer-time":
            tabletop_hits.append(deck["participant_id"])
    assert len(event["decklists"]) == 362
    assert tabletop_hits == []


def test_izzet_prowess_repaired_boundaries_and_precedence() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Cori-Steel Cutter": 3,
        "Lava Dart": 3,
        "Monastery Swiftspear": 2,
        "Preordain": 2,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "prowess",
        "izzet",
    )
    assert result.selected_rule_id == "prowess-izzet"
    assert result.selected_priority == 672200
    assert len(result.matched_rules) == 1

    for card, threshold in base.items():
        below_threshold = dict(base, **{card: threshold - 1})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown", card
    assert classify_counts(shadow, {}, base).status == "unknown"

    traditional = dict(
        base,
        **{
            "Dragon's Rage Channeler": 4,
            "Monastery Swiftspear": 4,
            "Slickshot Show-Off": 4,
        },
    )
    result = classify_counts(shadow, traditional, {})
    assert (result.archetype_id, result.subtype_id) == ("prowess", "izzet")

    soul_scar = dict(
        base,
        **{
            "Soul-Scar Mage": 4,
            "Stormchaser's Talent": 4,
            "Boomerang Basics": 4,
            "Mutagenic Growth": 3,
        },
    )
    result = classify_counts(shadow, soul_scar, {})
    assert (result.archetype_id, result.subtype_id) == ("prowess", "izzet")

    color_routes = {
        "Prismatic Ending": "jeskai",
        "Thoughtseize": "grixis",
        "Pick Your Poison": "temur",
    }
    for card, expected_subtype in color_routes.items():
        result = classify_counts(shadow, base, {card: 1})
        assert (result.archetype_id, result.subtype_id) == (
            "prowess",
            expected_subtype,
        )
        assert result.selected_rule_id != "prowess-izzet"

    lessons = dict(
        base,
        **{"Academic Dispute": 3, "Boomerang Basics": 3},
    )
    result = classify_counts(shadow, lessons, {})
    assert (result.archetype_id, result.subtype_id) == ("prowess", "lessons")
    assert result.selected_rule_id == "prowess-lessons"

    steel_cutter = dict(
        base,
        **{"Emry, Lurker of the Loch": 3, "Mishra's Bauble": 3},
    )
    result = classify_counts(shadow, steel_cutter, {})
    assert (result.archetype_id, result.subtype_id) == ("steel-cutter", "izzet")
    assert result.selected_rule_id == "steel-cutter-izzet"


def test_izzet_prowess_tabletop_regression() -> None:
    production = _load_baseline_rules()
    shadow = _load_shadow_rules()
    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    migrations: set[tuple[str, str, int]] = set()
    for deck in event["decklists"]:
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        baseline = classify_counts(production, dict(main), dict(side))
        result = classify_counts(shadow, dict(main), dict(side))
        if baseline.archetype_id == "prowess":
            assert identity_signature(result) == identity_signature(baseline)
        if (result.archetype_id, result.subtype_id) == ("prowess", "izzet") and (
            baseline.archetype_id,
            baseline.subtype_id,
        ) != ("prowess", "izzet"):
            migrations.add(
                (
                    deck["participant_id"],
                    baseline.status,
                    len(result.matched_rules),
                )
            )
    assert len(event["decklists"]) == 362
    assert migrations == {
        (
            "participant-3fffa8fa87a6c710c6a1d7a99775194e1fd221077ff17aadd1079b20468a5246",
            "unknown",
            1,
        )
    }


def test_solemnity_prison_boundaries_and_tabletop_regression() -> None:
    shadow = _load_shadow_rules()

    nine_lives = {"Solemnity": 3, "Nine Lives": 3}
    result = classify_counts(shadow, nine_lives, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "solemnity-prison",
        None,
    )
    assert result.selected_rule_id == "solemnity-prison-nine-lives"
    assert result.selected_priority == 673700
    assert len(result.matched_rules) == 1
    for card in nine_lives:
        below_threshold = dict(nine_lives, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    assert classify_counts(shadow, {}, nine_lives).status == "unknown"

    full_reviewed_build = dict(
        nine_lives,
        **{
            "Phyrexian Unlife": 4,
            "United Battlefront": 4,
            "Greater Auramancy": 4,
            "Sterling Grove": 4,
            "Solitary Confinement": 2,
        },
    )
    result = classify_counts(shadow, full_reviewed_build, {})
    assert result.selected_rule_id == "solemnity-prison-nine-lives"
    assert len(result.matched_rules) == 1

    unlife = {
        "Solemnity": 3,
        "Phyrexian Unlife": 3,
        "Nine Lives": 2,
    }
    result = classify_counts(shadow, unlife, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "solemnity-prison",
        None,
    )
    assert result.selected_rule_id == "solemnity-prison-unlife"
    assert result.selected_priority == 673600
    assert len(result.matched_rules) == 1
    for card in ("Solemnity", "Phyrexian Unlife"):
        below_threshold = dict(unlife, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"

    both_partners = dict(unlife, **{"Nine Lives": 3})
    result = classify_counts(shadow, both_partners, {})
    assert result.selected_rule_id == "solemnity-prison-nine-lives"
    assert len(result.matched_rules) == 1

    broodmoth_combo = {"Solemnity": 3, "Luminous Broodmoth": 3}
    assert classify_counts(shadow, broodmoth_combo, {}).status == "unknown"

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_hits: set[str] = set()
    for deck in event["decklists"]:
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        result = classify_counts(shadow, dict(main), dict(side))
        if result.archetype_id == "solemnity-prison":
            tabletop_hits.add(deck["participant_id"])
    assert len(event["decklists"]) == 362
    assert tabletop_hits == set()


def test_mono_green_trudge_boundaries_and_tabletop_regression() -> None:
    shadow = _load_shadow_rules()
    core = {
        "Slumbering Trudge": 3,
        "The Great Henge": 3,
    }
    result = classify_counts(shadow, core, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "mono-green-trudge",
        None,
    )
    assert result.selected_rule_id == "mono-green-trudge-primary"
    assert result.selected_priority == 641050
    assert len(result.matched_rules) == 1
    for card in core:
        below_threshold = dict(core, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    assert classify_counts(shadow, {}, core).status == "unknown"

    reviewed_build = dict(
        core,
        **{
            "Badgermole Cub": 4,
            "Fanatic of Rhonas": 4,
            "Life's Legacy": 3,
            "Ouroboroid": 3,
            "Green Sun's Zenith": 4,
            "Ashaya, Soul of the Wild": 1,
            "Quirion Ranger": 4,
            "Springheart Nantuko": 4,
            "Summoner's Pact": 3,
            "Craterhoof Behemoth": 1,
        },
    )
    result = classify_counts(shadow, reviewed_build, {})
    assert result.selected_rule_id == "mono-green-trudge-primary"
    assert len(result.matched_rules) == 1

    two_rigging = dict(core, **{"Fight Rigging": 2})
    assert classify_counts(shadow, two_rigging, {}).archetype_id == (
        "mono-green-trudge"
    )
    fight_rigging = dict(
        core,
        **{"Fight Rigging": 3, "Fanatic of Rhonas": 3},
    )
    result = classify_counts(shadow, fight_rigging, {})
    assert (result.archetype_id, result.subtype_id) == ("fight-rigging", None)
    assert result.selected_rule_id == "fight-rigging-primary"

    for off_color_source in ("Plains", "Island", "Swamp", "Mountain"):
        splashed = dict(core, **{off_color_source: 1})
        assert classify_counts(shadow, splashed, {}).status == "unknown"

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_hits: set[str] = set()
    for deck in event["decklists"]:
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        result = classify_counts(shadow, dict(main), dict(side))
        if result.archetype_id == "mono-green-trudge":
            tabletop_hits.add(deck["participant_id"])
    assert len(event["decklists"]) == 362
    assert tabletop_hits == set()


def test_grixis_tempo_boundaries_splash_labels_and_tabletop_regression() -> None:
    shadow = _load_shadow_rules()
    core = {
        "Fatal Push": 3,
        "Psychic Frog": 3,
        "Ragavan, Nimble Pilferer": 3,
        "Watery Grave": 1,
        "Steam Vents": 1,
    }
    result = classify_counts(shadow, core, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "grixis-tempo",
        None,
    )
    assert result.selected_rule_id == "grixis-tempo-ragavan"
    assert result.selected_priority == 638100
    assert len(result.matched_rules) == 1
    for card, threshold in core.items():
        below_threshold = dict(core, **{card: threshold - 1})
        result = classify_counts(shadow, below_threshold, {})
        assert result.selected_rule_id != "grixis-tempo-ragavan", card
        if card != "Steam Vents":
            assert result.status == "unknown", card
    assert classify_counts(shadow, {}, core).status == "unknown"

    for counterspell_count in (0, 4):
        build = dict(core, **{"Counterspell": counterspell_count})
        result = classify_counts(shadow, build, {})
        assert result.selected_rule_id == "grixis-tempo-ragavan"
        assert len(result.matched_rules) == 1

    reviewed_packages = (
        {
            "Dragon's Rage Channeler": 4,
            "Unholy Heat": 3,
            "Expressive Iteration": 4,
        },
        {
            "Quantum Riddler": 4,
            "Force of Negation": 3,
            "Subtlety": 3,
        },
    )
    for package in reviewed_packages:
        result = classify_counts(shadow, dict(core, **package), {})
        assert result.selected_rule_id == "grixis-tempo-ragavan"
        assert len(result.matched_rules) == 1

    for card in (
        "Goryo's Vengeance",
        "Persist",
        "Death's Shadow",
        "Plains",
        "Forest",
    ):
        excluded = dict(core, **{card: 1})
        assert classify_counts(shadow, excluded, {}).status == "unknown", card

    red_splash = {
        "Fatal Push": 3,
        "Counterspell": 3,
        "Watery Grave": 1,
        "Steam Vents": 1,
        "Ragavan, Nimble Pilferer": 2,
    }
    result = classify_counts(shadow, red_splash, {})
    assert (result.archetype_id, result.subtype_id, result.subtype_name) == (
        "dimir-tempo",
        "grixis",
        "Dimir Red Splash",
    )
    assert result.selected_rule_id == "dimir-tempo-grixis"
    assert len(result.matched_rules) == 1

    white_splash = {
        "Fatal Push": 3,
        "Counterspell": 3,
        "Watery Grave": 1,
        "Hallowed Fountain": 1,
    }
    result = classify_counts(shadow, white_splash, {})
    assert (result.archetype_id, result.subtype_id, result.subtype_name) == (
        "dimir-tempo",
        "esper",
        "Dimir White Splash",
    )
    assert result.selected_rule_id == "dimir-tempo-esper"

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_hits: set[str] = set()
    for deck in event["decklists"]:
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        result = classify_counts(shadow, dict(main), dict(side))
        if result.archetype_id == "grixis-tempo":
            tabletop_hits.add(deck["participant_id"])
    assert len(event["decklists"]) == 362
    assert tabletop_hits == set()


def test_orzhov_soultrader_boundaries_precedence_and_tabletop_regression() -> None:
    shadow = _load_shadow_rules()
    core = {
        "Warren Soultrader": 3,
        "Gravecrawler": 3,
        "Marionette Apprentice": 3,
        "Godless Shrine": 1,
    }
    result = classify_counts(shadow, core, {})
    assert (
        result.status,
        result.archetype_id,
        result.subtype_id,
        result.subtype_name,
    ) == ("classified", "soultrader", "orzhov", "Orzhov")
    assert result.selected_rule_id == "soultrader-orzhov"
    assert result.selected_priority == 687100
    assert len(result.matched_rules) == 1
    for card, threshold in core.items():
        below_threshold = dict(core, **{card: threshold - 1})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown", card
    assert classify_counts(shadow, {}, core).status == "unknown"

    construction_cards = dict(
        core,
        **{
            "Guide of Souls": 4,
            "Ocelot Pride": 4,
            "Knight-Errant of Eos": 4,
            "Chthonian Nightmare": 3,
            "Orcish Bowmasters": 4,
            "Sephiroth, Fabled SOLDIER": 2,
            "Overlord of the Balemurk": 1,
        },
    )
    result = classify_counts(shadow, construction_cards, {})
    assert result.selected_rule_id == "soultrader-orzhov"
    assert len(result.matched_rules) == 1

    energy_hybrid = dict(construction_cards, **{"Ajani, Nacatl Pariah": 3})
    result = classify_counts(shadow, energy_hybrid, {})
    assert (result.archetype_id, result.subtype_id) == ("soultrader", "orzhov")
    assert result.selected_rule_id == "soultrader-orzhov"
    assert result.selected_priority > 687000
    assert {item.rule_id for item in result.matched_rules} == {
        "soultrader-orzhov",
        "mardu-energy-primary",
    }

    for off_color_source in ("Island", "Forest", "Mountain"):
        splashed = dict(core, **{off_color_source: 1})
        assert classify_counts(shadow, splashed, {}).status == "unknown"
    for off_color_spell in ("Preordain", "Pick Your Poison", "Galvanic Discharge"):
        assert classify_counts(shadow, core, {off_color_spell: 1}).status == "unknown"

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_hits: set[str] = set()
    for deck in event["decklists"]:
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        result = classify_counts(shadow, dict(main), dict(side))
        if (result.archetype_id, result.subtype_id) == ("soultrader", "orzhov"):
            tabletop_hits.add(deck["participant_id"])
    assert len(event["decklists"]) == 362
    assert tabletop_hits == set()


def test_grixis_dress_down_boundaries_precedence_and_tabletop_regression() -> None:
    shadow = _load_shadow_rules()
    core = {
        "Dress Down": 3,
        "Nulldrifter": 3,
        "Kroxa, Titan of Death's Hunger": 3,
        "Steam Vents": 1,
        "Watery Grave": 1,
    }
    result = classify_counts(shadow, core, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "grixis-dress-down",
        None,
    )
    assert result.selected_rule_id == "grixis-dress-down-primary"
    assert result.selected_priority == 638050
    assert len(result.matched_rules) == 1
    for card, threshold in core.items():
        below_threshold = dict(core, **{card: threshold - 1})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown", card
    assert classify_counts(shadow, {}, core).status == "unknown"

    construction_cards = dict(
        core,
        **{
            "Fatal Push": 4,
            "Consign to Memory": 4,
            "Traumatic Critique": 3,
            "Force of Negation": 3,
            "Consult the Star Charts": 3,
        },
    )
    result = classify_counts(shadow, construction_cards, {})
    assert result.selected_rule_id == "grixis-dress-down-primary"
    assert len(result.matched_rules) == 1

    dimir_splash_hybrid = dict(core, **{"Fatal Push": 3, "Counterspell": 3})
    result = classify_counts(shadow, dimir_splash_hybrid, {})
    assert result.selected_rule_id == "grixis-dress-down-primary"
    assert {item.rule_id for item in result.matched_rules} == {
        "grixis-dress-down-primary",
        "dimir-tempo-grixis",
    }

    tempo_hybrid = dict(
        core,
        **{
            "Fatal Push": 3,
            "Psychic Frog": 3,
            "Ragavan, Nimble Pilferer": 3,
        },
    )
    result = classify_counts(shadow, tempo_hybrid, {})
    assert result.selected_rule_id == "grixis-tempo-ragavan"
    assert {item.rule_id for item in result.matched_rules} == {
        "grixis-tempo-ragavan",
        "grixis-dress-down-primary",
    }

    for excluded_card in ("Goryo's Vengeance", "Persist", "Death's Shadow"):
        excluded = dict(core, **{excluded_card: 1})
        assert classify_counts(shadow, excluded, {}).status == "unknown"
    for off_color_source in ("Hallowed Fountain", "Breeding Pool"):
        splashed = dict(core, **{off_color_source: 1})
        assert classify_counts(shadow, splashed, {}).status == "unknown"
    for off_color_spell in ("Prismatic Ending", "Pick Your Poison"):
        assert classify_counts(shadow, core, {off_color_spell: 1}).status == "unknown"

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_hits: set[str] = set()
    for deck in event["decklists"]:
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        result = classify_counts(shadow, dict(main), dict(side))
        if result.archetype_id == "grixis-dress-down":
            tabletop_hits.add(deck["participant_id"])
    assert len(event["decklists"]) == 362
    assert tabletop_hits == set()


def test_grixis_goryos_emperor_boundaries_and_tabletop_regression() -> None:
    shadow = _load_shadow_rules()
    core = {
        "Goryo's Vengeance": 1,
        "Emperor of Bones": 3,
        "Atraxa, Grand Unifier": 3,
        "Faithless Looting": 3,
        "Psychic Frog": 3,
    }
    result = classify_counts(shadow, core, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "grixis-goryos",
        None,
    )
    assert result.selected_rule_id == "grixis-goryos-emperor"
    assert result.selected_priority == 641090
    assert len(result.matched_rules) == 1

    two_goryos = dict(core, **{"Goryo's Vengeance": 2})
    result = classify_counts(shadow, two_goryos, {})
    assert result.selected_rule_id == "grixis-goryos-emperor"
    assert len(result.matched_rules) == 1
    zero_goryos = dict(core, **{"Goryo's Vengeance": 0})
    assert classify_counts(shadow, zero_goryos, {}).status == "unknown"

    original_primary = {
        "Goryo's Vengeance": 3,
        "Faithless Looting": 3,
        "Psychic Frog": 3,
    }
    result = classify_counts(shadow, original_primary, {})
    assert result.selected_rule_id == "grixis-goryos-primary"
    assert result.selected_priority == 641100
    assert len(result.matched_rules) == 1

    for card in (
        "Emperor of Bones",
        "Atraxa, Grand Unifier",
        "Faithless Looting",
        "Psychic Frog",
    ):
        below_threshold = dict(core, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown", card
    assert classify_counts(shadow, {}, core).status == "unknown"

    construction_cards = dict(
        core,
        **{
            "Griselbrand": 1,
            "Sin, Spira's Punishment": 2,
            "Thoughtseize": 4,
            "Force of Negation": 3,
            "Consign to Memory": 3,
            "Tainted Indulgence": 2,
            "Bitter Triumph": 1,
        },
    )
    result = classify_counts(shadow, construction_cards, {})
    assert result.selected_rule_id == "grixis-goryos-emperor"
    assert len(result.matched_rules) == 1

    for excluded_card in ("Ephemerate", "Persist"):
        excluded = dict(core, **{excluded_card: 1})
        assert classify_counts(shadow, excluded, {}).status == "unknown"

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_hits: set[str] = set()
    for deck in event["decklists"]:
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        result = classify_counts(shadow, dict(main), dict(side))
        if result.selected_rule_id == "grixis-goryos-emperor":
            tabletop_hits.add(deck["participant_id"])
    assert len(event["decklists"]) == 362
    assert tabletop_hits == set()


def test_through_the_breach_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    common = {
        "Through the Breach": 3,
        "Emrakul, the Aeons Torn": 3,
        "Ugin's Labyrinth": 3,
        "Eldrazi Temple": 3,
        "Devourer of Destiny": 3,
    }
    izzet = dict(
        common,
        **{
            "Kozilek's Command": 3,
            "Talisman of Creativity": 3,
        },
    )
    result = classify_counts(shadow, izzet, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "izzet-through-the-breach",
        None,
    )
    for card in izzet:
        below_threshold = dict(izzet, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"

    rakdos = dict(
        common,
        **{
            "Goryo's Vengeance": 3,
            "Faithless Looting": 3,
            "Talisman of Indulgence": 3,
        },
    )
    result = classify_counts(shadow, rakdos, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "rakdos-through-the-breach",
        None,
    )
    for card in rakdos:
        below_threshold = dict(rakdos, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"

    mixed_shell = dict(
        common,
        **{
            "Kozilek's Command": 3,
            "Talisman of Indulgence": 3,
        },
    )
    assert classify_counts(shadow, mixed_shell, {}).status == "unknown"


def test_cosmogoyf_necrodominance_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {"Necrodominance": 3, "Cosmogoyf": 3}
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "necrodominance",
        "cosmogoyf",
    )

    for card in base:
        below_threshold = dict(base, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    for excluded in ("Thud", "Fling"):
        with_fling_card = dict(base, **{excluded: 1})
        assert classify_counts(shadow, with_fling_card, {}).status == "unknown"

    thud_combo = dict(
        base,
        **{
            "Necrodominance": 2,
            "Thud": 3,
            "Plunge into Darkness": 3,
        },
    )
    result = classify_counts(shadow, thud_combo, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "fling-goyf",
        None,
    )


def test_badgermole_and_devoted_druid_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    devoted_core = {
        "Devoted Druid": 3,
        "Vizier of Remedies": 1,
        "Nature's Rhythm": 3,
        "Temple Garden": 1,
    }
    result = classify_counts(
        shadow,
        dict(devoted_core, **{"Overgrown Tomb": 1}),
        {},
    )
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "devoted-druid-combo",
        "abzan",
    )

    blue_splash = dict(
        devoted_core,
        **{"Overgrown Tomb": 1, "Breeding Pool": 1},
    )
    result = classify_counts(shadow, blue_splash, {"Consign to Memory": 2})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "devoted-druid-combo",
        "abzan",
    )

    result = classify_counts(shadow, devoted_core, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "devoted-druid-combo",
        "selesnya",
    )

    badgermole_core = {
        "Badgermole Cub": 3,
        "Leyline of Abundance": 3,
        "Green Sun's Zenith": 3,
        "Quirion Ranger": 3,
    }
    result = classify_counts(
        shadow,
        dict(badgermole_core, **{"Overgrown Tomb": 1}),
        {},
    )
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "badgermole-combo",
        "golgari",
    )

    druid_quillspike = dict(
        badgermole_core,
        **{"Forest": 7, "Devoted Druid": 4, "Quillspike": 1},
    )
    result = classify_counts(shadow, druid_quillspike, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "badgermole-combo",
        "mono-green",
    )

    with_vizier = dict(druid_quillspike, **{"Vizier of Remedies": 1})
    assert classify_counts(shadow, with_vizier, {}).status == "unknown"
    druid_alone = {"Devoted Druid": 4, "Quillspike": 1, "Forest": 7}
    assert classify_counts(shadow, druid_alone, {}).status == "unknown"

    landfall_core = {
        "Badgermole Cub": 3,
        "Green Sun's Zenith": 3,
        "Quirion Ranger": 2,
        "Springheart Nantuko": 3,
        "Ashaya, Soul of the Wild": 1,
        "Icetill Explorer": 3,
    }
    result = classify_counts(shadow, landfall_core, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "badgermole-combo",
        "landfall",
    )
    assert result.selected_rule_id == "badgermole-combo-landfall"
    for card, threshold in landfall_core.items():
        below_threshold = dict(landfall_core, **{card: threshold - 1})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    for excluded in ("Leyline of Abundance", "Vizier of Remedies"):
        with_excluded = dict(landfall_core, **{excluded: 1})
        assert classify_counts(shadow, with_excluded, {}).status == "unknown"


def test_dark_maestro_and_coffers_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    maestro = {
        "Cabal Coffers": 3,
        "Dark Petition": 3,
        "Profane Tutor": 3,
        "Molten-Core Maestro": 2,
    }
    result = classify_counts(shadow, maestro, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "dark-maestro",
        None,
    )
    for card, threshold in maestro.items():
        below_threshold = dict(maestro, **{card: threshold - 1})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    necro_maestro = dict(maestro, **{"Necrodominance": 3, "Blood Crypt": 1})
    result = classify_counts(shadow, necro_maestro, {})
    assert (result.archetype_id, result.subtype_id) == ("necrodominance", "rakdos")

    dimir = {
        "Cabal Coffers": 3,
        "Watery Grave": 3,
        "Consult the Star Charts": 3,
    }
    result = classify_counts(shadow, dimir, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "coffers",
        "dimir",
    )
    for card in dimir:
        below_threshold = dict(dimir, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    necro_dimir = dict(dimir, **{"Necrodominance": 3})
    result = classify_counts(shadow, necro_dimir, {})
    assert (result.archetype_id, result.subtype_id) == ("necrodominance", "dimir")

    golgari = {
        "Cabal Coffers": 3,
        "Karn, the Great Creator": 3,
        "Underground Mortuary": 2,
    }
    result = classify_counts(shadow, golgari, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "coffers",
        "golgari",
    )
    for card, threshold in golgari.items():
        below_threshold = dict(golgari, **{card: threshold - 1})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    necro_golgari = dict(
        golgari,
        **{"Necrodominance": 3, "Overgrown Tomb": 1},
    )
    result = classify_counts(shadow, necro_golgari, {})
    assert (result.archetype_id, result.subtype_id) == (
        "necrodominance",
        "golgari",
    )

    umori = {
        "Cabal Coffers": 3,
        "Dark Petition": 3,
        "Profane Tutor": 3,
        "Sylvan Scrying": 3,
        "Bloodchief's Thirst": 3,
    }
    result = classify_counts(shadow, umori, {"Umori, the Collector": 1})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "coffers",
        "umori",
    )
    for card in umori:
        below_threshold = dict(umori, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    assert (
        classify_counts(shadow, dict(umori, **{"Molten-Core Maestro": 1}), {}).status
        == "unknown"
    )

    historical_mono_black = {
        "Cabal Coffers": 3,
        "Karn, the Great Creator": 3,
        "Swamp": 10,
    }
    assert classify_counts(shadow, historical_mono_black, {}).status == "unknown"


def test_gruul_broodscale_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    gruul = {
        "Basking Broodscale": 3,
        "Blade of the Bloodchief": 2,
        "Stomping Ground": 1,
    }
    result = classify_counts(shadow, gruul, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "broodscale-combo",
        "gruul",
    )
    one_blade = dict(gruul, **{"Blade of the Bloodchief": 1})
    assert classify_counts(shadow, one_blade, {}).status == "unknown"
    mono_green = {
        "Basking Broodscale": 3,
        "Blade of the Bloodchief": 2,
        "Forest": 2,
    }
    result = classify_counts(shadow, mono_green, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "broodscale-combo",
        "mono-green",
    )


def test_eight_rack_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {
        "The Rack": 3,
        "Raven's Crime": 2,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "eight-rack",
        None,
    )
    assert (
        classify_counts(shadow, dict(base, **{"The Rack": 2}), {}).status == "unknown"
    )
    assert (
        classify_counts(shadow, dict(base, **{"Raven's Crime": 1}), {}).status
        == "unknown"
    )
    assert classify_counts(shadow, {}, base).status == "unknown"


def test_leyline_fling_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Leyline of Resonance": 3,
        "Heartfire Hero": 3,
        "Callous Sell-Sword": 3,
        "Monastery Swiftspear": 3,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "leyline-fling",
        None,
    )
    for card in base:
        below_threshold = dict(base, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    assert classify_counts(shadow, {}, base).status == "unknown"


def test_orzhov_blink_splash_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Phelia, Exuberant Shepherd": 3,
        "Overlord of the Balemurk": 3,
        "Ephemerate": 2,
        "Emperor of Bones": 2,
        "Flickerwisp": 2,
        "Solitude": 3,
        "Thoughtseize": 3,
        "Sacred Foundry": 1,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "orzhov-blink",
        None,
    )
    assert result.selected_rule_id == "orzhov-blink-splash"

    strict_primary = dict(base)
    del strict_primary["Sacred Foundry"]
    result = classify_counts(shadow, strict_primary, {})
    assert (result.status, result.archetype_id, result.selected_rule_id) == (
        "classified",
        "orzhov-blink",
        "orzhov-blink-primary",
    )

    thresholds = {
        "Phelia, Exuberant Shepherd": 2,
        "Overlord of the Balemurk": 2,
        "Ephemerate": 1,
        "Emperor of Bones": 1,
        "Flickerwisp": 1,
        "Solitude": 2,
        "Thoughtseize": 2,
    }
    for card, count in thresholds.items():
        below_threshold = dict(base, **{card: count})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"

    for card in (
        "Psychic Frog",
        "Quantum Riddler",
        "Detective's Phoenix",
        "Phlage, Titan of Fire's Fury",
        "Goryo's Vengeance",
    ):
        excluded_engine = dict(base, **{card: 1})
        assert classify_counts(shadow, excluded_engine, {}).status == "unknown"


def test_eldrazi_aggro_primary_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    primary = {"Eldrazi Linebreaker": 3}
    result = classify_counts(shadow, primary, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "eldrazi-aggro",
        None,
    )
    assert result.selected_rule_id == "eldrazi-aggro-primary"
    assert classify_counts(shadow, {"Eldrazi Linebreaker": 2}, {}).status == "unknown"
    assert classify_counts(shadow, {}, primary).status == "unknown"

    with_old_support = dict(primary, **{"It That Heralds the End": 3})
    result = classify_counts(shadow, with_old_support, {})
    assert (result.status, result.archetype_id, result.selected_rule_id) == (
        "classified",
        "eldrazi-aggro",
        "eldrazi-aggro-primary",
    )

    broodscale = {
        "Eldrazi Linebreaker": 4,
        "Basking Broodscale": 4,
        "Blade of the Bloodchief": 4,
        "Stomping Ground": 1,
    }
    result = classify_counts(shadow, broodscale, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "broodscale-combo",
        "gruul",
    )


def test_eldrazi_ouroboroid_synthetic_boundaries_and_precedence() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Ouroboroid": 3,
        "Badgermole Cub": 3,
        "Eldrazi Temple": 3,
        "Sowing Mycospawn": 3,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "eldrazi-ouroboroid",
        None,
    )
    assert result.selected_rule_id == "eldrazi-ouroboroid-primary"

    for card in base:
        below_threshold = dict(base, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown", card
    assert classify_counts(shadow, {}, base).status == "unknown"

    eldrazi_aggro = dict(base, **{"Eldrazi Linebreaker": 3})
    result = classify_counts(shadow, eldrazi_aggro, {})
    assert (result.status, result.archetype_id) == ("classified", "eldrazi-aggro")

    eldrazi_ramp = dict(base, **{"Ugin's Labyrinth": 3})
    result = classify_counts(shadow, eldrazi_ramp, {})
    assert (result.status, result.archetype_id) == ("classified", "eldrazi-ramp")

    badgermole_combo = dict(
        base,
        **{
            "Leyline of Abundance": 3,
            "Green Sun's Zenith": 3,
            "Quirion Ranger": 3,
        },
    )
    result = classify_counts(shadow, badgermole_combo, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "badgermole-combo",
        "mono-green",
    )

    broodscale_combo = dict(
        base,
        **{
            "Basking Broodscale": 3,
            "Blade of the Bloodchief": 2,
            "Forest": 2,
        },
    )
    result = classify_counts(shadow, broodscale_combo, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "broodscale-combo",
        "mono-green",
    )


def test_mono_green_stompy_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Aspect of Hydra": 3,
        "Old-Growth Troll": 3,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "mono-green-stompy",
        None,
    )
    assert result.selected_rule_id == "mono-green-stompy-primary"
    for card in base:
        below_threshold = dict(base, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    assert classify_counts(shadow, {}, base).status == "unknown"


def test_dredge_primary_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Arclight Phoenix": 3,
        "Creeping Chill": 3,
        "Life from the Loam": 3,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "dredge",
        None,
    )
    assert result.selected_rule_id == "dredge-primary"
    for card in base:
        below_threshold = dict(base, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    assert classify_counts(shadow, {}, base).status == "unknown"

    with_inquiry = dict(base, **{"Burning Inquiry": 3})
    result = classify_counts(shadow, with_inquiry, {})
    assert (result.status, result.archetype_id, result.selected_rule_id) == (
        "classified",
        "dredge",
        "dredge-primary",
    )


def test_hardened_scales_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {"Hardened Scales": 3}
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "hardened-scales",
        None,
    )
    assert result.selected_rule_id == "hardened-scales-primary"
    assert classify_counts(shadow, {"Hardened Scales": 2}, {}).status == "unknown"
    assert classify_counts(shadow, {}, base).status == "unknown"


def test_izzet_wizards_repair_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Snapcaster Mage": 2,
        "Flame of Anor": 3,
    }
    for bolt_count in (0, 1, 4):
        main = dict(base, **{"Lightning Bolt": bolt_count})
        result = classify_counts(shadow, main, {})
        assert (result.status, result.archetype_id, result.subtype_id) == (
            "classified",
            "izzet-wizards",
            None,
        )
        assert result.selected_rule_id == "izzet-wizards-primary"

    assert (
        classify_counts(shadow, {"Snapcaster Mage": 1, "Flame of Anor": 3}, {}).status
        == "unknown"
    )
    assert (
        classify_counts(shadow, {"Snapcaster Mage": 2, "Flame of Anor": 2}, {}).status
        == "unknown"
    )
    assert classify_counts(shadow, {}, base).status == "unknown"

    for card in IZZET_WIZARDS_REVIEWED_WHITE_SPELLS:
        main_result = classify_counts(shadow, dict(base, **{card: 1}), {})
        side_result = classify_counts(shadow, base, {card: 1})
        assert main_result.archetype_id != "izzet-wizards", card
        assert side_result.archetype_id != "izzet-wizards", card

    for neutral_card in (
        "Hallowed Fountain",
        "Sacred Foundry",
        "Apostle's Blessing",
    ):
        for main, side in (
            (dict(base, **{neutral_card: 1}), {}),
            (base, {neutral_card: 1}),
        ):
            result = classify_counts(shadow, main, side)
            assert (result.status, result.archetype_id) == (
                "classified",
                "izzet-wizards",
            )

    jeskai_base = dict(
        base,
        **{
            "Galvanic Discharge": 3,
            "Counterspell": 3,
            "Hallowed Fountain": 1,
            "Steam Vents": 1,
        },
    )
    for card in IZZET_WIZARDS_REVIEWED_WHITE_SPELLS:
        result = classify_counts(shadow, jeskai_base, {card: 1})
        assert (result.status, result.archetype_id, result.subtype_id) == (
            "classified",
            "jeskai-control",
            None,
        ), card


def test_jeskai_blink_repaired_primary_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Phelia, Exuberant Shepherd": 2,
        "Quantum Riddler": 3,
        "Solitude": 3,
        "Steam Vents": 1,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "jeskai-blink",
        None,
    )
    assert result.selected_rule_id == "jeskai-blink-primary"

    for card, threshold in base.items():
        below_threshold = dict(base, **{card: threshold - 1})
        assert classify_counts(shadow, below_threshold, {}).archetype_id != (
            "jeskai-blink"
        )
    for excluded in (
        "Watery Grave",
        "Temple Garden",
        "Goryo's Vengeance",
    ):
        with_excluded = dict(base, **{excluded: 1})
        assert classify_counts(shadow, with_excluded, {}).archetype_id != (
            "jeskai-blink"
        )

    stoneforge = dict(
        base,
        **{
            "Phelia, Exuberant Shepherd": 3,
            "Stoneforge Mystic": 3,
            "Kaldra Compleat": 1,
        },
    )
    result = classify_counts(shadow, stoneforge, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "jeskai-stoneforge",
        None,
    )


def test_jeskai_energy_repaired_primary_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Ajani, Nacatl Pariah": 3,
        "Guide of Souls": 3,
        "Ocelot Pride": 3,
        "Quantum Riddler": 1,
        "Mountain": 1,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "jeskai-energy",
        None,
    )
    assert result.selected_rule_id == "jeskai-energy-primary"
    assert result.selected_priority == 686000
    assert len(result.matched_rules) == 1

    for card in (
        "Ajani, Nacatl Pariah",
        "Guide of Souls",
        "Ocelot Pride",
    ):
        below_threshold = dict(base, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"

    without_red_source = dict(base)
    del without_red_source["Mountain"]
    assert classify_counts(shadow, without_red_source, {}).status == "unknown"
    assert classify_counts(shadow, {}, base).status == "unknown"

    two_riddlers = dict(base, **{"Quantum Riddler": 2})
    assert classify_counts(shadow, two_riddlers, {}).archetype_id == "jeskai-energy"

    no_discharge = dict(
        base,
        **{
            "Ragavan, Nimble Pilferer": 3,
            "Goblin Bombardment": 3,
            "Fable of the Mirror-Breaker": 2,
        },
    )
    assert classify_counts(shadow, no_discharge, {}).archetype_id == "jeskai-energy"

    boros = dict(base)
    del boros["Quantum Riddler"]
    result = classify_counts(shadow, boros, {"Quantum Riddler": 1})
    assert result.archetype_id == "boros-energy"
    assert result.selected_rule_id == "boros-energy-primary"

    azorius = dict(
        without_red_source,
        **{"Quantum Riddler": 4, "Hallowed Fountain": 1},
    )
    result = classify_counts(shadow, azorius, {})
    assert result.archetype_id == "azorius-energy"
    assert result.selected_rule_id == "azorius-energy-primary"

    mardu_hybrid = dict(base, **{"Orcish Bowmasters": 2})
    result = classify_counts(shadow, mardu_hybrid, {})
    assert result.archetype_id == "mardu-energy"
    assert result.selected_rule_id == "mardu-energy-primary"


def test_mardu_vial_synthetic_boundaries_and_energy_precedence() -> None:
    shadow = _load_shadow_rules()
    core = {
        "Aether Vial": 3,
        "Imperial Recruiter": 3,
        "Chthonian Nightmare": 2,
        "Solitude": 3,
    }
    result = classify_counts(shadow, core, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "mardu-vial",
        None,
    )
    assert result.selected_rule_id == "mardu-vial-primary"
    assert result.selected_priority == 686250

    for card, threshold in core.items():
        below_threshold = dict(core, **{card: threshold - 1})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    assert classify_counts(shadow, {}, core).status == "unknown"

    construction_cards = dict(
        core,
        **{
            "Ajani, Nacatl Pariah": 4,
            "Guide of Souls": 4,
            "Galvanic Discharge": 2,
            "Emperor of Bones": 2,
            "Phyrexian Tower": 2,
            "Seasoned Pyromancer": 3,
        },
    )
    result = classify_counts(shadow, construction_cards, {})
    assert result.archetype_id == "mardu-vial"
    assert result.selected_rule_id == "mardu-vial-primary"

    energy_primary = dict(
        construction_cards,
        **{"Ocelot Pride": 4, "Orcish Bowmasters": 2},
    )
    result = classify_counts(shadow, energy_primary, {})
    assert result.archetype_id == "mardu-energy"
    assert result.selected_rule_id == "mardu-energy-primary"

    energy_nightmare = dict(
        construction_cards,
        **{"Ocelot Pride": 4, "Blood Crypt": 1, "Godless Shrine": 1},
    )
    result = classify_counts(shadow, energy_nightmare, {})
    assert result.archetype_id == "mardu-energy"
    assert result.selected_rule_id == "mardu-energy-nightmare"


def test_golgari_yawgmoth_young_wolf_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    young_wolf_path = {
        "Yawgmoth, Thran Physician": 3,
        "Young Wolf": 2,
    }
    result = classify_counts(shadow, young_wolf_path, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "golgari-yawgmoth",
        None,
    )
    assert result.selected_rule_id == "golgari-yawgmoth-young-wolf"

    assert (
        classify_counts(
            shadow,
            {"Yawgmoth, Thran Physician": 3, "Young Wolf": 1},
            {},
        ).status
        == "unknown"
    )
    assert (
        classify_counts(
            shadow,
            {"Yawgmoth, Thran Physician": 2, "Young Wolf": 2},
            {},
        ).status
        == "unknown"
    )
    assert (
        classify_counts(
            shadow,
            {"Yawgmoth, Thran Physician": 3},
            {"Young Wolf": 2},
        ).status
        == "unknown"
    )
    assert classify_counts(shadow, {}, young_wolf_path).status == "unknown"

    grist_path = {
        "Yawgmoth, Thran Physician": 3,
        "Grist, the Hunger Tide": 1,
    }
    result = classify_counts(shadow, grist_path, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "golgari-yawgmoth",
        None,
    )
    assert result.selected_rule_id == "golgari-yawgmoth-primary"

    both_paths = dict(grist_path, **{"Young Wolf": 2})
    result = classify_counts(shadow, both_paths, {})
    assert result.selected_rule_id == "golgari-yawgmoth-primary"


def test_esper_value_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    ketramose = {
        "Relic of Progenitus": 2,
        "Ketramose, the New Dawn": 2,
        "Psychic Frog": 3,
        "Solitude": 3,
        "Phelia, Exuberant Shepherd": 2,
    }
    result = classify_counts(shadow, ketramose, {})
    assert (result.status, result.archetype_id) == ("classified", "esper-ketramose")

    traditional_blink = dict(
        ketramose,
        **{
            "Phelia, Exuberant Shepherd": 3,
            "Quantum Riddler": 3,
        },
    )
    result = classify_counts(shadow, traditional_blink, {})
    assert (result.status, result.archetype_id) == ("classified", "esper-blink")

    low_ketramose = dict(ketramose, **{"Ketramose, the New Dawn": 1})
    assert classify_counts(shadow, low_ketramose, {}).status == "unknown"

    blink = {
        "Ephemerate": 2,
        "Quantum Riddler": 3,
        "Solitude": 3,
        "Psychic Frog": 3,
    }
    result = classify_counts(shadow, blink, {})
    assert (result.status, result.archetype_id) == ("classified", "esper-blink")
    control = dict(blink, **{"Wrath of the Skies": 3})
    assert classify_counts(shadow, control, {}).status == "unknown"


def test_scapeshift_and_gruul_valakut_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    common = {
        "Scapeshift": 2,
        "Valakut, the Molten Pinnacle": 3,
        "Dryad of the Ilysian Grove": 3,
        "Icetill Explorer": 3,
    }
    naya = dict(common, **{"Sacred Foundry": 1})
    result = classify_counts(shadow, naya, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "scapeshift",
        "naya",
    )

    four_color = dict(
        naya,
        **{
            "Bring to Light": 2,
            "Thundering Falls": 1,
        },
    )
    result = classify_counts(shadow, four_color, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "scapeshift",
        "four-color",
    )
    assert classify_counts(shadow, common, {}).status == "unknown"
    one_bring_to_light = dict(naya, **{"Bring to Light": 1, "Thundering Falls": 1})
    assert classify_counts(shadow, one_bring_to_light, {}).status == "unknown"

    gruul_valakut = {
        "Valakut, the Molten Pinnacle": 3,
        "Dryad of the Ilysian Grove": 3,
        "Icetill Explorer": 3,
        "Vibrance": 3,
        "Wrenn and Six": 3,
        "Stomping Ground": 1,
    }
    result = classify_counts(shadow, gruul_valakut, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "gruul-valakut",
        None,
    )
    with_white = dict(gruul_valakut, **{"Sacred Foundry": 1})
    assert classify_counts(shadow, with_white, {}).status == "unknown"
    with_scapeshift = dict(gruul_valakut, **{"Scapeshift": 2})
    assert classify_counts(shadow, with_scapeshift, {}).status == "unknown"
    low_wrenn = dict(gruul_valakut, **{"Wrenn and Six": 2})
    assert classify_counts(shadow, low_wrenn, {}).status == "unknown"


def test_gruul_midrange_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Karn, the Great Creator": 3,
        "Blood Moon": 3,
        "Utopia Sprawl": 3,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "gruul-midrange",
        None,
    )
    assert result.selected_rule_id == "gruul-midrange-primary"

    for card in base:
        below_threshold = dict(base, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"

    assert classify_counts(shadow, {}, base).status == "unknown"

    historical_build = dict(
        base,
        **{
            "Arbor Elf": 4,
            "Fable of the Mirror-Breaker": 4,
            "Wrenn and Six": 2,
        },
    )
    assert classify_counts(shadow, historical_build, {}).archetype_id == (
        "gruul-midrange"
    )

    current_build = dict(
        base,
        **{
            "Fanatic of Rhonas": 4,
            "Malevolent Rumble": 4,
            "Endurance": 4,
            "Vibrance": 3,
            "Pillage": 1,
        },
    )
    assert classify_counts(shadow, current_build, {}).archetype_id == ("gruul-midrange")


def test_mono_blue_namor_synthetic_boundaries_and_precedence() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Namor the Sub-Mariner": 3,
        "Archmage's Charm": 3,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "mono-blue-namor",
        None,
    )
    assert result.selected_rule_id == "mono-blue-namor-primary"
    assert len(result.matched_rules) == 1

    for card in base:
        below_threshold = dict(base, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"

    traditional_merfolk = dict(base, **{"Lord of Atlantis": 3})
    result = classify_counts(shadow, traditional_merfolk, {})
    assert (result.archetype_id, result.subtype_id) == ("mono-blue-merfolk", None)
    assert result.selected_rule_id == "mono-blue-merfolk-primary"

    belcher = dict(
        base,
        **{"Goblin Charbelcher": 3, "Tameshi, Reality Architect": 3},
    )
    result = classify_counts(shadow, belcher, {})
    assert (result.archetype_id, result.subtype_id) == ("mono-blue-belcher", None)
    assert result.selected_rule_id == "mono-blue-belcher-primary"

    for off_color_source in (
        "Hallowed Fountain",
        "Watery Grave",
        "Steam Vents",
        "Breeding Pool",
    ):
        with_splash = dict(base, **{off_color_source: 1})
        assert classify_counts(shadow, with_splash, {}).status == "unknown"
    assert classify_counts(shadow, base, {"Wear/Tear": 1}).status == "unknown"
    assert classify_counts(shadow, base, {"Apostle's Blessing": 1}).archetype_id == (
        "mono-blue-namor"
    )


def test_golgari_goryos_synthetic_boundaries_and_existing_goryos_precedence() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Goryo's Vengeance": 3,
        "Dina's Guidance": 3,
        "Formidable Speaker": 3,
        "Overgrown Tomb": 1,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "golgari-goryos",
        None,
    )
    assert result.selected_rule_id == "golgari-goryos-primary"
    assert len(result.matched_rules) == 1

    for card in ("Goryo's Vengeance", "Dina's Guidance", "Formidable Speaker"):
        below_threshold = dict(base, **{card: 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"

    no_color_source = {
        card: count for card, count in base.items() if card != "Overgrown Tomb"
    }
    assert classify_counts(shadow, no_color_source, {}).status == "unknown"
    assert classify_counts(shadow, no_color_source, {"Overgrown Tomb": 1}).status == (
        "unknown"
    )
    for off_color_source in ("Hallowed Fountain", "Watery Grave", "Blood Crypt"):
        with_splash = dict(base, **{off_color_source: 1})
        assert classify_counts(shadow, with_splash, {}).status == "unknown"

    flexible_package = dict(
        base,
        **{
            "Persist": 4,
            "Unmarked Grave": 4,
            "Shifting Woodland": 4,
            "Archon of Cruelty": 3,
            "Atraxa, Grand Unifier": 1,
        },
    )
    assert classify_counts(shadow, flexible_package, {}).archetype_id == (
        "golgari-goryos"
    )

    esper = {
        "Goryo's Vengeance": 3,
        "Atraxa, Grand Unifier": 3,
        "Psychic Frog": 3,
        "Ephemerate": 3,
        "Dina's Guidance": 1,
        "Formidable Speaker": 3,
        "Overgrown Tomb": 1,
    }
    result = classify_counts(shadow, esper, {})
    assert (result.archetype_id, result.subtype_id) == ("esper-goryos", None)
    assert result.selected_rule_id == "esper-goryos-primary"


def test_amulet_scapeshift_maps_to_amulet_not_scapeshift() -> None:
    shadow = _load_shadow_rules()
    amulet = {
        "Amulet of Vigor": 4,
        "Scapeshift": 3,
        "Cultivator Colossus": 3,
        "Primeval Titan": 2,
        "Urza's Saga": 3,
    }
    result = classify_counts(shadow, amulet, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "amulet-titan",
        None,
    )
    low_saga = dict(amulet, **{"Urza's Saga": 2})
    assert classify_counts(shadow, low_saga, {}).status == "unknown"


def test_izzet_storm_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Ral, Monsoon Mage": 3,
        "Stormcatch Mentor": 3,
        "Past in Flames": 2,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "izzet-storm",
        None,
    )
    assert result.selected_rule_id == "izzet-storm-primary"

    for card, quantity in base.items():
        mutation = dict(base)
        mutation[card] = quantity - 1
        assert classify_counts(shadow, mutation, {}).status == "unknown", card

    assert classify_counts(shadow, {}, base).status == "unknown"

    one_ruby = dict(base, **{"Ruby Medallion": 1})
    assert classify_counts(shadow, one_ruby, {}).status == "unknown"
    ruby_storm = dict(base, **{"Ruby Medallion": 3})
    result = classify_counts(shadow, ruby_storm, {})
    assert (result.status, result.archetype_id) == ("classified", "ruby-storm")


def test_izzet_twin_synthetic_boundaries_and_cross_product_regression() -> None:
    shadow = _load_shadow_rules()
    twin = next(item for item in shadow.archetypes if item.id == "izzet-twin")
    assert twin.name == "Izzet Twin"
    assert twin.subtypes == ()
    assert [item.id for item in twin.rules] == ["izzet-twin-primary"]

    base = {
        "Splinter Twin": 2,
        "Fear of Missing Out": 3,
        "Steam Vents": 1,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "izzet-twin",
        None,
    )
    assert result.selected_rule_id == "izzet-twin-primary"
    assert len(result.matched_rules) == 1

    for card, quantity in (("Splinter Twin", 1), ("Fear of Missing Out", 2)):
        below_threshold = dict(base, **{card: quantity})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
    assert classify_counts(shadow, {}, base).status == "unknown"

    construction_cards = dict(
        base,
        **{
            "Flow State": 4,
            "Mishra's Bauble": 4,
            "Tamiyo, Inquisitive Student": 4,
            "Expressive Iteration": 4,
            "Force of Negation": 3,
        },
    )
    assert (
        classify_counts(shadow, construction_cards, {}).selected_rule_id
        == "izzet-twin-primary"
    )

    for source in ("Plains", "Swamp", "Forest"):
        result = classify_counts(shadow, dict(base, **{source: 1}), {})
        assert result.selected_rule_id != "izzet-twin-primary"
    for spell in ("Path to Exile", "Thoughtseize", "Pick Your Poison"):
        result = classify_counts(shadow, base, {spell: 1})
        assert result.selected_rule_id != "izzet-twin-primary"

    for traditional_creature in ("Deceiver Exarch", "Pestermite"):
        traditional = {
            "Splinter Twin": 3,
            traditional_creature: 4,
            "Steam Vents": 1,
        }
        assert (
            classify_counts(shadow, traditional, {}).selected_rule_id
            != "izzet-twin-primary"
        )

    frozen_hits: list[str] = []
    for record in load_frozen_records(FROZEN_PATH):
        main = dict(record["main"])
        side = dict(record["side"])
        result = classify_counts(shadow, main, side)
        if result.archetype_id == "izzet-twin":
            frozen_hits.append(str(record["id"]))
    assert frozen_hits == ["modern-baseline-0807"]

    event = json.loads(
        (ROOT / "data" / "modern" / "melee" / "events" / "434455.json").read_text(
            encoding="utf-8"
        )
    )
    tabletop_hits: list[str] = []
    for deck in event["decklists"]:
        main: Counter[str] = Counter()
        side: Counter[str] = Counter()
        for card in deck["cards"]:
            target = main if card["section"] == "main" else side
            target[card["name"]] += card["quantity"]
        result = classify_counts(shadow, dict(main), dict(side))
        if result.archetype_id == "izzet-twin":
            tabletop_hits.append(deck["participant_id"])
    assert len(event["decklists"]) == 362
    assert tabletop_hits == []


def test_asmo_persist_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Persist": 3,
        "Archon of Cruelty": 3,
        "Faithless Looting": 3,
        "Asmoranomardicadaistinaculdacar": 3,
        "The Underworld Cookbook": 3,
        "Ovalchase Daredevil": 3,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "asmo-persist",
        None,
    )
    assert result.selected_rule_id == "asmo-persist-primary"

    for card in base:
        mutation = dict(base)
        mutation[card] = 2
        assert classify_counts(shadow, mutation, {}).status == "unknown", card

    assert classify_counts(shadow, {}, base).status == "unknown"

    traditional_hybrid = dict(
        base,
        **{
            "Bloodghast": 3,
            "Stitcher's Supplier": 3,
        },
    )
    result = classify_counts(shadow, traditional_hybrid, {})
    assert (result.status, result.archetype_id) == ("classified", "asmo-persist")

    grixis_hybrid = dict(base, **{"Abhorrent Oculus": 3})
    result = classify_counts(shadow, grixis_hybrid, {})
    assert (result.status, result.archetype_id) == ("classified", "grixis-persist")


def test_golgari_delirium_synthetic_boundaries_and_precedence() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Nethergoyf": 3,
        "Omnivorous Flytrap": 3,
        "Mishra's Bauble": 3,
        "Witherbloom Command": 2,
        "Swamp": 1,
        "Forest": 1,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "golgari-delirium",
        None,
    )
    assert result.selected_rule_id == "golgari-delirium-primary"

    thresholds = {
        "Nethergoyf": 2,
        "Omnivorous Flytrap": 2,
        "Mishra's Bauble": 2,
        "Witherbloom Command": 1,
    }
    for card, quantity in thresholds.items():
        mutation = dict(base, **{card: quantity})
        assert classify_counts(shadow, mutation, {}).status == "unknown", card
    assert classify_counts(shadow, {}, base).status == "unknown"

    without_black_source = dict(base, Swamp=0)
    assert classify_counts(shadow, without_black_source, {}).status == "unknown"
    without_green_source = dict(base, Forest=0)
    assert classify_counts(shadow, without_green_source, {}).status == "unknown"
    for off_color_source in ("Plains", "Island", "Mountain"):
        mutation = dict(base, **{off_color_source: 1})
        assert classify_counts(shadow, mutation, {}).status == "unknown"

    saga_build = dict(
        base,
        **{
            "Urza's Saga": 4,
            "Shadowspear": 1,
            "Nihil Spellbomb": 1,
            "Vexing Bauble": 1,
        },
    )
    result = classify_counts(shadow, saga_build, {})
    assert result.archetype_id == "golgari-delirium"

    moonshadow_build = dict(base, **{"Moonshadow": 4, "Street Wraith": 3})
    result = classify_counts(shadow, moonshadow_build, {})
    assert result.archetype_id == "golgari-delirium"

    rakdos_deaths_shadow = dict(
        moonshadow_build,
        **{
            "Death's Shadow": 3,
            "Thoughtseize": 3,
            "Blood Crypt": 1,
        },
    )
    result = classify_counts(shadow, rakdos_deaths_shadow, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "deaths-shadow",
        "rakdos",
    )


def test_bogles_synthetic_boundaries_and_construction_choices() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Slippery Bogle": 3,
        "Gladecover Scout": 3,
        "Ethereal Armor": 3,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "bogles",
        None,
    )
    assert result.selected_rule_id == "bogles-primary"

    for card in base:
        mutation = dict(base)
        mutation[card] = 2
        assert classify_counts(shadow, mutation, {}).status == "unknown", card
    assert classify_counts(shadow, {}, base).status == "unknown"

    traditional_build = dict(
        base,
        **{
            "Daybreak Coronet": 4,
            "Kor Spiritdancer": 4,
            "Rancor": 4,
            "Spider Umbra": 4,
        },
    )
    result = classify_counts(shadow, traditional_build, {})
    assert result.archetype_id == "bogles"

    light_paws_build = dict(
        base,
        **{
            "Light-Paws, Emperor's Voice": 4,
            "Sheltered by Ghosts": 4,
            "Hyena Umbra": 4,
        },
    )
    result = classify_counts(shadow, light_paws_build, {})
    assert result.archetype_id == "bogles"

    no_coronet_off_color_build = dict(base, **{"Hallowed Fountain": 1})
    result = classify_counts(shadow, no_coronet_off_color_build, {})
    assert result.archetype_id == "bogles"

    aura_shell_without_both_hexproof_creatures = {
        "Ethereal Armor": 4,
        "Daybreak Coronet": 4,
        "Kor Spiritdancer": 4,
    }
    assert (
        classify_counts(shadow, aura_shell_without_both_hexproof_creatures, {}).status
        == "unknown"
    )


def test_reclamation_parent_boundaries_and_precedence() -> None:
    shadow = _load_shadow_rules()
    temur = {
        "Wilderness Reclamation": 3,
        "Island": 1,
        "Mountain": 1,
        "Forest": 1,
    }
    result = classify_counts(shadow, temur, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "temur-reclamation",
        None,
    )
    assert result.selected_rule_id == "temur-reclamation-primary"

    bant = {
        "Wilderness Reclamation": 3,
        "Plains": 1,
        "Island": 1,
        "Forest": 1,
    }
    result = classify_counts(shadow, bant, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "bant-reclamation",
        None,
    )
    assert result.selected_rule_id == "bant-reclamation-primary"

    for base in (temur, bant):
        below_threshold = dict(base, **{"Wilderness Reclamation": 2})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown"
        assert classify_counts(shadow, {}, base).status == "unknown"

    for source in ("Island", "Mountain", "Forest"):
        missing_source = dict(temur, **{source: 0})
        assert classify_counts(shadow, missing_source, {}).status == "unknown"
    for source in ("Plains", "Island", "Forest"):
        missing_source = dict(bant, **{source: 0})
        assert classify_counts(shadow, missing_source, {}).status == "unknown"

    temur_growth_build = dict(
        temur,
        **{
            "Growth Spiral": 4,
            "Galvanic Discharge": 4,
            "Consult the Star Charts": 4,
            "Traumatic Critique": 3,
        },
    )
    assert classify_counts(shadow, temur_growth_build, {}).archetype_id == (
        "temur-reclamation"
    )

    temur_wizards_build = dict(
        temur,
        **{"Snapcaster Mage": 2, "Flame of Anor": 3},
    )
    assert classify_counts(shadow, temur_wizards_build, {}).archetype_id == (
        "temur-reclamation"
    )

    bant_chant_build = dict(
        bant,
        **{"Orim's Chant": 4, "Planar Genesis": 4},
    )
    assert classify_counts(shadow, bant_chant_build, {}).archetype_id == (
        "bant-reclamation"
    )

    assert classify_counts(shadow, temur, {"Path to Exile": 1}).status == "unknown"
    assert classify_counts(shadow, bant, {"Galvanic Discharge": 1}).status == "unknown"
    assert classify_counts(shadow, dict(temur, Plains=1), {}).status == "unknown"
    assert classify_counts(shadow, dict(bant, Mountain=1), {}).status == "unknown"

    unsupported_sultai = {
        "Wilderness Reclamation": 3,
        "Island": 1,
        "Swamp": 1,
        "Forest": 1,
    }
    assert classify_counts(shadow, unsupported_sultai, {}).status == "unknown"

    omnath_hybrid = dict(
        temur,
        **{
            "Plains": 1,
            "Omnath, Locus of Creation": 2,
            "Wrenn and Six": 2,
            "Teferi, Time Raveler": 2,
        },
    )
    assert classify_counts(shadow, omnath_hybrid, {}).archetype_id == (
        "omnath-midrange"
    )


def test_agadeem_persist_reduced_crypt_boundaries_and_precedence() -> None:
    shadow = _load_shadow_rules()
    reduced_crypt = {
        "Persist": 3,
        "Archon of Cruelty": 3,
        "Crypt of Agadeem": 1,
        "Eyetwitch": 3,
        "Stitcher's Supplier": 3,
        "Phyrexian Tower": 3,
    }
    result = classify_counts(shadow, reduced_crypt, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "agadeem-persist",
        None,
    )
    assert result.selected_rule_id == "agadeem-persist-reduced-crypt"
    assert result.selected_priority == 639400
    assert len(result.matched_rules) == 1

    for card, threshold in reduced_crypt.items():
        below_threshold = dict(reduced_crypt, **{card: threshold - 1})
        assert classify_counts(shadow, below_threshold, {}).status == "unknown", card
    assert classify_counts(shadow, {}, reduced_crypt).status == "unknown"

    two_crypts = dict(reduced_crypt, **{"Crypt of Agadeem": 2})
    result = classify_counts(shadow, two_crypts, {})
    assert result.selected_rule_id == "agadeem-persist-reduced-crypt"
    assert len(result.matched_rules) == 1

    primary = dict(reduced_crypt, **{"Crypt of Agadeem": 3})
    result = classify_counts(shadow, primary, {})
    assert result.selected_rule_id == "agadeem-persist-primary"
    assert result.selected_priority == 639800
    assert len(result.matched_rules) == 1

    construction_cards = dict(
        reduced_crypt,
        **{
            "Emperor of Bones": 4,
            "Overlord of the Balemurk": 4,
            "Street Wraith": 4,
            "Culling Ritual": 2,
        },
    )
    result = classify_counts(shadow, construction_cards, {})
    assert result.selected_rule_id == "agadeem-persist-reduced-crypt"

    existing_persist_precedence = {
        "grixis-persist": {
            "Faithless Looting": 3,
            "Abhorrent Oculus": 3,
        },
        "esper-persist": {"Faithful Mending": 2},
        "asmo-persist": {
            "Faithless Looting": 3,
            "Asmoranomardicadaistinaculdacar": 3,
            "The Underworld Cookbook": 3,
            "Ovalchase Daredevil": 3,
        },
        "rakdos-persist": {
            "Faithless Looting": 3,
            "Bloodghast": 3,
        },
        "sultai-persist": {
            "Psychic Frog": 3,
            "Malevolent Rumble": 3,
        },
    }
    for expected_identity, additions in existing_persist_precedence.items():
        hybrid = dict(reduced_crypt, **additions)
        result = classify_counts(shadow, hybrid, {})
        assert result.archetype_id == expected_identity


def test_sultai_persist_synthetic_boundaries_and_precedence() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Persist": 3,
        "Archon of Cruelty": 3,
        "Psychic Frog": 3,
        "Malevolent Rumble": 3,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "sultai-persist",
        None,
    )
    assert result.selected_rule_id == "sultai-persist-primary"

    for card in base:
        mutation = dict(base)
        mutation[card] = 2
        assert classify_counts(shadow, mutation, {}).status == "unknown", card
    assert classify_counts(shadow, {}, base).status == "unknown"

    existing_persist_precedence = {
        "grixis-persist": {
            "Faithless Looting": 3,
            "Abhorrent Oculus": 3,
        },
        "agadeem-persist": {"Crypt of Agadeem": 3},
        "esper-persist": {"Faithful Mending": 2},
        "rakdos-persist": {
            "Faithless Looting": 3,
            "Bloodghast": 3,
            "Stitcher's Supplier": 3,
        },
        "asmo-persist": {
            "Faithless Looting": 3,
            "Asmoranomardicadaistinaculdacar": 3,
            "The Underworld Cookbook": 3,
            "Ovalchase Daredevil": 3,
        },
    }
    for expected_identity, additions in existing_persist_precedence.items():
        hybrid = dict(base, **additions)
        result = classify_counts(shadow, hybrid, {})
        assert result.archetype_id == expected_identity


def test_rakdos_persist_synthetic_boundaries() -> None:
    shadow = _load_shadow_rules()
    base = {
        "Persist": 3,
        "Archon of Cruelty": 3,
        "Faithless Looting": 3,
        "Bloodghast": 3,
        "Stitcher's Supplier": 3,
    }
    result = classify_counts(shadow, base, {})
    assert (result.status, result.archetype_id) == ("classified", "rakdos-persist")

    for card in base:
        mutation = dict(base)
        mutation[card] = 2
        assert classify_counts(shadow, mutation, {}).status == "unknown"

    one_oculus = dict(base, **{"Abhorrent Oculus": 1})
    assert classify_counts(shadow, one_oculus, {}).status == "unknown"
    grixis = dict(base, **{"Abhorrent Oculus": 3})
    result = classify_counts(shadow, grixis, {})
    assert (result.status, result.archetype_id) == ("classified", "grixis-persist")

    incomplete_living_end = dict(base, **{"Living End": 3})
    assert classify_counts(shadow, incomplete_living_end, {}).status == "unknown"
    rakdos_living_end = dict(
        incomplete_living_end,
        **{"Electrodominance": 4},
    )
    result = classify_counts(shadow, rakdos_living_end, {})
    assert (result.status, result.archetype_id, result.subtype_id) == (
        "classified",
        "living-end",
        "rakdos",
    )
