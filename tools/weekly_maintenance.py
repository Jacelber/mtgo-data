"""Private weekly preparation; optional selected image fill, never event fetch or publication."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import sys
import subprocess
import threading
from time import perf_counter

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from mtgmeta.mtgo import landing_editorial as editorial
from mtgmeta.mtgo import landing
from mtgmeta.mtgo import landing_screening as screening, stats
from mtgmeta.mtgo.normalize import load_rules_for_format
from mtgmeta.mtgo import review_submission as submissions
from mtgmeta.mtgo.landing_bundle import digest
from mtgmeta.mtgo.publication import require_private_output


def read(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    value = yaml.safe_load(text) if path.suffix in {".yaml", ".yml"} else json.loads(text)
    if not isinstance(value, dict):
        raise ValueError(f"Expected object: {path}")
    return value


def write(path, value):
    """Replace, never mutate a possibly hard-linked base file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def scope(source):
    format_id = source["format"]
    week = source["week"] if isinstance(source["week"], str) else source["week"]["id"]
    submissions.applies(week)
    if not re.fullmatch(r"[a-z][a-z0-9-]*", format_id):
        raise ValueError("Invalid format")
    return format_id, week


def new_output(root, output):
    output = Path(output).resolve()
    require_private_output(root, output / "index.html")
    if output.exists():
        raise ValueError("Snapshot exists; use a new output directory")
    output.mkdir(parents=True)
    return output


def card_names(deck):
    return {card["name"] for key in ("main_deck", "side_deck") for card in deck.get(key, [])}


def normalize_selected_cards(source, lookup):
    result, changes = deepcopy(source), []
    from mtgmeta.mtgo.landing_tabletop import deck_catalog
    decks = {d["token"]: d for d in deck_catalog(source)}
    for item in result.get("review", {}).get("features", {}).get("items", []):
        deck = decks.get(item.get("destination_id"))
        if deck is None:
            continue
        names = card_names(deck)
        normalized = []
        for name in item.get("featured_cards", []):
            matches = [n for n in names if n == name or lookup.get(n, {}).get("zh_name") == name]
            if len(matches) > 1:
                raise ValueError(f"Ambiguous card name in selected deck: {name}")
            value = matches[0] if matches else name
            normalized.append(value)
            if value != name:
                changes.append({"feature": item["destination_id"], "input": name, "canonical": value})
        item["featured_cards"] = normalized
    return result, changes


def inventory(root, source, displayed=None, previous=None, facts=None):
    """Derive required inputs without manufacturing choices or acceptance."""
    format_id, week = scope(source)
    page = facts["page"] if facts else read(root / f"stats/{format_id}/mtgo/landing/current.json")
    if page["week"]["id"] != week:
        raise ValueError("Current environment belongs to another week; provide the fixed data candidate")
    if source.get("bindings", {}).get("classifier_digest") != page["classifier"]["digest"]:
        raise ValueError("Content/classifier binding differs from the data candidate")
    if facts and any(source.get("bindings", {}).get(key) != value for key, value in facts["bindings"].items()):
        raise ValueError("Content scope differs from the fixed facts; retain the matching source")
    decks = source.get("all_top8")
    if decks is None:
        raise ValueError("Retained all_top8 required; do not rediscover or reclassify it here")
    bound_decks = source.get("bindings", {}).get("link_catalog_digest")
    if bound_decks and editorial.document_digest(decks) != bound_decks:
        raise ValueError("Retained deck catalog changed without a new submission binding")
    from mtgmeta.mtgo import landing_tabletop as tabletop
    if source.get("tabletop"):
        if source["bindings"].get("tabletop_digest") != tabletop.digest(source["tabletop"]):
            raise ValueError("Retained tabletop catalog changed without its submission binding")
    mtgo_decks = decks
    decks = tabletop.deck_catalog(source)
    if facts and facts.get("digest") and facts["digest"] != digest({k: v for k, v in facts.items() if k != "digest"}):
        raise ValueError("Fixed content facts changed")
    records = {item["token"]: item for item in decks}
    old = previous or {}
    if old and (old.get("format"), old.get("week")) != (format_id, week):
        raise ValueError("Previous inventory belongs to another scope")
    identities = deepcopy(old.get("aliases", {}))
    next_id = max([int(key[1:]) for key in identities] or [0]) + 1
    aliases = {}
    candidate_facts = {item["token"]: item.get("reasons", []) for item in source.get("candidate_evidence", [])}
    for deck in decks:
        identity = digest({"deck": deck, "facts": candidate_facts.get(deck["token"], []),
                           "classifier": source["bindings"]["classifier_digest"]})
        alias = next((key for key, value in identities.items() if value["identity"] == identity), None)
        if alias is None:
            alias = f"F{next_id}"
            next_id += 1
            identities[alias] = {"identity": identity, "token": deck["token"]}
        aliases[deck["token"]] = alias
    required, machine, errors = [], [], []
    review = source.get("review", {})
    copy = review.get("top_copy", {}).get("items", [])
    if not copy or any(not str(item.get("text", {}).get("zh", "")).strip() for item in copy):
        required.append("Landing 中文正文")
    if copy and any(not str(item.get("text", {}).get("en", "")).strip() for item in copy):
        machine.append("Landing 英文草稿")
    selection = review.get("features", {})
    features = selection.get("items", [])
    explicit_empty = selection.get("explicit_empty") is True
    if not features and not explicit_empty:
        required.append("Feature 有无及选择")
    if features and explicit_empty:
        errors.append("Feature 选择与明确不选冲突")
    for item in features:
        token = item.get("destination_id")
        alias = aliases.get(token, str(token))
        deck = records.get(token)
        if deck is None:
            errors.append(f"{alias}: 不属于固定牌表范围")
            continue
        if item.get("category") not in {"new_deck", "new_technology"}:
            required.append(f"{alias}: 展示类别（新套牌／新科技）")
        cards = item.get("featured_cards", [])
        if len(cards) != 4 or len(set(cards)) != 4:
            required.append(f"{alias}: 四张不同展示牌及顺序")
        else:
            for index, name in enumerate(cards, 1):
                if name not in card_names(deck):
                    errors.append(f"{alias}: 第{index}张 {name} 不在该牌表主备牌中")
        if not str(item.get("positioning", {}).get("zh", "")).strip():
            required.append(f"{alias}: Feature 中文说明")
        if not str(item.get("positioning", {}).get("en", "")).strip():
            machine.append(f"{alias}: Feature 英文草稿")
    if displayed and displayed.get("format") != format_id:
        raise ValueError("Displayed page belongs to another format")
    old_rows = {row["archetype_id"]: row for row in (displayed or {}).get("environment", {}).get("rows", [])}
    names_path = root / f"stats/{format_id}/archetype_names.json"
    names = {item["identity_id"]: item["display"] for item in read(names_path).get("names", [])} if names_path.is_file() else {}
    environment = []
    for row in page["environment"]["rows"]:
        parent = row["archetype_id"]
        cards = [card["name"] for card in row.get("key_cards", [])]
        prior = old_rows.get(parent)
        same = prior is not None and cards == [card["name"] for card in prior.get("key_cards", [])]
        same = same and row.get("display_name") == prior.get("display_name")
        status = "displayed_configuration_reused" if same else "changed" if prior else "not_previously_displayed"
        if not same:
            required.append(f"环境栏 {parent}: {'首次展示' if not prior else '实际改变'}的代表牌／展示确认")
        underlying = facts.get("environment_decks", mtgo_decks) if facts else mtgo_decks
        environment.append({"archetype_id": parent, "status": status, "cards": cards,
                            "name": names.get(parent, {}).get("zh") or row.get("display_name") or parent,
                            "facts": row, "decks": [d for d in underlying if d["parent_id"] == parent]})
    return {"format": format_id, "week": week, "source_digest": digest(source),
            "displayed_page_digest": digest(displayed) if displayed else None,
            "aliases": identities, "active_aliases": aliases, "required_user": required,
            "machine_pending": machine, "errors": errors, "environment": environment,
            "all_top8": mtgo_decks, "tabletop_decks": source.get("tabletop", {}).get("decks", []),
            "tabletop_events": source.get("tabletop", {}).get("events", []),
            "new_types": [r["archetype_id"] for r in environment if r["status"] == "not_previously_displayed"],
            "candidate_evidence": source.get("candidate_evidence", []),
            "work": {"classified": 0, "fetched": 0, "generated_pages": 0,
                     "reuse_check": "fixed source scope and displayed environment rows only"}}


