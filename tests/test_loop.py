import pytest

from API.harness import loop
from API.harness.history import History
from API.harness.tokens import TokenMeter
from API.harness.tools import TOOLS
from shared import store
from tests.fake_client import FakeClient, text_response, tool_response


@pytest.fixture(autouse=True)
def clean_data(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNT_DATA_DIR", str(tmp_path))


def run(client, user_text):
    messages = [{"role": "user", "content": user_text}]
    return loop.run_turn(client, messages, system="test", tools=TOOLS, meter=TokenMeter(),
                         history=History(), model="fake"), messages


def test_loop_runs_tools_until_end_turn():
    client = FakeClient([
        tool_response(("t1", "add_application", {"company": "Alpha", "role": "Dev"}),
                      ("t2", "save_preference", {"key": "work_mode", "value": "hybrid"})),
        text_response("done"),
    ])
    result, messages = run(client, "add Alpha")
    assert result["model_calls"] == 2
    assert result["text"] == "done"
    assert result["tools_called"] == ["add_application", "save_preference"]
    # both tool results returned in ONE user message
    results_msg = messages[2]
    assert results_msg["role"] == "user"
    assert [b["tool_use_id"] for b in results_msg["content"]] == ["t1", "t2"]
    # the state on disk changed
    assert store.find("Alpha")["role"] == "Dev"


def test_tool_error_goes_back_as_is_error():
    client = FakeClient([
        tool_response(("t1", "update_status", {"company_or_id": "Nope", "status": "offer"})),
        text_response("could not find it"),
    ])
    result, messages = run(client, "update Nope")
    block = messages[2]["content"][0]
    assert block["is_error"] is True
    assert result["text"] == "could not find it"


def test_history_is_append_only():
    h = History()
    h.append({"role": "user", "content": "a"})
    h.append({"role": "user", "content": "b"})
    assert [m["content"] for m in h.read_all()] == ["a", "b"]