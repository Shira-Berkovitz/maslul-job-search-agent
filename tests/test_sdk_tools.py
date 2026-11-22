"""Offline tests for the SDK tools (no login, no API key)."""
import asyncio

import pytest

pytest.importorskip("claude_agent_sdk")

from SDK import tools  # noqa: E402
from shared import store  # noqa: E402


@pytest.fixture(autouse=True)
def clean_data(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNT_DATA_DIR", str(tmp_path))


def call(t, args):
    return asyncio.run(t.handler(args))


def test_add_application_changes_state():
    r = call(tools.add_application, {"company": "Alpha", "role": "Dev"})
    assert "added #1 Alpha" in r["content"][0]["text"]
    assert store.find("Alpha")["status"] == "applied"


def test_tool_error_is_returned_as_is_error():
    r = call(tools.update_status, {"company_or_id": "Nope", "status": "offer"})
    assert r["is_error"] is True


def test_save_preference_writes_claude_md():
    call(tools.save_preference, {"key": "work_mode", "value": "hybrid"})
    text = (tools.workspace() / "CLAUDE.md").read_text(encoding="utf-8")
    assert "work_mode: hybrid" in text


def test_allowed_tools_are_only_ours():
    assert tools.ALLOWED_TOOLS == [f"mcp__jobs__{n}" for n in
                                   ["add_application", "update_status", "list_applications",
                                    "save_preference", "fetch_job_posting"]]