def render_inventory(value, lookup=None, names=None):
    from tools.weekly_maintenance_review import render_review
    return render_review(value, kind="content", lookup=lookup, names=names)


def render_classification(value, lookup=None, names=None):
    from tools.weekly_maintenance_review import render_review
    return render_review(value, kind="classification", lookup=lookup, names=names)


def link_or_copy(source, destination):
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)
    return str(destination)


def prepare(root, source, base, output, facts=None, *, visuals=None, fetch_missing=False, resource_fixture=None):
    """Compose only editorial outputs over a fixed site; no acceptance is invented."""
    format_id, week = scope(source)
    from mtgmeta.mtgo.landing_tabletop import validate_retained
    validate_retained(root, source)
    if not facts or "review_facts" not in facts or "admitted_scope" not in facts:
        raise ValueError("Fixed admitted facts with review_facts required; use the facts entry once")
    state = inventory(root, source, read(base / f"stats/{format_id}/mtgo/landing/current.json"), facts=facts)
    user_missing = [item for item in state["required_user"] if not item.startswith("环境栏 ")]
    if user_missing or state["errors"] or state["machine_pending"]:
        raise ValueError(json.dumps({"required_user": user_missing, "errors": state["errors"],
                                     "machine_pending": state["machine_pending"]}, ensure_ascii=False))
    source, facts = deepcopy(source), deepcopy(facts)
    visual_config = read(root / "configs/mtgo_landing_visuals.yaml")
    if visuals:
        rows = {row["archetype_id"]: row for row in facts["page"]["environment"]["rows"]}
        if set(visuals) - rows.keys():
            raise ValueError("Representative choices must belong to the current environment")
        for identity, cards in visuals.items():
            if not isinstance(cards, list) or len(cards) != 2 or len(set(cards)) != 2 or not all(isinstance(c, str) and c.strip() for c in cards):
                raise ValueError("Each representative choice needs two distinct canonical card names")
            rows[identity]["key_cards"] = [{"name": card} for card in cards]
            visual_config["formats"][format_id]["parents"][identity] = cards
        facts["review_facts"]["environment"] = deepcopy(facts["page"]["environment"])
        machine = landing._fact_digest({**facts["review_facts"], "classifier": facts["page"]["classifier"]})
        source["bindings"]["machine_fact_digest"] = machine
        facts["bindings"] = deepcopy(source["bindings"])
        facts["page"]["review_binding"]["machine_fact_digest"] = machine
        facts["digest"] = digest({k: v for k, v in facts.items() if k != "digest"})
    page_path = Path(f"stats/{format_id}/mtgo/landing/current.json")
    page = deepcopy(facts["page"]) if facts else read(base / page_path)
    if page["week"]["id"] != week or page["classifier"]["digest"] != source["bindings"]["classifier_digest"]:
        raise ValueError("Base page must be the fixed week/classifier data result")
    original_page = read(base / page_path)
    if facts and original_page["week"] == page["week"] and original_page.get("data_files"):
        page["data_files"] = deepcopy(original_page["data_files"])
    from mtgmeta.mtgo.landing_tabletop import deck_catalog
    decks = {item["token"]: item for item in deck_catalog(source)}
    material = editorial.materialize_review(source, editorial.load_name_catalog(root / editorial.DEFAULT_NAME_CATALOG),
                                           decks=decks)
    page["weekly_summary"]["items"] = material["weekly_summary"]
    public_features = [landing._public_feature(item) for item in material["features"]]
    page["features"]["items"] = public_features
    # Private prospective rendering only. An accepted source must still pass the
    # existing importer before production generation; never attach fabricated receipts.
    page["review_binding"]["pickup_document_digest"] = digest(source)
    landing.validate_document(page)
    site = output / "site"
    if site.is_relative_to(base):
        raise ValueError("Output site cannot be inside its base")
    config = read(root / "configs/pages_publication.json")
    from fnmatch import fnmatchcase
    reused_files = 0
    for relative in [*config["site_files"], *config["site_directories"]]:
        src = base / relative
        if not src.exists():
            continue
        sources = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
        for path in sources:
            rel = path.relative_to(base)
            if path.is_symlink() or any(fnmatchcase(rel.as_posix(), pattern) for pattern in config["excluded_patterns"]):
                continue
            dest = site / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            link_or_copy(path, dest)
            reused_files += 1
    archive_path = Path(f"stats/{format_id}/mtgo/landing/features/{week}.json")
    archive = (read(base / archive_path) if (base / archive_path).is_file() else {
        "schema_version": landing.FEATURE_ARCHIVE_SCHEMA_VERSION, "product": landing.FEATURE_ARCHIVE_PRODUCT_ID,
        "format": format_id, "source": "mtgo", "week": source["week"],
        "source_event_ids": source["bindings"]["source_event_ids"],
        "classifier_digest": source["bindings"]["classifier_digest"], "features": {}})
    archive["features"]["items"] = public_features
    archive["content_digest"] = editorial.document_digest(public_features)
    index_path = archive_path.with_name("index.json")
    index = read(base / index_path)
    for item in index["weeks"]:
        if item["week"] == week:
            item["feature_count"] = len(material["features"])
    if not any(item["week"] == week for item in index["weeks"]):
        index["weeks"].insert(0, {"week": week, "file": f"{week}.json", "start": source["week"]["start"],
                                "end": source["week"]["end"], "feature_count": len(public_features)})
    changed = []
    if any(item["deck"].get("source") == "melee" for item in public_features):
        # A previously accepted base may predate tabletop Feature rendering.
        # Copy on write so its original renderer/preview remain unchanged.
        for name in ("app-core.js", "app-mtgo.js"):
            relative = Path("assets/js/phase8") / name
            renderer = (root / relative).read_bytes()
            if not (site / relative).is_file() or (site / relative).read_bytes() != renderer:
                temporary = (site / relative).with_suffix(".js.new")
                temporary.write_bytes(renderer)
                temporary.replace(site / relative)
                changed.append(relative.as_posix())
        entrypoint = site / "index.html"
        html = entrypoint.read_text(encoding="utf-8")
        from hashlib import sha256
        for name in ("app-core.js", "app-mtgo.js"):
            relative = f"assets/js/phase8/{name}"
            version = sha256((site / relative).read_bytes()).hexdigest()[:12]
            html = re.sub(re.escape(relative) + r'(?:\?[^"\s>]*)?(?=")',
                          relative + "?v=" + version, html)
        if html != entrypoint.read_text(encoding="utf-8"):
            temporary = entrypoint.with_suffix(".html.new")
            temporary.write_text(html, encoding="utf-8")
            temporary.replace(entrypoint)
            changed.append("index.html")
    for relative, value in ((page_path, page), (archive_path, archive), (index_path, index)):
        if not (base / relative).is_file() or value != read(base / relative):
            write(site / relative, value)
            changed.append(relative.as_posix())
    write(output / "visuals.yaml", visual_config)
    write(output / "facts.json", facts)
    write(output / "source.json", source)
    write(output / "preparation.json", {"root": str(root.resolve()), "visuals": visuals or {},
        "names": editorial.load_name_catalog_document(root / editorial.DEFAULT_NAME_CATALOG),
        "input_digest": digest([source, facts, visual_config, page]), "changed": changed, "reused_files": reused_files})
    return finish_resources(output, fetch_missing=fetch_missing, resource_fixture=resource_fixture)


