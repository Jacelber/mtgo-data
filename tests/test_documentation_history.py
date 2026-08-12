from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "docs" / "STATUS.yaml"
HISTORY_PATH = ROOT / "docs" / "history" / "STATUS-2026-08-04-pre-P11-13.yaml"
HISTORY_INDEX_PATH = ROOT / "docs" / "history" / "README.md"
EXPECTED_HISTORY_SHA256 = (
    "a8166a61b471b5140e4d67105fea02515e2dde3318429cd85fb6841cc0308c66"
)


def live_status_policy_errors(status_bytes: bytes) -> list[str]:
    errors = []
    if len(status_bytes) > 16 * 1024:
        errors.append("STATUS exceeds 16 KiB")
    status = yaml.safe_load(status_bytes)
    status_document = status.get("status_document", {})
    if status_document.get("live_state_only") is not True:
        errors.append("live_state_only must be true")
    history_policy = status_document.get("history_policy")
    if not isinstance(history_policy, str) or not history_policy.strip():
        errors.append("history_policy must be non-empty")
    return errors


def test_live_status_is_small_current_state_and_points_to_history():
    status_bytes = STATUS_PATH.read_bytes()
    status = yaml.safe_load(status_bytes)

    assert 8 * 1024 <= len(status_bytes) <= 16 * 1024
    assert live_status_policy_errors(status_bytes) == []
    assert status["status_document"]["live_state_only"] is True
    assert status["status_document"]["history_policy"].strip()
    assert status["current_phase"]["id"] == 12
    assert {"id", "name", "authorization", "stop_point"} <= set(status["current_task"])
    assert set(status["current_task"]["authorization"]) == {
        "local_implementation",
        "commit",
        "remote_publication",
        "merge",
    }
    assert all(
        isinstance(value, bool)
        for value in status["current_task"]["authorization"].values()
    )
    assert status["known_blockers"] == []
    assert status["next_approved_task"]["local_execution_authorized"] is False
    assert status["current_task"]["id"] == "CLASSIFIER-DISPLAY-NAME-DEDUPE"
    assert status["current_task"]["status"] == (
        "owner_accepted_publication_authorized"
    )
    assert status["current_task"]["base_commit"] == (
        "a2b254298508d10431e76531b6a4e029802c9165"
    )
    assert status["current_task"]["authorization"] == {
        "local_implementation": True,
        "commit": True,
        "remote_publication": True,
        "merge": True,
    }
    assert status["recent_completion_handoff"]["id"] == (
        "CLASSIFIER-R5-PRODUCTION-PROMOTION"
    )
    assert status["recent_completion_handoff"]["merge_commit"] == (
        "a2b254298508d10431e76531b6a4e029802c9165"
    )
    assert status["next_approved_task"]["id"] == "P12-10"
    assert status["next_approved_task"]["status"] == (
        "blocked_pending_display_name_fix_acceptance_landing_shadow_and_separate_authorization"
    )
    assert status["next_approved_task"]["requires_user_confirmation"] is True
    assert status["next_approved_task"]["remote_publication_authorized"] is False
    future_task_gates = {gate["task"]: gate for gate in status["future_task_gates"]}
    assert future_task_gates["P12-10"]["status"] == (
        "blocked_pending_separate_authorization_and_evidence"
    )

    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    audit = (ROOT / "docs" / "audits" / "CLASSIFIER-R5-PRODUCTION-PROMOTION.md").read_text(
        encoding="utf-8"
    )
    decisions = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    for document in (roadmap, audit, decisions):
        assert "R5" in document
        assert "P12-10" in document
    assert "statistical_json_structure" in audit
    assert "Pickup" in audit
    assert "434455" in audit
    assert "commit" in audit
    assert "R5" in audit
    assert "production" in audit
    assert "P12-10" in audit

    historical_paths = {
        item["path"]
        for item in status["authoritative_documents"]["historical_documents"]
    }
    assert "docs/history/README.md" in historical_paths
    assert "docs/history/STATUS-2026-08-04-pre-P11-13.yaml" in historical_paths


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("oversize", "STATUS exceeds 16 KiB"),
        ("not-live", "live_state_only must be true"),
        ("empty-history", "history_policy must be non-empty"),
    ],
)
def test_live_status_policy_rejects_regressions(mutation, expected):
    status = yaml.safe_load(STATUS_PATH.read_bytes())
    if mutation == "not-live":
        status["status_document"]["live_state_only"] = False
    elif mutation == "empty-history":
        status["status_document"]["history_policy"] = ""
    status_bytes = yaml.safe_dump(status).encode("utf-8")
    if mutation == "oversize":
        status_bytes += b"#" * (16 * 1024 + 1)

    assert expected in live_status_policy_errors(status_bytes)


