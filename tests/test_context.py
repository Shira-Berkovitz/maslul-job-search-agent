import pytest

from API.harness import caching, context
from API.harness.tools import TOOLS
from shared import memory_store, tools_impl


@pytest.fixture(autouse=True)
def clean_data(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNT_DATA_DIR", str(tmp_path))


def test_context_has_memory_and_summary_but_not_full_list():
    memory_store.set_preference("work_mode", "hybrid")
    tools_impl.add_application("Alpha", "Backend Developer")
    msg = context.build_user_message("hi")
    ctx = msg["content"][0]["text"]
    assert "work_mode=hybrid" in ctx
    assert "1 applications" in ctx
    assert "Backend Developer" not in ctx  # details are pulled with a tool, not injected
    assert msg["content"][1]["text"] == "hi"


def test_messages_from_history_starts_after_last_compaction():
    entries = [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "old answer"},
        {"event": "compaction", "summary": "user likes hybrid"},
        {"role": "user", "content": "new"},
    ]
    msgs = context.messages_from_history(entries)
    assert "user likes hybrid" in msgs[0]["content"]
    assert msgs[-1]["content"] == "new"
    assert all(m["content"] != "old" for m in msgs)


def test_caching_marks_breakpoints_without_changing_originals():
    messages = [{"role": "user", "content": "hello"}]
    sys_c, tools_c, msgs_c = caching.apply("sys", TOOLS, messages)
    assert sys_c[0]["cache_control"] == {"type": "ephemeral"}
    assert tools_c[-1]["cache_control"] == {"type": "ephemeral"}
    assert msgs_c[-1]["content"][-1]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in TOOLS[-1]
    assert messages[0]["content"] == "hello"