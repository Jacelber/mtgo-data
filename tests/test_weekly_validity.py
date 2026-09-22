"""Cross-entry continuation: immutable decisions, real deltas and historical completion."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace
import shutil

import pytest
import yaml

from mtgmeta.mtgo import review_submission as review
from tools import build_weekly_review_web as web


def accept(packet):
    return review.record_decision(packet, None, list(packet["dimensions"]),
        evidence="synthetic explicit Owner decision", accepted_on="2026-09-21", entrypoint="synthetic review")


def classification():
    return {"format": "standard", "week": "2026-W38", "event_ids": ["1"],
            "classifier": {"subject_digest": "a" * 64}, "classification_review_digest": "b" * 64,
            "events": [{"event_id": "1", "record_count": 1}],
            "records": [{"reference": "1-1", "parent_id": "deck-a", "subtype_id": None,
                         "main_deck": [{"name": "Card", "qty": 60}], "sideboard": []}]}


def admission(value):
    packet = review.full_classification_packet(value)
    return {"week": value["week"], "kind": "owner_accepted_full_classification",
            "event_ids": value["event_ids"], "accepted_classifier_subject": value["classifier"]["subject_digest"],
            "classification_review_digest": value["classification_review_digest"],
            "evidence": "synthetic", "accepted_on": "2026-09-21",
            "classification_acceptance": {"submission": packet, "decisions": accept(packet)}}


@pytest.mark.parametrize("change,expected", [("engine", "equivalent"), ("parent", "changed"),
    ("subtype", "changed"), ("cards", "changed"), ("event", "changed"), ("missing", "evidence_required")])
def test_classification_proof_is_scoped_and_shared_with_feature(change, expected):
    before = classification()
    record = admission(before)
    original = deepcopy(record)
    after = deepcopy(before)
    after["classifier"]["subject_digest"] = "c" * 64
    after["classification_review_digest"] = "d" * 64
    if change == "parent": after["records"][0]["parent_id"] = "deck-b"
    if change == "subtype": after["records"][0]["subtype_id"] = "variant"
    if change == "cards": after["records"][0]["main_deck"][0]["qty"] = 59
    if change == "event": after["event_ids"] = ["2"]
    if change == "missing":
        packet = record["classification_acceptance"]["submission"]
        packet["bindings"].pop("material_digest")
        packet["digest"] = review.digest({k: v for k, v in packet.items() if k != "digest"})
        record["classification_acceptance"]["decisions"] = accept(packet)
        original = deepcopy(record)
    assert review.classification_validity(record, after)["state"] == expected
    registry = {"data_admissions": {"formats": {"standard": {"weekly_acceptances": [record]}}}}
    assert bool(web.accepted_classification(registry, after)) == (expected == "equivalent")
    assert record == original
    after["format"] = "modern"
    assert review.classification_validity(record, after)["state"] == "evidence_required"


@pytest.mark.parametrize("change", ["copy", "colors", "facts", "policy", "events"])
def test_content_equivalence_does_not_accept_real_or_unseen_changes(change):
    dimensions = {"copy.zh": "accepted", "copy.en": "accepted English", "visual.environment.a": ["u"]}
    bindings = {"source_event_ids": ["1"], "selection_policy_digest": "p", "link_catalog_digest": "links",
                "classifier_digest": "old", "machine_fact_digest": "old", "material_digest": "a" * 64}
    old = review.make_packet("content", "standard", "2026-W38", dimensions, bindings=bindings)
    receipt = accept(old)
    bindings.update(classifier_digest="new", machine_fact_digest="new")
    same = review.make_packet("content", "standard", "2026-W38", dimensions, bindings=bindings)
    review.require_accepted(old, receipt, current=same)
    if change == "copy": dimensions["copy.en"] = "unseen"
    if change == "colors": dimensions["visual.environment.a"] = ["r"]
    if change == "facts": bindings["material_digest"] = "b" * 64
    if change == "policy": bindings["selection_policy_digest"] = "different"
    if change == "events": bindings["source_event_ids"] = ["1", "2"]
    changed = review.make_packet("content", "standard", "2026-W38", dimensions, bindings=bindings)
    with pytest.raises(ValueError): review.require_accepted(old, receipt, current=changed)


def test_content_reader_and_import_reuse_original_provenance(tmp_path, monkeypatch):
    from mtgmeta.mtgo import landing, landing_editorial as editorial
    from tools import import_landing_conversation as importer
    root = Path(__file__).resolve().parents[1]
    source = yaml.safe_load((root / "stats/modern/mtgo/landing/review/2026-W37.yaml").read_text(encoding="utf-8"))
    source["week"] = {"id": "2026-W38", "start": "2026-09-14", "end": "2026-09-20"}
    (tmp_path / "configs").mkdir()
    (tmp_path / editorial.DEFAULT_NAME_CATALOG).write_text("names: []", encoding="utf-8")
    (tmp_path / "schemas").mkdir()
    shutil.copyfile(root / editorial.DEFAULT_REVIEW_SCHEMA, tmp_path / editorial.DEFAULT_REVIEW_SCHEMA)
    monkeypatch.setattr(review, "visual_colors", lambda *a: {})
    facts = {"source_event_ids": source["bindings"]["source_event_ids"], "count": 247}
    keys = ("source_event_ids", "classifier_digest", "selection_policy_digest", "machine_fact_digest", "link_catalog_digest")
    packet = review.make_content_packet(tmp_path, "modern", "2026-W38", source["review"], {"rows": []},
        {"names": []}, bindings={k: source["bindings"][k] for k in keys}, facts=facts)
    source["acceptance"] = {"submission": packet, "decisions": accept(packet)}
    original = deepcopy(source)
    subject = {**source, **source["bindings"], "classifier_digest": "e" * 64, "machine_fact_digest": "f" * 64}
    monkeypatch.setattr(editorial, "build_top8_subject", lambda *a: subject)
    def build(*args, **kwargs):
        kwargs["_review_facts"].update(facts)
        return "not_applicable", {"environment": {"rows": []}}
    monkeypatch.setattr(landing, "build_document", build)
    current = review.content_packet(tmp_path, source)
    assert review.packet_validity(packet, current)["state"] == "equivalent"
    destination = importer.import_content(tmp_path, source)
    actual = editorial.load_review_document(destination, tmp_path / editorial.DEFAULT_REVIEW_SCHEMA)
    assert actual["acceptance"] == source["acceptance"]
    assert actual["bindings"]["classifier_digest"] == source["bindings"]["classifier_digest"]
    saved = destination.read_bytes()
    facts["count"] = 248
    with pytest.raises(ValueError): importer.import_content(tmp_path, source)
    assert destination.read_bytes() == saved
    assert source == original


def test_completed_history_survives_current_drift_and_late_event_is_a_supplement(tmp_path, monkeypatch):
    from tools import generate_weekly_maintenance_readiness as ready
    from mtgmeta.mtgo import publication, classification as classifier
    from mtgmeta import weekly_review
    before = classification()
    row = admission(before)
    preview = review.make_packet("preview", "standard", "2026-W38", {"final_page": "accepted"}, bindings={})
    completed = {"accepted_event_ids": ["1"], "accepted_classifier_subject": "a" * 64,
                 "classification_review_digest": "b" * 64, "landing_content_digest": "c" * 64,
                 "preview_acceptance": {"submission": preview, "decisions": accept(preview),
                    "publication": {"health": "passed", "package": "package", "operation": "op", "preview_digest": preview["digest"]}}}
    registry = {"schema_version": "1.2.0", "weekly_maintenance": {"standard": {"start_week": "2026-W38"}},
        "data_admissions": {"formats": {"standard": {"weekly_acceptances": [row]}}},
        "records": [{"week": "2026-W38", "completed_on": "2026-09-21", "evidence": "synthetic actual completion",
                     "review_scope": "full_official_classification_v2", "formats": {"standard": completed}}]}
    (tmp_path / "configs").mkdir()
    path = tmp_path / "configs/mtgo_weekly_review_completions.yaml"
    path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    page = tmp_path / "stats/standard/mtgo/landing/current.json"
    page.parent.mkdir(parents=True)
    page.write_text(json.dumps({"week": {"id": "2026-W38"}}))
    monkeypatch.setattr(ready, "_landing_content_digest", lambda *a: "c" * 64)
    monkeypatch.setattr(review, "preview_packet", lambda *a: preview)
    def build(root, fmt, week):
        result = deepcopy(before)
        result["week"] = week
        result["classifier"]["subject_digest"] = "d" * 64
        return result
    monkeypatch.setattr(weekly_review, "build_mtgo_weekly_review", build)
    state = ready._completion_state(tmp_path, "2026-W38", format_id="standard")
    assert state["state"] == "stale" and state["historical_state"] == "verified"
    events = [("1.json", {"event_id": "1", "starttime": "2026-09-15"}),
              ("2.json", {"event_id": "2", "starttime": "2026-09-22"})]
    pending = {"2"}
    monkeypatch.setattr(publication, "retained_events", lambda *a: events)
    monkeypatch.setattr(publication, "resolve_scope", lambda *a: SimpleNamespace(week=date(2026,9,14),event_ids={"1"},pending_event_ids=pending))
    monkeypatch.setattr(publication, "inspect_publication", lambda *a: [])
    monkeypatch.setattr(ready, "_intentional_unknowns", lambda *a, **k: {"standard": {}})
    monkeypatch.setattr(classifier, "audit_mtgo_classification", lambda *a: SimpleNamespace(reports={
        "unknown_decks": {"records": []}, "index": {"summary": {"strict_validation": "pass"}}}))
    def run():
        result = ready._independent_readiness(tmp_path, registry,publication_sha="a"*40,production_run_id="1",
            production_run_attempt="1",source_sha="b"*40,generated_at="2026-09-28T00:00:00Z")
        import jsonschema
        jsonschema.validate(result,json.loads((Path(__file__).resolve().parents[1]/"schemas/weekly-maintenance-readiness.schema.json").read_text(encoding="utf-8")))
        return result["formats"][0]
    first = run()
    assert first["review_week"] == "2026-W39"
    assert first["completed_reviews"] == ["2026-W38"]
    assert first["outstanding_supplement_weeks"] == []
    assert first["historical_changes"][0]["week"] == "2026-W38"
    events.append(("3.json", {"event_id": "3", "starttime": "2026-09-16"}));pending.add("3")
    second = run()
    assert second["review_week"] == "2026-W38" and second["review_kind"] == "supplement"
    assert second["completed_reviews"] == ["2026-W38"]
    assert second["outstanding_supplement_weeks"] == ["2026-W38"]
    # Admission alone cannot close an unfinished supplement.
    pending.remove("3")
    row["event_ids"] = ["1", "3"]
    path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    third = run()
    assert third["review_week"] == "2026-W38"
    assert third["outstanding_supplement_weeks"] == ["2026-W38"]
    # Completion is exercised through the append-only exporter in the producer tests.
    assert completed["accepted_event_ids"] == ["1"]
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == registry
    completed["preview_acceptance"]["publication"]["health"] = "unknown"
    path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    assert ready._completion_state(tmp_path,"2026-W38",format_id="standard")["historical_state"] == "invalid"


def test_equivalent_classification_decisions_continue_without_rewriting_original():
    original = classification()
    packet = review.full_classification_packet(original)
    envelope = {"submission": packet, "decisions": accept(packet)}
    saved = deepcopy(envelope)
    current = deepcopy(original)
    current["classifier"]["subject_digest"] = "c" * 64
    current["classification_review_digest"] = "d" * 64
    updated = review.full_classification_packet(current)
    receipt = review.reuse_decisions(updated, envelope)
    review.require_accepted(updated, receipt)
    assert receipt["decisions"] == saved["decisions"]["decisions"]
    assert receipt["equivalent_submission"] == packet
    current["classifier"]["subject_digest"] = "e" * 64
    again = review.full_classification_packet(current)
    review.require_accepted(again, review.reuse_decisions(again, {"submission": updated, "decisions": receipt}))
    current["records"][0]["parent_id"] = "unseen"
    changed = review.full_classification_packet(current)
    with pytest.raises(ValueError): review.require_accepted(changed, review.reuse_decisions(changed, envelope))
    assert envelope == saved


def test_new_completion_keeps_comparable_classification_material():
    from mtgmeta.weekly_review import build_v2_completion_record
    original = classification()
    record = build_v2_completion_record([original], week_id="2026-W38", completed_on="2026-09-21",
        evidence="synthetic actual acceptance", landing_content_digests={"standard": "c" * 64}, independent_format=True)
    packet = record["formats"]["standard"]["classification_submission"]
    changed = deepcopy(original)
    changed["classifier"]["subject_digest"] = "e" * 64
    changed["classification_review_digest"] = "f" * 64
    assert review.packet_validity(packet, review.full_classification_packet(changed))["state"] == "equivalent"


def test_readiness_workflow_preserves_old_notice_and_names_supplement(tmp_path):
    import os
    import subprocess
    node = os.environ.get("WEEKLY_TEST_NODE") or shutil.which("node")
    if not node:
        pytest.skip("Node runtime required for actual notification script verification")
    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] / ".github/workflows/update.yml").read_text(encoding="utf-8"))
    script = next(step["with"]["script"] for job in workflow["jobs"].values() for step in job.get("steps", [])
                  if step.get("name") == "Create or update the deduplicated readiness issue")
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(script), encoding="utf-8")
    harness = r"""