def finish_resources(output, *, fetch_missing=False, resource_fixture=None):
    """Resume only an unsubmitted preparation; never rewrite a preview snapshot."""
    if (output / "preview.json").exists():
        raise ValueError("Preview already fixed; use a new revision, not resources in place")
    plan, source, facts = (read(output / name) for name in ("preparation.json", "source.json", "facts.json"))
    root, site = Path(plan["root"]), output / "site"
    format_id, week = scope(source)
    config = read(output / "visuals.yaml")
    page = read(site / f"stats/{format_id}/mtgo/landing/current.json")
    if plan["input_digest"] != digest([source, facts, config, page]):
        raise ValueError("Preparation input changed; create a revision")
    from tools import weekly_resources, build_archetype_visuals
    resource_work = weekly_resources.ensure(site, page, fetch_missing=fetch_missing, fixture=resource_fixture)
    if plan["visuals"]:
        build_archetype_visuals.generate(site, format_id, identities=set(plan["visuals"]), config_override=config)
    packet = submissions.preview_packet(site, format_id)
    from mtgmeta.mtgo.landing_tabletop import deck_catalog
    decks = {item["token"]: item for item in deck_catalog(source)}
    content = submissions.make_content_packet(site, format_id, week, source["review"], page["environment"],
        plan["names"], bindings=source["bindings"],
        facts=facts["review_facts"], decks=decks)
    write(output / "content.json", content)
    write(output / "preview.json", packet)
    return {"format": format_id, "week": week, "site": str(site),
            "entrypoint": f"/index.html?format={format_id}&view=landing&lang=zh",
            "preview": str(output / "preview.json"), "state": "private_preview_requires_actual_page_check",
            "publishable": False, "source_digest": digest(source),
            "source": str(output / "source.json"), "facts": str(output / "facts.json"),
            "visual_config": str(output / "visuals.yaml"), "resources": resource_work,
            "work": {"generated": plan["changed"], "reused_files": plan["reused_files"], "fetched": 0,
                     "classified": 0, "translated": 0,
                     "reuse_check": "fixed scope and preview's selected product dependencies"}}


def prepare_facts(root, format_id, week, output):
    """One retained-input pass, shared by existing screening and Landing logic."""
    admitted = editorial.build_admitted_content_facts(root, format_id, week, require_delivered_classifier=True)
    rules, events, processed = (admitted[key] for key in ("rules", "events", "processed"))
    monday = editorial._week_monday(week)
    records, top8, page = (admitted[key] for key in ("records", "all_top8", "page"))
    policy = screening.load_screening_policy(root)
    known_file = root / f"stats/{format_id}/mtgo/landing/review/known_archetypes.json"
    known = screening.load_known(known_file, stable_ids=True)
    if known is None:
        start = monday - timedelta(weeks=screening.INITIAL_KNOWN_WEEKS)
        known = {r["archetype_id"] for day, event in events if start <= day < monday
                 for r in processed[id(event)]["records"] if r["archetype"] != "Unknown"}
    candidates, _, _, _ = editorial.build_candidate_documents(events, rules, monday, known,
        policy, format_id, stable_ids=True, processed_events=processed)
    evidence = []
    for item in candidates["existing_changes"] + candidates["new_archetypes"]:
        deck = next((d for d in top8 if str(d["event_id"]) == str(item["event_id"])
                     and d["deck_fingerprint_sha256"] == item["deck_fingerprint_sha256"]), None)
        if deck:
            evidence.append({"token": deck["token"], "source_order": len(evidence) + 1,
                             "reasons": item["candidate_reasons"]})
    bindings = {"source_event_ids": page["source_event_ids"], "classifier_digest": page["classifier"]["digest"],
        "selection_policy_digest": editorial.document_digest(policy),
        "machine_fact_digest": page["review_binding"]["machine_fact_digest"],
        "link_catalog_digest": editorial.document_digest(top8)}
    source = {"schema_version": "1.3.0", "format": format_id, "source": "mtgo", "week": page["week"],
        "bindings": bindings, "all_top8": top8, "candidate_evidence": evidence,
        "known_archetype_ids": sorted({r["archetype_id"] for r in records if r["archetype"] != "Unknown"}),
        "review": {"top_copy": {"items": []}, "features": {"items": []}}}
    facts = {"page": page, "bindings": bindings, "review_facts": admitted["review_facts"],
             "admitted_scope": admitted["admitted_scope"], "pending_event_ids": admitted["pending_event_ids"],
             "known_state": {"path": str(known_file.relative_to(root)),
                             "initialized": not known_file.exists(), "known_ids": sorted(known)},
             "environment_decks": [{"parent_id": r["archetype_id"], "event_id": r["event_id"],
                 "player": r["player"], "final_rank": r["final_rank"],
                 **screening.record_deck_cards(r)} for r in records if r["is_high_score"]]}
    facts["digest"] = digest(facts)
    write(output / "source.json", source)
    write(output / "facts.json", facts)
    return {"source": str(output / "source.json"), "facts": str(output / "facts.json"),
            "pending_event_ids": admitted["pending_event_ids"],
            "work": {"processed_events": len(events), "fetched": 0, "public_files_written": 0,
                     "reuse": "same processed retained events passed to existing builders"}}


