import pytest

from API.agent import JobHuntAgent
from API.harness import compaction
from API.harness.history import History
from API.harness.tokens import TokenMeter
from shared import memory_store
from tests.fake_client import FakeClient, text_response, tool_response


@pytest.fixture(autouse=True)
def clean_data(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNT_DATA_DIR", str(tmp_path))


def test_session_2_loads_state_from_disk():
    a1 = JobHuntAgent(FakeClient([
        tool_response(("t1", "save_preference", {"key": "work_mode", "value": "hybrid"})),
        text_response("saved"),
    ]))
    a1.ask("I only want hybrid jobs")

    # new instance = new session: it must load history + memory from disk
    client2 = FakeClient([text_response("you prefer hybrid")])
    a2 = JobHuntAgent(client2)
    assert len(a2.messages) == 4  # user, assistant(tool_use), user(tool_result), assistant
    a2.ask("what are my preferences?")
    sent = client2.requests[0]["messages"]
    assert "work_mode=hybrid" in sent[-1]["content"][0]["text"]  # memory in the context
    assert memory_store.load()["preferences"]["work_mode"] == "hybrid"


def test_effort_is_sent_to_the_model():
    client = FakeClient([text_response("hi")])
    JobHuntAgent(client, effort="medium").ask("hello")
    assert client.requests[0]["output_config"] == {"effort": "medium"}


def test_compaction_over_threshold_summarizes_and_appends_event():
    history = History()
    messages = [{"role": "user", "content": "x" * 400},
                {"role": "assistant", "content": "y" * 400}]
    client = FakeClient([text_response("- user likes hybrid")])
    new = compaction.maybe_compact(client, messages, history=history, meter=TokenMeter(),
                                   model="fake", threshold=50)
    assert "user likes hybrid" in new[0]["content"]
    assert history.read_all()[-1] == {"event": "compaction", "summary": "- user likes hybrid"}


def test_no_compaction_under_threshold():
    client = FakeClient([])
    msgs = [{"role": "user", "content": "short"}]
    assert compaction.maybe_compact(client, msgs, history=History(), meter=TokenMeter(),
                                    model="fake", threshold=10_000) is msgs
    assert client.requests == []