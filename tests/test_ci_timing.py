import json

from ci_timing import COMMITTED_BASELINE_MARKER, TimingRecorder, render_summary


class FakeItem:
    def __init__(self, nodeid, baseline=False):
        self.nodeid = nodeid
        self.baseline = baseline

    def get_closest_marker(self, name):
        return object() if self.baseline and name == COMMITTED_BASELINE_MARKER else None


class FakeReport:
    def __init__(self, nodeid, duration, outcome="passed", when="call"):
        self.nodeid = nodeid
        self.duration = duration
        self.outcome = outcome
        self.when = when


class FakeSession:
    def __init__(self, items):
        self.items = items


def test_timing_recorder_groups_calls_and_orders_the_slowest(tmp_path):
    report_path = tmp_path / "pytest-timing.json"
    recorder = TimingRecorder(report_path)
    recorder.pytest_collection_finish(
        FakeSession([
            FakeItem("tests/test_fast.py::test_fast"),
            FakeItem("tests/test_baseline.py::test_baseline", baseline=True),
        ])
    )
    recorder.pytest_runtest_logreport(FakeReport("tests/test_fast.py::test_fast", 0.25))
    recorder.pytest_runtest_logreport(
        FakeReport("tests/test_baseline.py::test_baseline", 1.5, outcome="failed")
    )
    recorder.pytest_runtest_logreport(
        FakeReport("tests/test_fast.py::test_fast", 0.01, when="setup")
    )
    recorder.pytest_sessionfinish(None, exitstatus=1)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["selected"] == 2
    assert report["completed"] == 2
    assert report["groups"]["ordinary"] == {
        "selected": 1,
        "completed": 1,
        "call_duration_seconds": 0.25,
    }
    assert report["groups"][COMMITTED_BASELINE_MARKER] == {
        "selected": 1,
        "completed": 1,
        "call_duration_seconds": 1.5,
    }
    assert [item["nodeid"] for item in report["slowest_tests"]] == [
        "tests/test_baseline.py::test_baseline",
        "tests/test_fast.py::test_fast",
    ]


def test_render_summary_contains_group_totals_and_slowest_test():
    summary = render_summary(
        {
            "selected": 2,
            "completed": 2,
            "exitstatus": 0,
            "groups": {
                "ordinary": {
                    "selected": 1,
                    "completed": 1,
                    "call_duration_seconds": 0.25,
                },
                COMMITTED_BASELINE_MARKER: {
                    "selected": 1,
                    "completed": 1,
                    "call_duration_seconds": 1.5,
                },
            },
            "slowest_tests": [
                {
                    "nodeid": "tests/test_baseline.py::test_baseline",
                    "duration_seconds": 1.5,
                    "outcome": "passed",
                }
            ],
        }
    )

    assert "Pytest timing observation" in summary
    assert "committed_baseline" in summary
    assert "tests/test_baseline.py::test_baseline" in summary