def test_pre_split_status_history_is_complete_and_non_authoritative():
    history_bytes = HISTORY_PATH.read_bytes()
    history = yaml.safe_load(history_bytes)
    index = HISTORY_INDEX_PATH.read_text(encoding="utf-8")

    assert hashlib.sha256(history_bytes).hexdigest() == EXPECTED_HISTORY_SHA256
    assert history["current_task"]["id"] == "P11-12"
    assert "phase_0_tasks" in history
    assert "phase_8_plan" in history
    assert "phase_9_plan" in history
    assert "phase_5_tasks" in history
    assert "phase_6_tasks" in history
    assert "non-authoritative" in index
    assert "must not be used to authorize work" in index
    assert EXPECTED_HISTORY_SHA256 in index
    assert "83a54fe0907e1c8775b643295fd9e15327e0daf5" in index


def test_agent_adapters_are_thin_and_have_no_phase_snapshot():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    copilot = (ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")

    assert len(agents.encode("utf-8")) <= 8 * 1024
    assert len(claude.encode("utf-8")) <= 2 * 1024
    assert len(copilot.encode("utf-8")) <= 2 * 1024
    for adapter in (claude, copilot):
        assert "`AGENTS.md` is the mandatory entry point" in adapter
        assert "At the time this file was created" not in adapter
        assert "When the project is in Phase 0" not in adapter


def test_readme_keeps_supported_operations_without_phase_narrative():
    readme_bytes = (ROOT / "README.md").read_bytes()
    readme = readme_bytes.decode("utf-8")

    assert len(readme_bytes) <= 20 * 1024
    assert "Phase 9 is complete" not in readme
    assert "P7-02" not in readme
    assert "P7-03" not in readme
    assert "mtgo-data-mtgo.exe --root . --format standard build-statistics" in readme
    assert "mtgo-data-melee.exe --event-id 434455" in readme
    assert "-m mtgmeta.melee.retention" in readme
    assert "Melee production candidate" in readme
    assert "docs/STATUS.yaml" in readme


def test_pr_maturity_and_validation_class_policy_is_consistent():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    workflow = (ROOT / "docs" / "DEVELOPMENT_WORKFLOW.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    decisions = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    admission = (ROOT / "docs" / "audits" / "CI-MASTER-ADMISSION.md").read_text(
        encoding="utf-8"
    )

    assert "Pull-request maturity and validation scope are separate" in agents
    assert "Pull-request maturity is not an input to validation strength" in workflow
    assert "pull-request maturity and validation class are separated" in roadmap
    assert (
        "# DEC-085 - Separate pull-request maturity from validation class" in decisions
    )
    assert "Draft and Ready\npull requests use the same" in admission
    assert "every Ready pull request retains the complete" not in roadmap


def test_p12_03_landing_contract_is_consistent():
    scope = (ROOT / "docs" / "PROJECT_SCOPE.md").read_text(encoding="utf-8")
    statistics = (ROOT / "docs" / "STATISTICS_SPEC.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "DATA_ARCHITECTURE.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    decisions = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    audit = (ROOT / "docs" / "audits" / "P12-03.md").read_text(encoding="utf-8")

    for document in (statistics, roadmap, decisions, audit):
        assert "five percentage points" in document
        assert "Weekly Pickup" in document

    assert "five-percentage-point movement" in architecture
    assert "Weekly Pickup" in architecture

    assert "at least `0.03`" in statistics
    assert "construction-deviation score of at least `20`" in statistics
    assert "There is no separate public `notable`" in statistics
    assert "does not derive a statistical `new_entry`" in statistics
    assert "product ID `mtgo-landing`" in architecture
    assert "Standard and Modern are the explicit migration exceptions" in architecture
    assert "P12-10 is blocked" in architecture
    assert "future formats to admit Landing" in roadmap
    assert "# DEC-086 - Freeze the reviewed MTGO Landing contract" in decisions
    assert "products predate Landing" in scope


def test_p12_04b_design_and_pickup_integration_contract_is_consistent():
    design_system = (ROOT / "docs" / "FRONTEND_DESIGN_SYSTEM.md").read_text(
        encoding="utf-8"
    )
    scope = (ROOT / "docs" / "PROJECT_SCOPE.md").read_text(encoding="utf-8")
    statistics = (ROOT / "docs" / "STATISTICS_SPEC.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "DATA_ARCHITECTURE.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    decisions = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    audit = (ROOT / "docs" / "audits" / "P12-04.md").read_text(encoding="utf-8")

    for term in (
        "Editorial Analysis Console (A3)",
        "猫猫万智周报",
        "--canvas: #efece5",
        "--brand: #4b2c1f",
        "780 CSS pixels",
        "390- and 412-pixel widths",
        "prefers-reduced-motion",
        "not a top-level product",
    ):
        assert term in design_system

    navigation_section = scope.split("### 9.1 Navigation hierarchy", 1)[1].split(
        "### 9.2 MTGO page", 1
    )[0]
    assert "MTGO weekly Landing" in navigation_section
    assert "- Weekly Pickup." not in navigation_section
    assert "internal Weekly Pickup capability" in scope

    assert "every approved Weekly Pickup item" in statistics
    assert "final four-card display" in statistics
    assert "section-level selection changes" in statistics
    assert "only the curated feature content" in statistics
    assert "not a standalone" in statistics
    assert "user-facing product" in statistics

    assert "zero or more approved `new_deck`" in architecture
    assert "four reviewer-selected cards" in architecture
    assert "stats/<format>/mtgo/pickup/index.json" in architecture
    assert "product=weekly-pickup&week=<week>" in architecture
    assert "product=mtgo-landing&section=features&week=<week>" in architecture

    assert "duplicate standalone product" in roadmap
    assert "show every approved item for the selected feature week" in roadmap
    assert "four retained top-level product views" in roadmap
    assert "remove `weekly-pickup` from the product navigation" in roadmap
    assert "bounded archive view" in roadmap

    assert (
        "# DEC-087 - Integrate Weekly Pickup into the accepted Landing design"
        in decisions
    )
    assert (
        "supersede DEC-086's maximum of two items and eight-card display" in decisions
    )
    assert "## P12-04B contract freeze" in audit
    assert "P12-04B changes no production HTML" in audit


def test_p12_04a_visual_comparison_is_local_and_self_contained():
    comparison = (ROOT / "docs" / "design" / "p12-04a-comparison.html").read_text(
        encoding="utf-8"
    )
    audit = (ROOT / "docs" / "audits" / "P12-04.md").read_text(encoding="utf-8")
    selected = (ROOT / "docs" / "design" / "p12-04a-selected-desktop.html").read_text(
        encoding="utf-8"
    )
    cat_comparison = (
        ROOT / "docs" / "design" / "p12-04a-cat-brand-comparison.html"
    ).read_text(encoding="utf-8")
    talent_image = (
        ROOT / "docs" / "design" / "assets" / "p12-04a" / "stormchasers-talent.jpg"
    ).read_bytes()
    basics_image = (
        ROOT / "docs" / "design" / "assets" / "p12-04a" / "boomerang-basics.jpg"
    ).read_bytes()

    assert "方向 A · 编辑观察站" in comparison
    assert "方向 B · 分析控制台" in comparison
    assert "所有数值与文案均为布局示意" in comparison
    assert 'data-direction="a"' in comparison
    assert "<link " not in comparison
    assert "<script src=" not in comparison
    assert "http://" not in comparison
    assert "https://" not in comparison
    assert "Production front-end, code, data, or public path changed: no" in audit
    assert "No repository content was transmitted" in audit
    assert "select **Direction A**" in audit
    assert "牌背配色题头" in selected
    assert "本周环境变化" in selected
    assert "数据完整度" in selected
    assert "本周环境占比" in selected
    assert "代表单卡" in selected
    assert "此前四周占比" in selected
    assert "本周全部精选内容" in selected
    assert "固定 3% 纳入阈值" in selected
    assert "与下表采用相同的 3%" in selected
    assert "Stormchaser's Talent" in selected
    assert "Boomerang Basics" in selected
    assert "推荐档层叠卡图" in selected
    assert "data-set-card-scale" not in selected
    assert "color-pips" in selected
    assert selected.count('class="mana-pip"') == 10
    for symbol in ("w", "u", "r", "g"):
        assert f"assets/p12-04a/mana-{symbol}.svg" in selected
    assert "brief-type" not in selected
    assert 'id="inline-detail-row"' in selected
    assert "查看完整环境占比统计" in selected
    assert "展开完整牌表和详情" not in selected
    assert "人工" not in selected
    assert "审核" not in selected
    assert "批准" not in selected
    assert "font-size: 17px" in selected
    assert "font-size: 19px" in selected
    assert selected.count('class="feature-card"') == 12
    assert talent_image.startswith(b"\xff\xd8") and len(talent_image) > 50_000
    assert basics_image.startswith(b"\xff\xd8") and len(basics_image) > 50_000
    for symbol in ("w", "u", "b", "r", "g"):
        symbol_image = (
            ROOT / "docs" / "design" / "assets" / "p12-04a" / f"mana-{symbol}.svg"
        ).read_bytes()
        assert symbol_image.startswith(b"<svg")
        assert b"<script" not in symbol_image.lower()
    assert "<link " not in selected
    assert "<script src=" not in selected
    assert "http://" not in selected
    assert "https://" not in selected
    assert "Repository-managed editorial input" in audit
    assert "does not require or prefer a web editor" in audit
    assert "## P12-04A-MOBILE responsive translation" in audit
    assert "390 to 412 pixels" in audit
    assert "@media (max-width: 780px)" in selected
    assert selected.count("assets/p12-04a/cat-line-art-watermark.png") == 1
    assert 'class="cat-brand-watermark" aria-hidden="true"' in selected
    assert selected.count('href="#features">本周精选</a>') == 1
    assert "往期精选" not in selected
    assert 'id="feature-week" aria-label="选择精选周次"' in selected
    assert "选择过去周次即可查看这一板块的历史内容" in selected
    assert "其他区域仍显示本周数据" in selected
    assert "桌面最终稿＋小屏翻译" in selected
    assert '<div class="brand"><strong>猫猫万智周报</strong></div>' in selected
    assert '<div class="brand"><small>' not in selected
    assert 'class="header-actions" aria-label="语言"' in selected
    assert 'aria-pressed="true">中文' in selected
    assert ".header-actions button {" in selected
    assert "border: 0;" in selected
    assert ".brand { grid-column: 1; grid-row: 1; }" in selected
    assert ".header-actions { grid-column: 2; grid-row: 1;" in selected
    assert "## Owner responsive-review refinements" in audit
    assert "## Cat-brand four-direction comparison" in audit
    assert 'data-variant="a"' in cat_comparison
    assert 'data-variant="b"' in cat_comparison
    assert 'data-variant="c"' not in cat_comparison
    assert 'data-variant="d"' not in cat_comparison
    assert cat_comparison.count("猫猫万智周报") == 3
    assert "MTGO Environment Trends" not in cat_comparison
    assert cat_comparison.count("assets/p12-04a/cat-line-art-prototype.png") == 1
    assert cat_comparison.count("assets/p12-04a/cat-line-art-watermark.png") == 1
    assert "assets/p12-04a/cat-portrait-prototype.png" not in cat_comparison
    assert "cat-medallion" in cat_comparison
    assert "cat-watermark" in cat_comparison
    assert "top: -5px;" in cat_comparison
    assert "right: 68px;" in cat_comparison
    assert "width: 84px;" in cat_comparison
    assert "height: 64px;" in cat_comparison
    assert ".cat-watermark { display: none; }" not in cat_comparison
    assert "ear-mark" not in cat_comparison
    assert "paw-mark" not in cat_comparison
    assert "cat-eye" not in cat_comparison
    assert "fur-stripe" not in cat_comparison
    assert "Cat-brand direction refinement" in audit
    assert "Owner-supplied line-art finalist comparison" in audit
    assert "http://" not in cat_comparison
    assert "https://" not in cat_comparison
    cat_line_art = (
        ROOT / "docs" / "design" / "assets" / "p12-04a" / "cat-line-art-prototype.png"
    ).read_bytes()
    assert cat_line_art.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(cat_line_art) > 100_000
    cat_watermark = (
        ROOT / "docs" / "design" / "assets" / "p12-04a" / "cat-line-art-watermark.png"
    ).read_bytes()
    assert cat_watermark.startswith(b"\x89PNG\r\n\x1a\n")
    assert cat_watermark[25] in (4, 6)
    assert len(cat_watermark) > 100_000
    assert "首次点按查看名称和占比" in selected
    assert "grid-template-columns: repeat(3, minmax(0, 1fr)) 116px" in selected
    assert "--rep-width: 70px" in selected
    assert "--rep-height: 98px" in selected
    assert not (ROOT / "docs" / "design" / "p12-04a-selected-mobile.html").exists()
