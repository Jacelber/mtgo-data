"""Collect and render lightweight pytest timing observations for read-only CI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


REPORT_ENVIRONMENT_VARIABLE = "PYTEST_TIMING_REPORT"
COMMITTED_BASELINE_MARKER = "committed_baseline"
SLOW_TEST_LIMIT = 25


class TimingRecorder:
    """Record call-phase timing without changing pytest selection or outcomes."""

    def __init__(self, report_path: Path):
        self.report_path = report_path
        self.groups_by_nodeid: dict[str, str] = {}
        self.selected_counts = {"ordinary": 0, COMMITTED_BASELINE_MARKER: 0}
        self.results: list[dict[str, object]] = []

    def pytest_collection_modifyitems(self, items):
        for item in items:
            group = (
                COMMITTED_BASELINE_MARKER
                if item.get_closest_marker(COMMITTED_BASELINE_MARKER) is not None
                else "ordinary"
            )
            self.groups_by_nodeid[item.nodeid] = group
            self.selected_counts[group] += 1

    def pytest_runtest_logreport(self, report):
        if report.when != "call":
            return
        self.results.append(
            {
                "nodeid": report.nodeid,
                "group": self.groups_by_nodeid.get(report.nodeid, "ordinary"),
                "duration_seconds": report.duration,
                "outcome": report.outcome,
            }
        )

    def pytest_sessionfinish(self, session, exitstatus):
        groups = {}
        for group, selected in self.selected_counts.items():
            reports = [result for result in self.results if result["group"] == group]
            groups[group] = {
                "selected": selected,
                "completed": len(reports),
                "call_duration_seconds": sum(
                    float(result["duration_seconds"]) for result in reports
                ),
            }

        report = {
            "schema_version": "1.0.0",
            "exitstatus": exitstatus,
            "selected": sum(self.selected_counts.values()),
            "completed": len(self.results),
            "groups": groups,
            "slowest_tests": sorted(
                self.results,
                key=lambda result: float(result["duration_seconds"]),
                reverse=True,
            )[:SLOW_TEST_LIMIT],
        }
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def pytest_configure(config):
    report_path = os.environ.get(REPORT_ENVIRONMENT_VARIABLE)
    if report_path:
        config.pluginmanager.register(
            TimingRecorder(Path(report_path)), "ci-timing-recorder"
        )


def render_summary(report: dict[str, object]) -> str:
    groups = report["groups"]
    lines = [
        "## Pytest timing observation",
        "",
        "- Selected tests: {}".format(report["selected"]),
        "- Completed test calls: {}".format(report["completed"]),
        "- Pytest exit status: {}".format(report["exitstatus"]),
        "",
        "| Group | Selected | Completed | Call time |",
        "| --- | ---: | ---: | ---: |",
    ]
    for group in ("ordinary", COMMITTED_BASELINE_MARKER):
        values = groups[group]
        lines.append(
            "| {} | {} | {} | {:.2f}s |".format(
                group,
                values["selected"],
                values["completed"],
                values["call_duration_seconds"],
            )
        )

    lines.extend(["", "### Slowest test calls", "", "| Test | Duration | Outcome |", "| --- | ---: | --- |"])
    for result in report["slowest_tests"]:
        lines.append(
            "| `{}` | {:.2f}s | {} |".format(
                result["nodeid"], result["duration_seconds"], result["outcome"]
            )
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    arguments = parser.parse_args()
    report = json.loads(arguments.summary.read_text(encoding="utf-8"))
    print(render_summary(report), end="")


if __name__ == "__main__":
    main()
