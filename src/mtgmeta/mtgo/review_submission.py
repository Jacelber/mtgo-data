"""Scoped, portable review material and explicit decisions, effective from W38.

Digests bind submitted material, not human attention or authorization. The agent
must obtain the cited decision in conversation; these records are not signatures.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import html
import json
from pathlib import Path
import re

from .landing_bundle import digest

EFFECTIVE_WEEK = "2026-W38"
VERSION = "1.0.0"


def names_approved(status) -> bool:
    return status == "approved" or status == {"english": "approved", "chinese": "approved"}


def applies(week: str) -> bool:
    if not isinstance(week, str) or not re.fullmatch(r"\d{4}-W\d{2}", week):
        raise ValueError("Use a complete ISO week, YYYY-Wnn")
    year, number = week.split("-W")
    date.fromisocalendar(int(year), int(number), 1)
    return week >= EFFECTIVE_WEEK


def dimension_digest(packet: dict, key: str) -> str:
    return digest({"format": packet["format"], "week": packet["week"],
                   "kind": packet["kind"], "key": key, "value": packet["dimensions"][key]})


def make_packet(kind: str, format_id: str, week: str, dimensions: dict, *, bindings: dict) -> dict:
    applies(week)  # Validate the ISO week even when preparing historical examples.
    if not re.fullmatch(r"[a-z][a-z0-9-]*", format_id) or not dimensions:
        raise ValueError("Review requires a format and explicit judgment objects")
    packet = {"schema_version": VERSION, "kind": kind, "format": format_id,
              "week": week, "bindings": deepcopy(bindings), "dimensions": deepcopy(dimensions)}
    packet["digest"] = digest(packet)
    return packet


def validate_packet(packet: dict) -> None:
    if packet.get("schema_version") != VERSION or packet.get("digest") != digest(
        {key: value for key, value in packet.items() if key != "digest"}
    ):
        raise ValueError("Submitted review material changed")
    if not packet.get("dimensions"):
        raise ValueError("Submitted review has no judgment objects")


def record_decision(packet: dict, receipt: dict | None, keys: list[str], *,
                    evidence: str, accepted_on: str, entrypoint: str) -> dict:
    validate_packet(packet)
    if not evidence.strip() or not entrypoint.strip() or not keys:
        raise ValueError("Decision needs the actual conversation reference, submitted entry and scope")
    date.fromisoformat(accepted_on)
    result = deepcopy(receipt or {})
    scope = {key: packet[key] for key in ("format", "week", "kind")}
    if result and any(result.get(key) != value for key, value in scope.items()):
        raise ValueError("Decision receipt belongs to another format, week or review kind")
    result.update(scope)
    decisions = result.setdefault("decisions", {})
    for key in keys:
        if key not in packet["dimensions"]:
            raise ValueError(f"Decision refers to unsubmitted material: {key}")
        decisions[key] = {"subject": dimension_digest(packet, key), "evidence": evidence,
                          "accepted_on": accepted_on, "entrypoint": entrypoint,
                          "submitted_digest": packet["digest"]}
    return result


def decision_state(packet: dict, receipt: dict | None) -> dict:
    validate_packet(packet)
    scope_matches = receipt and all(receipt.get(key) == packet[key]
                                    for key in ("format", "week", "kind"))
    decisions = receipt.get("decisions", {}) if scope_matches else {}
    accepted, pending = [], []
    for key in packet["dimensions"]:
        decision = decisions.get(key, {})
        established = (packet["kind"] == "content" and key.startswith("name.")
                       and key in packet["bindings"].get("established_names", {})
                       and packet["bindings"]["established_names"][key] == packet["dimensions"][key])
        valid = established or (decision.get("subject") == dimension_digest(packet, key)
                 and all(isinstance(decision.get(field), str) and decision[field].strip()
                         for field in ("evidence", "accepted_on", "entrypoint", "submitted_digest")))
        if valid and not established:
            try:
                date.fromisoformat(decision["accepted_on"])
            except ValueError:
                valid = False
        (accepted if valid else pending).append(key)
    return {"accepted": accepted, "pending": pending}


def reuse_decisions(packet: dict, envelope: dict) -> dict:
    """Carry exact stable name/visual choices; weekly copy and final pages never roll forward."""
    prior, receipt = envelope["submission"], envelope["decisions"]
    state = decision_state(prior, receipt)
    if (prior["format"], prior["kind"]) != (packet["format"], packet["kind"]):
        raise ValueError("Cannot reuse decisions from another format or kind")
    if prior["week"] == packet["week"]:
        return deepcopy(receipt)
    result = {key: packet[key] for key in ("format", "week", "kind")}
    result["decisions"] = {}
    for key in state["accepted"]:
        if (key.startswith(("name.", "visual.")) and key in receipt.get("decisions", {})
                and key in packet["dimensions"] and prior["dimensions"][key] == packet["dimensions"][key]):
            result["decisions"][key] = {**receipt["decisions"][key], "subject": dimension_digest(packet, key),
                                         "reused_from_week": prior["week"]}
    return result


def require_accepted(packet: dict, receipt: dict, *, current: dict | None = None) -> None:
    state = decision_state(packet, receipt)
    if state["pending"]:
        raise ValueError("Review still needs decisions: " + ", ".join(state["pending"]))
    if current is not None:
        validate_packet(current)
        def subject(value):
            return {**{key: item for key, item in value.items() if key not in {"digest", "bindings"}},
                    "bindings": {key: item for key, item in value["bindings"].items() if key != "established_names"}}
        if subject(current) != subject(packet):
            changed = sorted(key for key in set(current["dimensions"]) | set(packet["dimensions"])
                             if current["dimensions"].get(key) != packet["dimensions"].get(key))
            raise ValueError("Submitted material no longer matches current content: "
                             + (", ".join(changed) or "source bindings"))


def classification_packet(materials: dict, requests: list[dict]) -> dict:
    review = materials["classification"]
    rows = {row["reference"]: row for row in review["records"]}
    if len(rows) != len(review["records"]):
        raise ValueError("Classification references must be unique")
    dimensions, used = {}, set()
    for request in requests:
        key = request["id"]
        members = request["members"]
        if (key in dimensions or not members or len(members) != len(set(members))
                or not request.get("reason") or not request.get("proposed")):
            raise ValueError("Every group needs a unique ID, all members, proposal and factual reason")
        selected = []
        for member in members:
            if member not in rows or member in used:
                raise ValueError(f"Missing or duplicated requested deck: {member}")
            row = deepcopy(rows[member])
            for zone in ("main_deck", "sideboard"):
                if not isinstance(row.get(zone), list) or (zone == "main_deck" and not row[zone]):
                    raise ValueError(f"{member}: complete {zone} is unavailable")
                if any(not isinstance(card.get("qty"), int) or isinstance(card["qty"], bool)
                       or card["qty"] <= 0 or not card.get("name") for card in row[zone]):
                    raise ValueError(f"{member}: invalid card quantities")
                row[zone + "_total"] = sum(card["qty"] for card in row[zone])
                for card in row[zone]:
                    translated = materials.get("localization", {}).get(card["name"], {}).get("zh_name")
                    if translated:
                        card["zh_name"] = translated
            selected.append(row)
            used.add(member)
        dimensions[key] = {"reason": request["reason"], "proposed": request["proposed"],
                           "members": selected}
        for language, name in request.get("names", {}).items():
            if language not in {"zh", "en"} or not isinstance(name, str) or not name.strip():
                raise ValueError("Name proposal must explicitly identify zh or en")
            dimensions[f"{key}.name.{language}"] = name
    return make_packet("classification", review["format"], review["week"], dimensions,
                       bindings={"event_ids": review["event_ids"],
                                 "classifier": review["classifier"]["subject_digest"],
                                 "classification_review_digest": review["classification_review_digest"]})


def full_classification_packet(review: dict) -> dict:
    """The full-table decision is distinct from individual classification proposals."""
    for row in review["records"]:
        if not all(isinstance(row.get(zone), list) for zone in ("main_deck", "sideboard")):
            raise ValueError("Full classification submission lacks complete deck material")
        if not row.get("reference"):
            raise ValueError("Full classification submission lacks direct references")
    value = {"event_ids": sorted(review["event_ids"]), "record_count": len(review["records"]),
             "classifier": review["classifier"]["subject_digest"],
             "classification_review_digest": review["classification_review_digest"]}
    return make_packet("full_classification", review["format"], review["week"],
                       {"full_classification": value}, bindings=value)


def validate_classification_acceptance(record: dict, format_id: str | None = None) -> None:
    if not applies(record["week"]):
        return
    acceptance = record.get("classification_acceptance")
    if not isinstance(acceptance, dict):
        raise ValueError("W38 onward full classification requires the submitted full-table decision")
    packet = acceptance["submission"]
    if (packet["kind"] != "full_classification" or packet["week"] != record["week"]
            or (format_id is not None and packet["format"] != format_id)
            or set(packet["dimensions"]) != {"full_classification"}):
        raise ValueError("Individual or other-scope decisions cannot accept a full classification")
    require_accepted(packet, acceptance["decisions"])
    value = packet["dimensions"]["full_classification"]
    if (value.get("classifier") != record["accepted_classifier_subject"]
            or value.get("classification_review_digest") != record["classification_review_digest"]
            or value.get("event_ids") != sorted(record["event_ids"])):
        raise ValueError("Classification acceptance subject changed")


def visual_colors(root: Path, format_id: str) -> dict:
    from mtgmeta.mana_identity import rendered_mana_identities

    return {
        identity_id: list(colors)
        for identity_id, colors in rendered_mana_identities(root, format_id).items()
    }


def content_dimensions(root: Path, format_id: str, review: dict, environment: dict, names: dict) -> dict:
    colors = visual_colors(root, format_id)
    dimensions = {}
    copy = review["top_copy"]["items"]
    features = review["features"]["items"]
    if bool(features) == bool(review["features"].get("explicit_empty")):
        raise ValueError("Feature selection and explicit empty decision disagree")
    for language in ("zh", "en"):
        dimensions[f"copy.{language}"] = [{"order": item["order"], "text": item["text"][language]}
                                            for item in copy]
    dimensions["features"] = [{key: item[key] for key in
                                ("destination_id", "parent_id", "subtype_id", "category", "source_order")}
                               for item in features]
    identities = set()
    for row in environment["rows"]:
        parent = row["archetype_id"]
        dimensions[f"visual.environment.{parent}"] = {
            "colors": colors.get(parent), "cards": [card["name"] for card in row["key_cards"]]}
        identities.add((parent, None))
    for item in features:
        identity = item["parent_id"] + ("/" + item["subtype_id"] if item["subtype_id"] else "")
        token = item["destination_id"]
        dimensions[f"visual.feature.{token}"] = {"colors": colors.get(identity), "cards": item["featured_cards"]}
        for language in ("zh", "en"):
            dimensions[f"feature.{token}.{language}"] = item["positioning"][language]
        identities.add((item["parent_id"], item["subtype_id"]))
    for key, value in dimensions.items():
        if key.startswith("visual."):
            expected = 2 if key.startswith("visual.environment.") else 4
            if (not isinstance(value["colors"], list) or not value["colors"]
                    or len(set(value["colors"])) != len(value["colors"])
                    or any(color not in "wubrgc" or len(color) != 1 for color in value["colors"])
                    or ("c" in value["colors"] and value["colors"] != ["c"])
                    or len(value["cards"]) != expected or len(set(value["cards"])) != expected):
                raise ValueError(f"Incomplete visual material: {key}; colorless must use ['c']")
    for parent, subtype in sorted(identities, key=lambda item: (item[0], item[1] or "")):
        identity = f"{format_id}|{parent}|{subtype or 'none'}"
        selected = next((item for item in names["names"] if item["identity_key"] == identity), None)
        if selected is None:
            raise ValueError(f"Missing displayed bilingual name: {identity}")
        for language, field in (("zh", "chinese"), ("en", "english")):
            dimensions[f"name.{identity}.{language}"] = selected[field]
    return dimensions


def make_content_packet(root, format_id, week, content, environment, names, *, bindings):
    dimensions = content_dimensions(root, format_id, content, environment, names)
    established = {}
    for item in names["names"]:
        status = item.get("review_status")
        for language, field in (("zh", "chinese"), ("en", "english")):
            key = f"name.{item['identity_key']}.{language}"
            approved = status == "approved" or isinstance(status, dict) and status.get(field) == "approved"
            if approved and key in dimensions:
                established[key] = item[field]
    return make_packet("content", format_id, week, dimensions,
                       bindings={**bindings, "established_names": established})


def content_packet(root: Path, source: dict) -> dict:
    import yaml
    from . import landing, landing_editorial as editorial
    format_id, week = source["format"], source["week"]["id"]
    subject = editorial.build_top8_subject(root, format_id, week)
    if source["week"] != subject["week"]:
        raise ValueError("Review content week differs from its actual subject")
    bindings = {key: subject[key] for key in ("source_event_ids", "classifier_digest",
                "selection_policy_digest", "machine_fact_digest", "link_catalog_digest")}
    if any(source["bindings"].get(key) != value for key, value in bindings.items()):
        raise ValueError("Review content uses outdated source bindings")
    year, number = week.split("-W")
    from datetime import timedelta
    _, page = landing.build_document(root, format_id,
                                     today=date.fromisocalendar(int(year), int(number), 1) + timedelta(days=7),
                                     _admit_review=False)
    names = yaml.safe_load((root / editorial.DEFAULT_NAME_CATALOG).read_text(encoding="utf-8"))
    return make_content_packet(root, format_id, week, source["review"], page["environment"], names,
                       bindings=bindings)


def name_digest(packet: dict) -> str:
    return digest({key: value for key, value in packet["dimensions"].items() if key.startswith("name.")})


def preview_images(root: Path, format_id: str, page: dict) -> dict:
    """Bind the actual selected local images, not every archetype's metadata."""
    result = {}
    rows = page["environment"]["rows"]
    if rows:
        source = (root / "assets/js/phase8/archetype-visuals.js").read_text(encoding="utf-8")
        section = source.split("const representativeCards = Object.freeze({", 1)[1]
        match = re.search(rf"^  {re.escape(format_id)}: Object\.freeze\(\{{\n(.*?)^  \}}\),", section, re.M | re.S)
        if not match:
            raise ValueError("Selected representative images are unavailable")
        groups = dict(re.findall(r'^    "([^"]+)": Object\.freeze\(\[\n(.*?)^    \]\),', match[1], re.M | re.S))
        for row in rows:
            cards = [json.loads(value) for value in re.findall(r'Object\.freeze\((\{[^\n]+\})\)', groups.get(row["archetype_id"], ""))]
            if [card["name"] for card in cards] != [card["name"] for card in row["key_cards"]]:
                raise ValueError("Rendered representative cards differ from the submitted environment")
            for card in cards:
                relative = card["image"]
                if not relative.startswith("../images/representative-cards/") or ".." in relative[3:].split("/"):
                    raise ValueError("Unsupported representative image location")
                path = "assets/" + relative[3:]
                result[path] = hashlib_sha(root / path)
    manifest_path = root / "assets/card-cache/v1/manifest.json"
    if manifest_path.is_file():
        from .landing_bundle import read_json
        manifest = read_json(manifest_path)
        selected = {card["name"] for feature in page["features"]["items"] for card in feature["featured_cards"]}
        for card in manifest["cards"]:
            if card["name"] not in selected:
                continue
            if not any(use.get("format") == format_id and page["week"]["id"] in use.get("weeks", []) for use in card["uses"]):
                continue
            relative = card["local_path"]
            if not relative.startswith("assets/card-cache/v1/") or ".." in relative.split("/"):
                raise ValueError("Unsupported Feature image location")
            result[relative] = hashlib_sha(root / relative)
    return result


