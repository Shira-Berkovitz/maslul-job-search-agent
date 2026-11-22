"""Runs the whole scenario runner offline, with a fake client (no API key)."""
import pytest

from API.main import run_scenario
from tests.fake_client import FakeClient, text_response, tool_response


@pytest.fixture(autouse=True)
def clean_data(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNT_DATA_DIR", str(tmp_path))


SCENARIO = {
    "sessions": [["save hybrid", "add Alpha"], ["what do I prefer?"]],
    "checks": [
        {"name": "mem", "type": "memory_contains_any", "values": ["hybrid"]},
        {"name": "alpha", "type": "app_status", "company": "Alpha", "status": "applied"},
        {"name": "loaded", "type": "session2_loaded_state"},
        {"name": "recall", "type": "response_mentions_any", "turn": 3, "values": ["hybrid"]},
        {"name": "fetch", "type": "tool_called", "tool": "fetch_job_posting"},  # should FAIL
    ],
}


def test_run_scenario_offline():
    responses = [
        tool_response(("a", "save_preference", {"key": "work_mode", "value": "hybrid"})),
        text_response("saved"),
        tool_response(("b", "add_application", {"company": "Alpha", "role": "Dev"})),
        text_response("added"),
        text_response("you prefer hybrid"),
    ]
    shared_client = FakeClient(responses)
    out = run_scenario(SCENARIO, lambda: shared_client, "fake", "medium", 20_000)
    passed = {c["name"]: c["passed"] for c in out["checks"]}
    assert passed == {"mem": True, "alpha": True, "loaded": True, "recall": True, "fetch": False}
    assert out["checks_passed"] == "4/5"
    assert [t["session"] for t in out["turns"]] == [1, 1, 2]
    assert out["totals"]["model_calls"] == 5
    assert out["lines_of_code"]["loop"] > 0