const assert=require('assert');
const script=JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'));
const run=new (Object.getPrototypeOf(async function(){}).constructor)('require','core','github','context','process',script);
(async()=>{
 const cases = [
  {selected:null, outstanding:[], existing:false},
  {selected:'2026-W38', outstanding:['2026-W38'], existing:false},
  {selected:null, outstanding:[], existing:true, close:true},
  {selected:'2026-W39', outstanding:[], existing:true, close:true},
  {selected:'2026-W37', outstanding:['2026-W38'], existing:true, close:false},
  {selected:'2026-W37', existing:true, close:false}, // older handoff has no queue proof
 ];
 for (const {selected,outstanding,existing,close} of cases) {
  const calls=[], summaries=[];
  const readiness={schema_version:'1.7.0',formats:[{format:'standard',review_week:selected,
    review_kind:selected==='2026-W38'?'supplement':'weekly', outstanding_supplement_weeks:outstanding,
    public_week:'2026-W38',landing_week:'2026-W38',data_admission:'review_delta_required',completion:{state:'stale'},
    completed_reviews:['2026-W38'],historical_changes:[{week:'2026-W38',mismatches:['technical evidence required']}],
    blockers:[],landing_screening:{status:'after_data_acceptance'}}]};
  const summary={addRaw(){return this},addEOL(){return this},addHeading(){return this},
    addCodeBlock(value){summaries.push(value);return this},async write(){}};
  const core={summary,setFailed(message){throw new Error(message)}};
  const issues=[{number:1,state:'closed',body:'<!-- weekly-maintenance:standard:2026-W38 -->'}];
  if(existing) issues.push({number:2,state:'open',body:'<!-- weekly-maintenance:standard:2026-W38:supplement -->'});
  const github={paginate:async()=>issues,rest:{issues:{
    listForRepo(){},create:async x=>{calls.push(x);return {data:{number:3}}},update:async x=>{calls.push(x)},createComment:async()=>{throw Error('unexpected comment')}}}};
  await run(name=>name==='fs'?{readFileSync:()=>JSON.stringify(readiness)}:require(name),core,github,
    {repo:{owner:'example',repo:'example'},serverUrl:'https://example.test',runId:1}, {env:{READINESS_RESULT:'success',READINESS_PATH:'synthetic'}});
  assert(!calls.some(call=>call.issue_number===1));
  assert.strictEqual(calls.some(call=>call.issue_number===2 && call.state==='closed'),!!close);
  assert(summaries.some(value=>value.includes('technical evidence required')));
  assert.strictEqual(calls.length,(selected?1:0)+(close?1:0));
  if(selected==='2026-W38') assert(calls[0].body.includes('<!-- weekly-maintenance:standard:2026-W38:supplement -->'));
 }

})().catch(e=>{console.error(e);process.exit(1)});
"""
    result = subprocess.run([node, "-e", harness, str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_same_technical_identifiers_cannot_hide_changed_material():
    before = classification()
    packet = review.full_classification_packet(before)
    before["records"][0]["main_deck"][0]["name"] = "Different Card"
    assert review.packet_validity(packet, review.full_classification_packet(before))["state"] == "changed"


@pytest.mark.parametrize("change", ["missing", "invalid", "contradiction", "partial"])
def test_classification_comparison_requires_consistent_material_evidence(change):
    raw = classification()
    record = admission(raw)
    row = raw["records"][0]
    row["deck_material_digest"] = review.digest({zone: row[zone] for zone in ("main_deck", "sideboard")})
    if change in {"missing", "invalid"}:
        row.pop("main_deck")
        row.pop("sideboard")
        if change == "missing": row.pop("deck_material_digest")
        else: row["deck_material_digest"] = "not-a-digest"
    elif change == "partial": row.pop("sideboard")
    else: row["main_deck"][0]["qty"] = 59
    assert review.classification_validity(record, raw)["state"] == "evidence_required"
    with pytest.raises(ValueError): review.classification_comparison_packet(raw)


def test_readiness_retains_all_queued_supplement_weeks(tmp_path, monkeypatch):
    from tools import generate_weekly_maintenance_readiness as ready
    from mtgmeta.mtgo import publication, classification as classifier
    from mtgmeta import weekly_review
    registry = {"weekly_maintenance": {"standard": {"start_week": "2026-W38"}},
        "data_admissions": {"formats": {"standard": {"weekly_acceptances": [
            {"week": "2026-W38", "event_ids": ["1"]}, {"week": "2026-W39", "event_ids": ["2", "4"]}]}}},
        "records": [{"week": week, "formats": {"standard": {"accepted_event_ids": [event]}}}
                    for week, event in [("2026-W38", "1"), ("2026-W39", "2")]]}
    monkeypatch.setattr(ready, "_completion_state", lambda *a, **k: {
        "state": "stale", "historical_state": "verified", "mismatches": ["technical drift"]})
    monkeypatch.setattr(ready, "_intentional_unknowns", lambda *a, **k: {"standard": {}})
    monkeypatch.setattr(publication, "resolve_scope", lambda *a: SimpleNamespace(
        week=date(2026, 9, 21), event_ids={"1", "2", "4"}, pending_event_ids={"3"}))
    monkeypatch.setattr(publication, "retained_events", lambda *a: [
        ("3.json", {"event_id": "3", "starttime": "2026-09-16"})])
    monkeypatch.setattr(weekly_review, "build_mtgo_weekly_review", lambda *a: classification())
    monkeypatch.setattr(publication, "inspect_publication", lambda *a: [])
    monkeypatch.setattr(classifier, "audit_mtgo_classification", lambda *a: SimpleNamespace(reports={
        "unknown_decks": {"records": []}, "index": {"summary": {"strict_validation": "pass"}}}))
    path = tmp_path / "stats/standard/mtgo/landing/current.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"week": {"id": "2026-W39"}}))
    result = ready._independent_readiness(tmp_path, registry, publication_sha="a"*40, production_run_id="1",
        production_run_attempt="1", source_sha="b"*40, generated_at="2026-10-05T00:00:00Z")["formats"][0]
    assert result["review_week"] == "2026-W38"
    assert result["outstanding_supplement_weeks"] == ["2026-W38", "2026-W39"]
    assert result["completed_reviews"] == ["2026-W38", "2026-W39"]