def preview_packet(root: Path, format_id: str) -> dict:
    """Bind final acceptance to actual generated product files, not a proposal."""
    from .landing_bundle import inspect_bundle
    bundle = inspect_bundle(root, format_id)
    page = bundle["documents"]["landing"]
    colors = visual_colors(root, format_id)
    identities = {row["archetype_id"] for row in page["environment"]["rows"]}
    identities.update(item["archetype_id"] + ("/" + item["subtype_id"] if item.get("subtype_id") else "")
                      for item in page["features"]["items"])
    selected_colors = {key: colors.get(key) for key in sorted(identities)}
    if any(value is None for value in selected_colors.values()):
        raise ValueError("Final page is missing an explicit color identity")
    # Keep technical provenance separate so a repair with the same displayed
    # result can reuse decisions, while the new candidate is still verified.
    def meaning(value):
        if isinstance(value, dict):
            return {key: meaning(item) for key, item in value.items()
                    if key not in {"review_binding", "generated_at", "classifier_digest", "content_digest"}}
        if isinstance(value, list):
            return [meaning(item) for item in value]
        return value
    from .landing_bundle import read_json
    names = read_json(root / f"stats/{format_id}/archetype_names.json")
    selected_names = {row["identity_id"]: row["display"] for row in names["names"]
                      if row["identity_id"] in identities}
    if set(selected_names) != identities:
        raise ValueError("Final page is missing displayed bilingual names")
    resources = {path.relative_to(root).as_posix(): hashlib_sha(path) for path in
                 sorted((root / "assets/js/phase8").glob("*.js"))
                 if path.name != "archetype-visuals.js"}
    resources.update({path.relative_to(root).as_posix(): hashlib_sha(path)
                      for path in sorted((root / "assets/css").glob("phase8-*.css"))})
    if not resources or not (root / "index.html").is_file():
        raise ValueError("Final preview lacks its page renderer")
    resources["index.html"] = hashlib_sha(root / "index.html")
    dimensions = {"final_page": {"product_digest": digest(meaning(bundle["documents"])),
                                 "names": selected_names, "colors": selected_colors,
                                 "selected_local_images": preview_images(root, format_id, page),
                                 "renderer_resources": resources}}
    return make_packet("preview", format_id, bundle["week"], dimensions,
                       bindings={"bundle_digest": bundle["digest"], "renderer_resources": resources})