def classification_material(root, format_id, week, melee_ids, output, localization=None):
    """Separate source submissions in one immutable full-deck Web carrier."""
    from mtgmeta import weekly_review
    scope({"format": format_id, "week": week})
    if len(set(melee_ids)) != len(melee_ids) or any(not re.fullmatch(r"[1-9][0-9]*", value) for value in melee_ids):
        raise ValueError("Melee members must be distinct positive event IDs")
    mtgo = weekly_review.build_mtgo_weekly_review(root, format_id, week)
    lookup_path = localization or root / "assets/card-localization/cards.json"
    lookup = read(lookup_path) if lookup_path.is_file() else {}
    inputs = {}
    for row in mtgo["records"]:
        relative, pointer = row["source_locator"].split("#", 1)
        if relative not in inputs:
            inputs[relative] = read(root / relative)
        player = inputs[relative]["players"][int(pointer.split("/")[-1])]
        row["main_deck"] = player.get("main_deck")
        row["sideboard"] = player.get("sideboard")
        row["reference"] = f"mtgo:{row['event_id']}:{row['rank']}"
    members = [{"source": "mtgo", "events": mtgo["event_ids"], "records": mtgo["records"],
                "unavailable": [], "packet": submissions.full_classification_packet(mtgo)}]
    blocked = []
    for event_id in melee_ids:
        try:
            review = weekly_review.build_melee_review(root, format_id, event_id, refresh_retained=True)
            if review["classifier"]["subject_digest"] != mtgo["classifier"]["subject_digest"]:
                raise ValueError("Melee/MTGO classifier subjects differ")
            event_path = root / f"data/{format_id}/melee/events/{event_id}.json"
            event = read(event_path)
            review["known_input_quality"] = event.get("quality", {})
            decks = {item["participant_id"]: item for item in event["decklists"]
                     if item.get("status") == "submitted" and item.get("game_format") == format_id}
            for row in review["available_records"]:
                row["event_metadata"] = event.get("metadata", {})
                row["date"] = event.get("metadata", {}).get("date", {}).get("start")
                row["event_name"] = event.get("metadata", {}).get("name", "")
                cards = decks[row["participant_id"]]["cards"]
                row["main_deck"] = [{"name": c["name"], "qty": c["quantity"]} for c in cards if c["section"] == "main"]
                row["sideboard"] = [{"name": c["name"], "qty": c["quantity"]} for c in cards if c["section"] == "sideboard"]
                row["reference"] = f"melee:{event_id}:{row['participant_id']}"
                row["source_locator"] = f"data/{format_id}/melee/events/{event_id}.json#participant/{row['participant_id']}"
            packet = submissions.make_packet("melee_classification", format_id, week,
                {f"melee.{event_id}": review}, bindings={"event_id": event_id,
                 "source_digest": digest(event), "classifier": review["classifier"]["subject_digest"]})
            members.append({"source": "melee", "events": [event_id], "records": review["available_records"],
                            "unavailable": review["unavailable_records"], "known_input_quality": event.get("quality", {}), "packet": packet})
        except (ValueError, OSError, KeyError) as exc:
            blocked.append({"source": "melee", "event_id": event_id, "error": str(exc)})
    for member in members:
        key = member["source"] + ("-" + member["events"][0] if member["source"] == "melee" else "")
        write(output / f"{key}-submission.json", member["packet"])
    material = {"format": format_id, "week": week, "members": members, "blocked": blocked}
    write(output / "materials.json", material)
    names_path = root / f"stats/{format_id}/archetype_names.json"
    names = read(names_path).get("names", []) if names_path.is_file() else []
    (output / "index.html").write_text(render_classification(material, lookup, names), encoding="utf-8")
    return {"material": str(output / "index.html"), "blocked": blocked, "state": "partial" if blocked else "ready",
            "scope": {"mtgo": mtgo["event_ids"], "melee": melee_ids}, "fetched": 0}


def stage_data(root, plan, resume_stage=None, previous=None):
    """Finite existing producer order, in an already isolated preparation tree."""
    from mtgmeta.mtgo.publication import stage_publications, resolve_scope
    root = root.resolve()
    if root == ROOT:
        raise ValueError("Use a separate isolated data candidate, not the implementation checkout")
    require_private_output(ROOT, root / "index.html")
    if (root / ".git").exists():
        branch = subprocess.run(["git", "-C", str(root), "branch", "--show-current"],
                                check=True, capture_output=True, text=True).stdout.strip()
        if branch in {"master", "main"}:
            raise ValueError("Data preparation cannot use a production branch")
    formats = plan.get("mtgo_formats", [])
    if len(formats) != len(set(formats)) or any(not re.fullmatch(r"[a-z][a-z0-9-]*", f) for f in formats):
        raise ValueError("Invalid MTGO product scope")
    for format_id in formats:
        scope({"format": format_id, "week": plan["week"]})
        if resolve_scope(root, format_id).week.strftime("%G-W%V") != plan["week"]:
            raise ValueError(f"Accepted MTGO scope does not match the planned week: {format_id}")
    if resume_stage is not None:
        if (not previous or previous.get("plan_digest") != digest(plan)
                or previous.get("root") != str(root)
                or Path(previous.get("stage", "")).resolve() != resume_stage.resolve()):
            raise ValueError("Resume requires the same plan, root and previously recorded stage")
    elif previous is not None:
        raise ValueError("Previous result requires its resume stage")
    from mtgmeta.melee import classification, opportunities, stats as melee_stats, matchup as melee_matchup, publish
    producers = {"classification": classification.main, "opportunities": opportunities.main, "stats": melee_stats.main,
                 "matchup": melee_matchup.main, "publish": publish.main}
    members = plan.get("melee", [])
    for item in members:
        scope({"format": item["format"], "week": plan["week"]})
        if not re.fullmatch(r"[1-9][0-9]*", item["event_id"]):
            raise ValueError("Invalid Melee event identity")
        if set(item["steps"]) - set(producers) or len(item["steps"]) != len(set(item["steps"])):
            raise ValueError("Unknown or duplicate Melee producer")
    completed = []
    if resume_stage is None:
        for item in members:
            # Scope is determined in step 3; this wrapper does not discover
            # additional consumers or silently expand historical products.
            for name, producer in producers.items():
                if name not in item["steps"]:
                    continue
                started = perf_counter()
                code = producer(["--root", str(root), "--format", item["format"],
                                 "--event-id", item["event_id"], "--execute"])
                if code:
                    raise ValueError(f"Melee {item['event_id']} {name} failed; retained candidate: {root}; completed={completed}")
                completed.append({"format": item["format"], "event": item["event_id"], "producer": name,
                                  "seconds": round(perf_counter() - started, 4)})
    if formats:
        result = stage_publications(root, formats, include_landing=False, execute=False, resume_stage=resume_stage)
    elif resume_stage is not None:
        raise ValueError("An MTGO resume stage requires its original format scope")
    else:
        result = {"stage": str(root), "formats": [], "executed": False}
    return {**result, "root": str(root), "melee_completed": completed,
            "reused_melee": (previous.get("melee_completed", []) + previous.get("reused_melee", [])) if previous else [],
            "plan_digest": digest(plan), "fetched": 0,
            "remote_writes": 0, "landing": "retained", "next": "verify the fixed combined product and reuse the existing package/publish path"}


