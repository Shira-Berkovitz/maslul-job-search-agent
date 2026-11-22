"""Offline tests for the web app logic (no server, no API key)."""
import pytest

from shared import store
from tests.fake_client import FakeClient, text_response, tool_response
from web.service import JobHuntService


@pytest.fixture(autouse=True)
def clean_data(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNT_DATA_DIR", str(tmp_path))


def make_service(responses):
    client = FakeClient(responses)
    return JobHuntService(lambda: client, model="fake")


def test_chat_returns_reply_tools_meta_and_new_state():
    svc = make_service([
        tool_response(("a", "add_application", {"company": "Monday", "role": "Dev"})),
        text_response("added Monday"),
    ])
    out = svc.chat("I applied to Monday")
    assert out["reply"] == "added Monday"
    assert out["tools"] == ["add_application"]
    assert out["meta"]["model_calls"] == 2
    assert out["state"]["applications"][0]["company"] == "Monday"
    assert out["state"]["stats"]["turns"] == 1


def test_history_hides_context_and_tool_results():
    svc = make_service([
        tool_response(("a", "add_application", {"company": "Monday", "role": "Dev"})),
        text_response("added Monday"),
    ])
    svc.chat("I applied to Monday")
    assert svc.history() == [
        {"role": "user", "text": "I applied to Monday"},
        {"role": "assistant", "text": "added Monday", "tools": ["add_application"]},
    ]


def test_move_changes_status_without_the_model():
    svc = make_service([])
    store.add("Wix", "Dev")
    state = svc.move(1, "interview")
    assert state["applications"][0]["status"] == "interview"


def test_empty_message_is_rejected():
    with pytest.raises(ValueError):
        make_service([]).chat("   ")


def test_reset_clears_everything():
    svc = make_service([])
    store.add("Wix", "Dev")
    assert svc.reset()["applications"] == []