def hashlib_sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_completion(root: Path, format_id: str, week: str, record: dict) -> None:
    if not applies(week):
        return
    accepted = record.get("preview_acceptance", {})
    packet = accepted.get("submission", {})
    if packet.get("format") != format_id or packet.get("week") != week or packet.get("kind") != "preview":
        raise ValueError("Completion lacks the actual submitted final preview")
    require_accepted(packet, accepted["decisions"])
    publication = accepted.get("publication", {})
    if (publication.get("health") != "passed" or not publication.get("operation")
            or not publication.get("package") or publication.get("preview_digest") != packet["digest"]):
        raise ValueError("Completion requires the corresponding confirmed publication")
    # Completed historical weeks retain their recorded object. The current page
    # must still match when it is this week; a later admitted week does not undo it.
    from .landing_bundle import read_json
    current = read_json(root / f"stats/{format_id}/mtgo/landing/current.json")
    if current["week"]["id"] == week:
        actual = preview_packet(root, format_id)
        if actual["dimensions"] != packet["dimensions"]:
            raise ValueError("Completed preview differs from the current product")


def resume_summary(root: Path, format_id: str, week: str, *, envelope: dict | None = None) -> dict:
    import yaml
    from . import landing_editorial as editorial
    from .landing_bundle import read_json
    registry = yaml.safe_load((root / "configs/mtgo_weekly_review_completions.yaml").read_text(encoding="utf-8"))
    admissions = registry.get("data_admissions", {}).get("formats", {}).get(format_id, {})
    candidates = [admissions.get("initial", {}), *admissions.get("weekly_acceptances", [])]
    accepted = [item for item in candidates if item.get("week") == week
                and item.get("kind") in {"owner_accepted_initial_public_scope", "owner_accepted_full_classification"}]
    status = {"format": format_id, "week": week, "classification": "unknown",
              "data_publication": "unknown", "content": "not_recorded", "preview": "not_recorded",
              "features": "not_recorded", "copy": "not_recorded", "visuals": "not_recorded",
              "completion": "not_recorded", "pending_decisions": [], "next_actions": []}
    if accepted:
        from mtgmeta.weekly_review import build_mtgo_weekly_review
        current = build_mtgo_weekly_review(root, format_id, week)
        current_event_ids = set(current["event_ids"])
        valid = [item for item in accepted if item.get("classification_review_digest") == current["classification_review_digest"]
                 and item.get("accepted_classifier_subject") == current["classifier"]["subject_digest"]
                 and (current_event_ids <= set(item.get("event_ids", []))
                      if item.get("kind") == "owner_accepted_initial_public_scope"
                      else current_event_ids == set(item.get("event_ids", [])))]
        for item in list(valid):
            try:
                validate_classification_acceptance(item, format_id)
            except (ValueError, KeyError, TypeError):
                valid.remove(item)
        status["classification"] = "accepted" if valid else "changed"
        status["classification_evidence"] = [{key: item.get(key) for key in ("accepted_on", "evidence")} for item in valid]
    review_path = root / f"stats/{format_id}/mtgo/landing/review/{week}.yaml"
    if review_path.is_file():
        try:
            document = editorial.load_review_document(review_path, root / editorial.DEFAULT_REVIEW_SCHEMA)
            status["content"] = "accepted_recorded"
            status["features"] = "explicit_none" if document["review"]["features"]["explicit_empty"] else "selected"
            status["copy"] = "explicit_none" if not document["review"]["top_copy"]["items"] else "recorded"
            if "acceptance" in document:
                content_acceptance = document["acceptance"]
                current = content_packet(root, document)
                require_accepted(content_acceptance["submission"], content_acceptance["decisions"], current=current)
                status["visuals"] = "accepted"
                if envelope is None:
                    envelope = content_acceptance
        except (OSError, ValueError, KeyError, editorial.MTGOLandingEditorialError) as exc:
            status["content"] = "needs_repair"
            status["content_problem"] = str(exc)
    if envelope:
        packet = envelope["submission"]
        if packet["format"] != format_id or packet["week"] != week:
            raise ValueError("Resume input belongs to another format or week")
        status["pending_decisions"] = decision_state(packet, envelope.get("decisions"))["pending"]
        status["material_digest"] = packet["digest"]
        if packet["kind"] == "preview":
            try:
                current = preview_packet(root, format_id)
                state = decision_state(current, envelope.get("decisions"))
                status["pending_decisions"] = state["pending"]
                status["source_bindings_changed"] = current["bindings"] != packet["bindings"]
            except (OSError, ValueError, KeyError, TypeError) as exc:
                status["pending_decisions"] = ["final_page"]
                status["preview_problem"] = str(exc)
            status["preview"] = "accepted_recorded" if not status["pending_decisions"] else "pending"
        if packet["kind"] == "content":
            for field, prefixes in {"copy": ("copy.", "feature."), "visuals": ("visual.",),
                                    "features": ("features",)}.items():
                status[field] = "pending" if any(key.startswith(prefixes) for key in status["pending_decisions"]) else "accepted_recorded"
            if status["content"] == "needs_repair":
                status["next_actions"].append("先修复内容与当前输入的差异；已记录决定不代表当前内容可以发布")
    try:
        page = read_json(root / f"stats/{format_id}/mtgo/landing/current.json")
        status["local_landing_week"] = page["week"]["id"]
    except (OSError, ValueError, KeyError):
        status["local_landing_week"] = None
    completed = [item for item in registry.get("records", []) if item.get("week") == week
                 and format_id in item.get("formats", {})]
    if completed:
        try:
            validate_completion(root, format_id, week, completed[-1]["formats"][format_id])
            status["completion"] = "legacy_recorded" if not applies(week) else "confirmed_recorded"
            if applies(week):
                status["publication_evidence"] = completed[-1]["formats"][format_id]["preview_acceptance"]["publication"]
                status["data_publication"] = "confirmed_recorded"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            status["completion"] = "needs_repair"
            status["completion_problem"] = str(exc)
    status["next_actions"] += (["准备或修复本赛制的完整分类材料"] if status["classification"] != "accepted"
                              else ["复用分类决定，核对统计后准备本赛制内容"])
    if status["pending_decisions"]:
        status["next_actions"].append("仅提交列出的待决定内容；继续无关且已授权工作")
    if status["completion"] in {"legacy_recorded", "confirmed_recorded"}:
        status["next_actions"] = ["保留本周完成结果，不重开验收；后续周维护转入下一待审周"]
        if status["completion"] == "legacy_recorded":
            status["preview"] = status["visuals"] = "not_separately_recorded_legacy"
    status["next_actions"].append("如需核对当前线上状态，查询原发布操作；本地记录不等于实时线上查询")
    return status