def record_input(packet, values, *, evidence, accepted_on, previous=None):
    """Record actual owner-authored values, not an invented later Web visit."""
    allowed = [key for key in values if key == "features" or key == "copy.zh" or (key.startswith("feature.") and key.endswith(".zh"))]
    if not values or set(allowed) != set(values):
        raise ValueError("Owner input can establish selections and Chinese only, not English or visual/page acceptance")
    if any(packet["dimensions"].get(key) != value for key, value in values.items()):
        raise ValueError("Owner input differs from the material; preserve the actual input")
    receipt = submissions.record_decision(packet, previous, allowed, evidence=evidence,
                                          accepted_on=accepted_on, entrypoint="conversation:" + evidence)
    receipt["owner_input"] = {"evidence": evidence, "values": deepcopy(values), "kind": "authored_input"}
    return {"submission": packet, "decisions": receipt}


def page_delta(before_site, after_site, format_id, before_packet=None):
    """Identify a single Feature-card change; all other page meaning must match."""
    from mtgmeta.mtgo.landing_bundle import inspect_bundle
    old_bundle = inspect_bundle(before_site, format_id)
    if before_packet is not None:
        before = before_packet.get("submission", before_packet)
        submissions.validate_packet(before)
        if (before["kind"] != "preview" or before["format"] != format_id
                or before["bindings"].get("bundle_digest") != old_bundle["digest"]):
            raise ValueError("Retained preview does not bind the original page documents")
    else:
        try:
            before = submissions.preview_packet(before_site, format_id)
        except FileNotFoundError as exc:
            return {"state": "evidence_required", "reason": "Original selected resource unavailable",
                    "missing": str(exc.filename), "next": "Use the retained fixed preview via --before-packet; do not infer prior bytes"}
    after = submissions.preview_packet(after_site, format_id)
    old = old_bundle["documents"]
    new = inspect_bundle(after_site, format_id)["documents"]
    prior_features = {f["destination_id"]: f for f in old["landing"]["features"]["items"]}
    next_features = {f["destination_id"]: f for f in new["landing"]["features"]["items"]}
    changed = [key for key in set(prior_features) | set(next_features)
               if prior_features.get(key) != next_features.get(key)]
    def without_cards(value):
        if isinstance(value, dict):
            return {key: without_cards(item) for key, item in value.items()
                    if key not in {"review_binding", "generated_at", "content_digest"}
                    and not (key == "featured_cards" and value.get("destination_id") in changed)}
        if isinstance(value, list):
            return [without_cards(item) for item in value]
        return value
    a, b = before["dimensions"]["final_page"], after["dimensions"]["final_page"]
    if "image_subjects" not in a:
        return {"state": "evidence_required", "reason": "Retained preview lacks bilingual selected-resource evidence"}
    identical_context = all(a[key] == b[key] for key in ("names", "colors", "renderer_resources"))
    excluded_regions = {"feature:" + token for token in changed}
    def unchanged_regions(value):
        return submissions.image_display_subject({key: item for key, item in value["image_subjects"].items()
                                                  if key not in excluded_regions})
    identical_context = identical_context and unchanged_regions(a) == unchanged_regions(b)
    scoped = (len(changed) == 1 and set(prior_features) == set(next_features)
              and without_cards(old) == without_cards(new) and identical_context
              and (before["format"], before["week"]) == (after["format"], after["week"]))
    return {"before": before, "after": after, "changed_features": changed,
            "state": "feature_cards_only" if scoped else "same" if submissions.preview_validity(before, after, dimensions_only=True)["state"] in {"current", "equivalent"} else "wider_change",
            "work": "compared selected product documents and bound renderer/names/colors/images; no generation or browser rerun"}


def resource_selection_matches(packet, resources, only_feature=None):
    expected = []
    for region, languages in packet["dimensions"]["final_page"]["image_subjects"].items():
        if only_feature and region != "feature:" + only_feature:
            continue
        for language, images in languages.items():
            for item in images:
                expected.append({"region": region, "language": language, "name": item["name"],
                    "selected": item["image"], "sha256": item["sha256"],
                    "display_name": item["display_name"], "link": item["link"]})
    actual = [{key: row.get(key) for key in expected[0]} for row in resources] if expected else resources
    key = lambda row: json.dumps(row, sort_keys=True)
    return sorted(expected, key=key) == sorted(actual, key=key)


def accept_page(packet, check, *, evidence, accepted_on, entrypoint, previous=None, delta=None):
    if check.get("state") != "passed" or check.get("preview_digest") != packet["digest"]:
        raise ValueError("Actual-page check does not bind this preview")
    if check.get("only_feature"):
        if not previous or not delta or delta["state"] != "feature_cards_only":
            raise ValueError("Regional confirmation requires prior accepted page and mechanical delta")
        if delta["after"] != packet or delta["before"] != previous["submission"]:
            raise ValueError("Delta does not bind the actual accepted and changed pages")
        submissions.require_accepted(previous["submission"], previous["decisions"])
        if delta["changed_features"] != [check["only_feature"]]:
            raise ValueError("Confirmation/check scope differs from changed region")
    receipt = submissions.record_decision(packet, None, ["final_page"], evidence=evidence,
        accepted_on=accepted_on, entrypoint=entrypoint)
    if check.get("only_feature"):
        receipt["scoped_page_continuation"] = {"previous": previous, "delta_digest": digest(delta),
            "region": check["only_feature"], "evidence": evidence}
    return {"submission": packet, "decisions": receipt}


