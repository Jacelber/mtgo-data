from pathlib import Path
import json

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_playwright_dependency_and_command_are_pinned() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["private"] is True
    assert package["devDependencies"] == {"@playwright/test": "1.62.1"}
    assert package["scripts"] == {
        "test:browser": "node tests/browser/browser-preflight-cli.js && playwright test"
    }
    assert (ROOT / "package-lock.json").exists()
    config = (ROOT / "playwright.config.js").read_text(encoding="utf-8")
    assert 'command: "node tests/browser/static-server.js"' in config
    assert "python -m http.server" not in config


def test_browser_ci_job_is_parallel_read_only_and_exact() -> None:
    workflow = yaml.load(
        (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    job = workflow["jobs"]["browser-validation"]
    commands = [step.get("run") for step in job["steps"] if step.get("run")]
    assert job["needs"] == "admission"
    assert "permissions" not in job
    assert "npm ci" in commands
    assert "npx playwright install --with-deps chromium" in commands
    assert "npm run test:browser" in commands
    assert not any("setup-python" in step.get("uses", "") for step in job["steps"])


def test_browser_spec_covers_required_production_matrix() -> None:
    spec = (ROOT / "tests/browser/production-pages.spec.js").read_text(
        encoding="utf-8"
    )
    for required in (
        'const languages = ["zh", "en"]',
        'width: 390',
        '"standard", "modern"',
        'data-surface", surface',
        'tabletop-major-events',
        'unavailable Tabletop Standard redirects',
        'page.on("pageerror"',
    ):
        assert required in spec