def validate_content_acceptance(document: dict) -> None:
    acceptance = document.get("acceptance")
    if not isinstance(acceptance, dict):
        raise ValueError("Content acceptance is missing")
    packet = acceptance["submission"]
    if (packet["kind"] != "content" or packet["format"] != document["format"]
            or packet["week"] != document["week"]["id"]):
        raise ValueError("Content acceptance belongs to another subject")
    require_accepted(packet, acceptance["decisions"])
    for key, value in packet["bindings"].items():
        if key == "established_names":
            continue  # Rechecked against the actual catalog by content_packet/build_document.
        if document["bindings"].get(key) != value:
            raise ValueError(f"Content acceptance source changed: {key}")
    for language in ("zh", "en"):
        value = [{"order": item["order"], "text": item["text"][language]}
                 for item in document["review"]["top_copy"]["items"]]
        if value != packet["dimensions"].get(f"copy.{language}"):
            raise ValueError(f"Unsubmitted copy: {language}")
    features = document["review"]["features"]["items"]
    selection = [{key: item[key] for key in ("destination_id", "parent_id", "subtype_id", "category", "source_order")}
                 for item in features]
    if selection != packet["dimensions"].get("features"):
        raise ValueError("Unsubmitted Feature selection")
    for item in features:
        token = item["destination_id"]
        for language in ("zh", "en"):
            if item["positioning"][language] != packet["dimensions"].get(f"feature.{token}.{language}"):
                raise ValueError("Unsubmitted Feature text")
        if item["featured_cards"] != packet["dimensions"].get(f"visual.feature.{token}", {}).get("cards"):
            raise ValueError("Unsubmitted Feature cards")
    if name_digest(packet) != document["bindings"]["bilingual_catalog_digest"]:
        raise ValueError("Submitted names changed")