def adopt_displayed(packet, displayed_site, *, evidence, accepted_on, previous=None):
    """Apply the Owner's standing displayed-environment policy, not a new vote."""
    submissions.validate_packet(packet)
    if packet["kind"] != "content":
        raise ValueError("Displayed policy applies only to content environment dimensions")
    page = read(displayed_site / f"stats/{packet['format']}/mtgo/landing/current.json")
    colors = submissions.visual_colors(displayed_site, packet["format"])
    names_doc = read(displayed_site / f"stats/{packet['format']}/archetype_names.json")
    names = {item["identity_id"]: item["display"] for item in names_doc["names"]}
    keys = []
    for row in page["environment"]["rows"]:
        identity = row["archetype_id"]
        key = f"visual.environment.{identity}"
        old = {"colors": colors.get(identity), "cards": [c["name"] for c in row["key_cards"]]}
        same_names = all(packet["dimensions"].get(f"name.{packet['format']}|{identity}|none.{lang}") == names.get(identity, {}).get(lang)
                         for lang in ("zh", "en"))
        if old == packet["dimensions"].get(key) and same_names:
            keys.append(key)
    receipt = submissions.record_decision(packet, previous, keys, evidence=evidence,
        accepted_on=accepted_on, entrypoint=str(displayed_site)) if keys else deepcopy(previous or {})
    receipt["displayed_environment_policy"] = {"evidence": evidence, "page_digest": digest(page),
        "keys": keys, "basis": "Owner policy: previously displayed and unchanged configurations are accepted"}
    return {"submission": packet, "decisions": receipt}


def adopt_content(root, source, preparation):
    """Connect a fixed accepted candidate to the existing private importer."""
    root = root.resolve()
    if root == ROOT:
        raise ValueError("Content adoption requires a separate non-production preparation directory")
    if (root / ".git").exists() and subprocess.run(["git", "-C", str(root), "remote"],
            check=True, capture_output=True, text=True).stdout.strip():
        raise ValueError("Content adoption cannot target a remote-connected production checkout")
    require_private_output(ROOT, root / "index.html")
    format_id, _ = scope(source)
    prepared = read(preparation / "preview.json")
    bound = source["acceptance"]["decisions"]["accepted_page_binding"]
    if bound["preview_digest"] != prepared["digest"]:
        raise ValueError("Accepted source is not bound to this preparation")
    submissions.require_accepted(bound["acceptance"]["submission"], bound["acceptance"]["decisions"], current=prepared)
    configuration_path = root / "configs/mtgo_landing_visuals.yaml"
    configuration = read(configuration_path)
    proposed = read(preparation / "visuals.yaml")
    configuration["formats"][format_id] = proposed["formats"][format_id]
    old_config = configuration_path.read_bytes()
    from tools.weekly_resources import replace_bytes
    from tools.import_landing_conversation import import_content
    destination = root / f"stats/{format_id}/mtgo/landing/review/{source['week']['id']}.yaml"
    old_content = destination.read_bytes() if destination.is_file() else None
    write(configuration_path, configuration)
    if old_content is not None:
        replace_bytes(destination, old_content)  # Detach any retained hardlink.
    try:
        destination = import_content(root, source)
    except Exception:
        replace_bytes(configuration_path, old_config)
        if old_content is not None:
            replace_bytes(destination, old_content)
        raise
    return {"source": str(destination), "visuals": str(configuration_path), "remote_writes": 0}