def write_materials(packet: dict, output: Path, receipt: dict | None = None, *, preview_entrypoint: str | None = None) -> None:
    """Produce one immutable, self-contained private handoff with direct anchors."""
    validate_packet(packet)
    if output.exists():
        raise ValueError("Use a new snapshot directory; preserve material already submitted")
    state = decision_state(packet, receipt)
    labels = {"reason": "判断依据", "proposed": "拟议分类", "members": "本组全部牌表",
              "reference": "引用编号", "main_deck": "完整主牌", "sideboard": "完整备牌",
              "main_deck_total": "主牌总数", "sideboard_total": "备牌总数", "event_id": "赛事",
              "rank": "排名", "player": "牌手", "date": "日期", "cards": "代表牌",
              "colors": "指示色", "text": "正文", "order": "顺序", "destination_id": "牌表引用",
              "parent_id": "类别", "subtype_id": "子类", "category": "类型", "source_order": "候选顺序"}
    def render(value, field=None):
        if field == "colors":
            return "无色" if value == [] else "／".join({"w": "白", "u": "蓝", "b": "黑", "r": "红", "g": "绿", "c": "无色"}[c] for c in value)
        if isinstance(value, list):
            if field in {"main_deck", "sideboard"}:
                return "<ul>" + "".join(f'<li>{card["qty"]} × {html.escape(card.get("zh_name", card["name"]))}'
                    + (f' <small>（{html.escape(card["name"])}）</small>' if card.get("zh_name") else '') + '</li>' for card in value) + "</ul>"
            return "<ol>" + "".join("<li>" + render(item) + "</li>" for item in value) + "</ol>" if value else "<p>明确为空</p>"
        if isinstance(value, dict):
            visible = {key: item for key, item in value.items() if key in labels}
            other = {key: item for key, item in value.items() if key not in labels}
            result = "<dl>" + "".join(f"<dt>{labels[key]}</dt><dd>{render(item, key)}</dd>"
                                       for key, item in visible.items()) + "</dl>"
            if other:
                result += "<details><summary>补充定位依据</summary><pre>" + html.escape(json.dumps(other, ensure_ascii=False, indent=2)) + "</pre></details>"
            return result
        text = str(value)
        pieces, previous = [], 0
        for match in re.finditer(r"\[\[card:([^|\]]+)\|([^\]]+)\]\]", text):
            pieces.extend((html.escape(text[previous:match.start()]),
                           f'<span title="{html.escape(match[1], quote=True)}">{html.escape(match[2])}</span>'))
            previous = match.end()
        pieces.append(html.escape(text[previous:]))
        return "".join(pieces)
    sections = []
    for key, value in packet["dimensions"].items():
        status = "已有有效确认" if key in state["accepted"] else "待判断"
        anchor = html.escape(key, quote=True)
        title = {"copy.zh": "中文正文", "copy.en": "英文正文", "features": "Feature 选择", "final_page": "最终页面"}.get(key, key)
        if key.startswith("name."):
            title = ("中文名称" if key.endswith(".zh") else "英文名称") + " · " + key[5:-3]
        elif key.startswith("visual."):
            title = ("高占比套牌视觉" if key.startswith("visual.environment.") else "Feature 视觉") + " · " + key.rsplit(".", 1)[-1]
        body = render(value)
        if key == "final_page":
            from urllib.parse import urlparse
            if not preview_entrypoint or urlparse(preview_entrypoint).scheme not in {"http", "https", "file"}:
                raise ValueError("Final preview material requires the actual submitted page entry")
            body = f'<p><a href="{html.escape(preview_entrypoint, quote=True)}">打开本次最终页面</a></p><p>请核对页面中的内容、名称、颜色、代表牌和使用体验。</p>'
        sections.append(f'<section id="{anchor}"><h2><a href="#{anchor}">{html.escape(title)}</a> · {status}</h2>{body}</section>')
    output.mkdir(parents=True)
    (output / "submission.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if receipt:
        (output / "decisions.json").write_text(json.dumps({"submission": packet, "decisions": receipt}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    page = ('<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>本次待确认材料</title><style>body{max-width:1000px;margin:32px auto;padding:20px;font:16px/1.6 system-ui;color:#183b39;background:#f3f5f0}section{background:white;padding:20px;margin:20px 0;border:1px solid #d9e3dc;border-radius:10px}h2,pre{overflow-wrap:anywhere;white-space:pre-wrap}h2{font-size:19px}dt{font-weight:bold}dd{margin-bottom:10px}a{color:#126b60}</style>'
            f'<h1>{html.escape(packet["week"])} · {html.escape(packet["format"])} · 本次确认范围</h1>'
            '<p>每项对应独立判断；中文、英文与视觉资料分别列出。请在对话中说明确认范围。已有有效决定继续复用。</p>'
            + "".join(sections) + f'<details><summary>材料版本</summary>{packet["digest"]}</details></html>')
    (output / "index.html").write_text(page, encoding="utf-8")