def finalize_source(root, source, site, acceptance, facts):
    """Export accepted private source without another classification or generation."""
    format_id, week = scope(source)
    inventory(root, source, facts=facts)
    if "review_facts" not in facts or "admitted_scope" not in facts:
        raise ValueError("Fixed admitted facts with review_facts required")
    actual = submissions.preview_packet(site, format_id)
    submissions.require_accepted(acceptance["submission"], acceptance["decisions"], current=actual)
    page = read(site / f"stats/{format_id}/mtgo/landing/current.json")
    from mtgmeta.mtgo.landing_tabletop import deck_catalog
    decks = {item["token"]: item for item in deck_catalog(source)}
    material = editorial.materialize_review(source, editorial.load_name_catalog(root / editorial.DEFAULT_NAME_CATALOG),
                                           decks=decks)
    if (material["weekly_summary"] != page["weekly_summary"]["items"]
            or [landing._public_feature(item) for item in material["features"]] != page["features"]["items"]
            or source["bindings"]["classifier_digest"] != page["classifier"]["digest"]
            or source["bindings"]["source_event_ids"] != page["source_event_ids"]):
        raise ValueError("Source does not describe the actually accepted page")
    document = deepcopy(source)
    document["schema_version"] = "1.3.0"
    document["source"] = "mtgo"
    document["review"]["top_copy"]["reviewed"] = True
    document["review"]["features"]["reviewed"] = True
    packet = submissions.make_content_packet(root, format_id, week, document["review"], page["environment"],
        editorial.load_name_catalog_document(root / editorial.DEFAULT_NAME_CATALOG), bindings=source["bindings"],
        facts=facts["review_facts"], decks=decks)
    origin = acceptance["decisions"]["decisions"]["final_page"]
    receipt = submissions.record_decision(packet, None, list(packet["dimensions"]), evidence=origin["evidence"],
        accepted_on=origin["accepted_on"], entrypoint=origin["entrypoint"])
    receipt["accepted_page_binding"] = {"preview_digest": actual["digest"], "acceptance": acceptance}
    receipt["admitted_scope"] = deepcopy(facts["admitted_scope"])
    document["bindings"]["bilingual_catalog_digest"] = submissions.name_digest(packet)
    document["bindings"]["content_sha256"] = editorial.document_digest({k: document[k] for k in ("format", "week", "review")})
    document["acceptance"] = {"submission": packet, "decisions": receipt}
    from mtgmeta.mtgo.landing_tabletop import deck_catalog
    document.setdefault("known_archetype_ids", sorted({d["parent_id"] for d in deck_catalog(source)}))
    for index, item in enumerate(document.get("candidate_evidence", []), 1):
        item.setdefault("source_order", index)
    editorial.validate_review_document(document, root / editorial.DEFAULT_REVIEW_SCHEMA)
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    facts_cmd = sub.add_parser("facts")
    facts_cmd.add_argument("--root", type=Path, default=ROOT)
    facts_cmd.add_argument("--format", required=True)
    facts_cmd.add_argument("--week", required=True)
    facts_cmd.add_argument("--output", type=Path, required=True)
    classify = sub.add_parser("classification")
    classify.add_argument("--root", type=Path, default=ROOT)
    classify.add_argument("--format", required=True)
    classify.add_argument("--week", required=True)
    classify.add_argument("--melee", action="append", default=[])
    classify.add_argument("--output", type=Path, required=True)
    classify.add_argument("--localization", type=Path)
    render = sub.add_parser("render", help="Re-render a retained inventory/materials snapshot without rebuilding facts")
    render.add_argument("--root", type=Path, default=ROOT)
    render.add_argument("--input", type=Path, required=True)
    render.add_argument("--kind", choices=("content", "classification"), required=True)
    render.add_argument("--output", type=Path, required=True)
    render.add_argument("--localization", type=Path)
    stage = sub.add_parser("stage-data")
    stage.add_argument("--root", type=Path, required=True)
    stage.add_argument("--plan", type=Path, required=True)
    stage.add_argument("--resume-stage", type=Path)
    stage.add_argument("--previous-result", type=Path)
    stage.add_argument("--output", type=Path, required=True)
    resources = sub.add_parser("resources", help="Resume missing resources of an unsubmitted preparation")
    resources.add_argument("--preparation", type=Path, required=True)
    resources.add_argument("--fetch-missing-resources", action="store_true")
    resources.add_argument("--resource-fixture", type=Path)
    tabletop = sub.add_parser("tabletop", help="Add explicitly selected retained Swiss <=2-loss Feature decks")
    tabletop.add_argument("--root", type=Path, required=True)
    tabletop.add_argument("--source", type=Path, required=True)
    tabletop.add_argument("--facts", type=Path, required=True)
    tabletop.add_argument("--event", action="append", required=True)
    tabletop.add_argument("--output", type=Path, required=True)
    for name in ("inspect", "prepare"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--root", type=Path, default=ROOT)
        cmd.add_argument("--source", type=Path, required=True)
        cmd.add_argument("--output", type=Path, required=True)
        cmd.add_argument("--facts", type=Path)
        cmd.add_argument("--localization", type=Path, help="Existing bilingual lookup; never fetched here")
        if name == "inspect":
            cmd.add_argument("--displayed-page", type=Path)
            cmd.add_argument("--previous", type=Path)
            cmd.add_argument("--no-feature", action="store_true", help="Only when the Owner explicitly chose no Feature")
        else:
            cmd.add_argument("--base-site", type=Path, required=True)
            cmd.add_argument("--visuals", type=Path, help="Only actual Owner choices: identity -> two canonical names")
            cmd.add_argument("--fetch-missing-resources", action="store_true")
            cmd.add_argument("--resource-fixture", type=Path, help="Isolated finite response fixture; no live fallback")
    serve = sub.add_parser("serve")
    serve.add_argument("--directory", type=Path, required=True)
    serve.add_argument("--port", type=int, default=8765)
    check = sub.add_parser("check-preview")
    check.add_argument("--site", type=Path, required=True)
    check.add_argument("--format", required=True)
    check.add_argument("--output", type=Path, required=True)
    check.add_argument("--node", default="node")
    check.add_argument("--only-feature")
    record = sub.add_parser("record-input")
    record.add_argument("--packet", type=Path, required=True)
    record.add_argument("--values", type=Path, required=True)
    record.add_argument("--evidence", required=True)
    record.add_argument("--accepted-on", required=True)
    record.add_argument("--output", type=Path, required=True)
    record.add_argument("--previous", type=Path)
    delta_cmd = sub.add_parser("page-delta")
    delta_cmd.add_argument("--before-site", type=Path, required=True)
    delta_cmd.add_argument("--before-packet", type=Path, help="Retained fixed preview when original cache is unavailable")
    delta_cmd.add_argument("--after-site", type=Path, required=True)
    delta_cmd.add_argument("--format", required=True)
    delta_cmd.add_argument("--output", type=Path, required=True)
    accept = sub.add_parser("accept-page")
    accept.add_argument("--packet", type=Path, required=True)
    accept.add_argument("--check", type=Path, required=True)
    accept.add_argument("--evidence", required=True)
    accept.add_argument("--accepted-on", required=True)
    accept.add_argument("--entrypoint", required=True)
    accept.add_argument("--previous", type=Path)
    accept.add_argument("--delta", type=Path)
    accept.add_argument("--output", type=Path, required=True)
    adopt = sub.add_parser("adopt-displayed")
    adopt.add_argument("--packet", type=Path, required=True)
    adopt.add_argument("--displayed-site", type=Path, required=True)
    adopt.add_argument("--evidence", required=True)
    adopt.add_argument("--accepted-on", required=True)
    adopt.add_argument("--previous", type=Path)
    adopt.add_argument("--output", type=Path, required=True)
    finalize = sub.add_parser("finalize-source")
    finalize.add_argument("--root", type=Path, default=ROOT)
    finalize.add_argument("--source", type=Path, required=True)
    finalize.add_argument("--site", type=Path, required=True)
    finalize.add_argument("--acceptance", type=Path, required=True)
    finalize.add_argument("--facts", type=Path, required=True)
    finalize.add_argument("--output", type=Path, required=True)
    adopt_content_cmd = sub.add_parser("adopt-content")
    adopt_content_cmd.add_argument("--root", type=Path, required=True)
    adopt_content_cmd.add_argument("--source", type=Path, required=True)
    adopt_content_cmd.add_argument("--preparation", type=Path, required=True)
    adopt_content_cmd.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    started = perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        if args.command == "resources":
            result = finish_resources(args.preparation, fetch_missing=args.fetch_missing_resources,
                                      resource_fixture=args.resource_fixture)
            result["timing"] = {"started_at": started_at, "seconds": round(perf_counter() - started, 4)}
            write(args.preparation / "result.json", result)
            print(json.dumps({"result": str(args.preparation / "result.json"), "preview": result["preview"],
                              "downloaded": result["resources"]["downloaded"]}, ensure_ascii=False))
            return 0
        if args.command in {"page-delta", "accept-page", "adopt-displayed", "finalize-source", "stage-data", "adopt-content"}:
            require_private_output(ROOT, args.output.resolve())
            if args.output.exists():
                raise ValueError("Record exists; choose a new immutable path")
            if args.command == "page-delta":
                result = page_delta(args.before_site, args.after_site, args.format,
                                    read(args.before_packet) if args.before_packet else None)
            elif args.command == "stage-data":
                result = stage_data(args.root, read(args.plan), args.resume_stage,
                                    read(args.previous_result) if args.previous_result else None)
            elif args.command == "finalize-source":
                result = finalize_source(args.root, read(args.source), args.site, read(args.acceptance), read(args.facts))
            elif args.command == "adopt-content":
                result = adopt_content(args.root, read(args.source), args.preparation)
            elif args.command == "adopt-displayed":
                result = adopt_displayed(read(args.packet), args.displayed_site, evidence=args.evidence,
                    accepted_on=args.accepted_on, previous=read(args.previous)["decisions"] if args.previous else None)
            else:
                result = accept_page(read(args.packet), read(args.check), evidence=args.evidence,
                    accepted_on=args.accepted_on, entrypoint=args.entrypoint,
                    previous=read(args.previous) if args.previous else None,
                    delta=read(args.delta) if args.delta else None)
            write(args.output, result)
            print(json.dumps({"record": str(args.output), "state": result.get("state", "recorded"),
                              "seconds": round(perf_counter() - started, 4)}))
            return 0
        if args.command == "check-preview":
            output = new_output(ROOT, args.output)
            checked_packet = submissions.preview_packet(args.site, args.format)
            class QuietHandler(SimpleHTTPRequestHandler):
                def log_message(self, format, *args):
                    pass
            handler = functools.partial(QuietHandler, directory=str(args.site.resolve()))
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result = subprocess.run([args.node, str(ROOT / "tools/check_weekly_preview.cjs"),
                    f"http://127.0.0.1:{server.server_port}", args.format, str(output), str(args.site.resolve()),
                    args.only_feature or ""], capture_output=True, text=True)
            finally:
                server.shutdown()
                server.server_close()
            if result.returncode == 0:
                resources = json.loads((output / "resources.json").read_text(encoding="utf-8"))
                if (not resource_selection_matches(checked_packet, resources, args.only_feature)
                        or submissions.preview_packet(args.site, args.format) != checked_packet):
                    result = subprocess.CompletedProcess(result.args, 1, result.stdout,
                        "Consumer resource selection does not match the fixed preview, or candidate changed during check")
            summary = {"state": "passed" if result.returncode == 0 else "failed", "returncode": result.returncode,
                       "preview_digest": checked_packet["digest"], "only_feature": args.only_feature,
                       "stdout": result.stdout, "stderr": result.stderr,
                       "timing": {"started_at": started_at, "seconds": round(perf_counter() - started, 4)}}
            write(output / "result.json", summary)
            print(json.dumps(summary, ensure_ascii=False))
            return result.returncode
        if args.command == "serve":
            handler = functools.partial(SimpleHTTPRequestHandler, directory=str(args.directory.resolve()))
            server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
            print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}/index.html"}), flush=True)
            server.serve_forever()
            return 0
        if args.command == "record-input":
            require_private_output(ROOT, args.output.resolve())
            if args.output.exists():
                raise ValueError("Preserve previous decisions; choose a new record")
            result = record_input(read(args.packet), read(args.values), evidence=args.evidence, accepted_on=args.accepted_on,
                                  previous=read(args.previous)["decisions"] if args.previous else None)
            write(args.output, result)
            print(json.dumps({"record": str(args.output)}, ensure_ascii=False))
            return 0
        root = args.root.resolve()
        output = new_output(root, args.output)
        if args.command == "tabletop":
            from mtgmeta.mtgo import landing_tabletop
            source, facts = read(args.source), read(args.facts)
            format_id, week = scope(source)
            value = landing_tabletop.build_catalog(root, format_id, week, args.event)
            source["tabletop"] = value
            source["bindings"]["tabletop_digest"] = landing_tabletop.digest(value)
            facts["bindings"] = deepcopy(source["bindings"])
            facts["digest"] = digest({k: v for k, v in facts.items() if k != "digest"})
            write(output / "source.json", source)
            write(output / "facts.json", facts)
            print(json.dumps({"source": str(output / "source.json"), "facts": str(output / "facts.json"),
                              "events": value["events"], "deck_count": len(value["decks"]),
                              "fetched": 0, "classified": 0}, ensure_ascii=False))
            return 0
        if args.command == "render":
            material = read(args.input)
            format_id, _ = scope(material)
            lookup = args.localization or root / "assets/card-localization/cards.json"
            names_path = root / f"stats/{format_id}/archetype_names.json"
            renderer = render_inventory if args.kind == "content" else render_classification
            text = renderer(material, read(lookup) if lookup.is_file() else {},
                            read(names_path).get("names", []) if names_path.is_file() else [])
            (output / "index.html").write_text(text, encoding="utf-8")
            shutil.copyfile(args.input, output / args.input.name)
            write(output / "result.json", {"material": str(output / "index.html"),
                "retained_material_digest": digest(material), "classified": 0, "fetched": 0})
            print(json.dumps({"material": str(output / "index.html")}, ensure_ascii=False))
            return 0
        if args.command in {"facts", "classification"}:
            summary = (prepare_facts(root, args.format, args.week, output) if args.command == "facts"
                       else classification_material(root, args.format, args.week, args.melee, output, args.localization))
            summary["timing"] = {"started_at": started_at, "seconds": round(perf_counter() - started, 4)}
            write(output / "result.json", summary)
            print(json.dumps(summary, ensure_ascii=False))
            return 0
        source = read(args.source)
        lookup = args.localization or ((args.base_site if args.command == "prepare" else root) / "assets/card-localization/cards.json")
        source, normalizations = normalize_selected_cards(source, read(lookup) if lookup.is_file() else {})
        if args.command == "inspect":
            if args.no_feature:
                source.setdefault("review", {})["features"] = {"explicit_empty": True, "items": []}
                write(output / "source.json", source)
            result = inventory(root, source, read(args.displayed_page) if args.displayed_page else None,
                               read(args.previous) if args.previous else None, read(args.facts) if args.facts else None)
            write(output / "inventory.json", result)
            (output / "index.html").write_text(render_inventory(result, read(lookup) if lookup.is_file() else {},
                read(root / f"stats/{source['format']}/archetype_names.json").get("names", [])
                if (root / f"stats/{source['format']}/archetype_names.json").is_file() else []), encoding="utf-8")
            summary = {key: result[key] for key in ("required_user", "machine_pending", "errors", "new_types", "work")}
            summary["material"] = str(output / "index.html")
            summary["source"] = str(output / "source.json") if args.no_feature else str(args.source)
        else:
            summary = prepare(root, source, args.base_site.resolve(), output, read(args.facts) if args.facts else None,
                visuals=read(args.visuals) if args.visuals else None, fetch_missing=args.fetch_missing_resources,
                resource_fixture=args.resource_fixture)
        summary["timing"] = {"started_at": started_at, "seconds": round(perf_counter() - started, 4)}
        summary["card_name_normalizations"] = normalizations
        write(output / "result.json", summary)
        shown = deepcopy(summary)
        if "resources" in shown:
            shown["resources"] = {"downloaded": shown["resources"]["downloaded"],
                "reused_count": len(shown["resources"]["reused"]), "details": str(output / "result.json")}
        print(json.dumps(shown, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(json.dumps({"state": "blocked", "error": str(exc), "seconds": round(perf_counter() - started, 4)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
