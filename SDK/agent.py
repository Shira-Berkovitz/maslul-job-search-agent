"""The SDK version of the agent. Claude Code runs the harness; here we only configure it."""
import json

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient,
                              ResultMessage, TextBlock, ToolUseBlock)

from SDK import tools
from shared import pricing
from shared.paths import data_dir

FILE = "agent.py"

SYSTEM_PROMPT = """You are a job-search tracking assistant.
You help the user track job applications, statuses and preferences.

Rules:
- Use the tools to read or change data. Never invent applications.
- When the user states a lasting preference or decision, save it with save_preference.
- Preferences saved in earlier sessions are in your memory (CLAUDE.md).
- If a request contradicts a saved preference, point out the conflict and ask which one
  is correct. Do not silently overwrite the preference.
- To see applications, call list_applications.
- Keep answers short. Answer in the user's language."""


def log(msg: str) -> None:
    print(f"[SDK/{FILE}] {msg}")


def session_file():
    return data_dir() / "sdk_session.json"


def _load_session() -> dict:  # replaces: history.py
    f = session_file()  # replaces: history.py
    return json.loads(f.read_text()) if f.exists() else {}  # replaces: history.py


def load_session_id() -> str | None:  # replaces: history.py
    return _load_session().get("session_id")  # replaces: history.py


def save_session(session_id: str, total_cost_usd: float) -> None:  # replaces: history.py
    session_file().write_text(json.dumps({"session_id": session_id,  # replaces: history.py
                                          "total_cost_usd": total_cost_usd}))


class SdkJobHuntAgent:
    def __init__(self, model: str = "claude-opus-5-5", effort: str = "medium",
                 resume: str | None = None):
        self.options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,  # replaces: context.py
            model=model,
            effort=effort,
            mcp_servers={tools.SERVER: tools.server},  # replaces: tools.py
            tools=[],  # no built-in Claude Code tools, only ours
            allowed_tools=tools.ALLOWED_TOOLS,  # replaces: tools.py
            strict_mcp_config=True,
            permission_mode="dontAsk",  # anything not in allowed_tools is denied
            setting_sources=["project"],  # replaces: memory.py (loads CLAUDE.md from cwd)
            cwd=str(tools.workspace()),  # replaces: memory.py
            resume=resume,  # replaces: history.py
            max_turns=10,  # replaces: loop.py (max_iterations)
        )
        self.client = ClaudeSDKClient(self.options)
        # Claude Code reports a RUNNING total cost for the session, and a resumed session
        # continues the old total, so we start from the total saved at the end of session 1
        self._last_total_cost = _load_session().get("total_cost_usd", 0.0) if resume else 0.0
        log(f"agent configured (model={model}, effort={effort}, resume={resume})")

    async def __aenter__(self):
        await self.client.connect()
        return self

    async def __aexit__(self, *exc):
        await self.client.disconnect()

    async def ask(self, user_text: str) -> dict:
        log(f"user: {user_text}")
        await self.client.query(user_text)  # replaces: loop.py
        usage_by_call: dict[str, dict] = {}
        tools_called, texts, result = [], [], None
        async for msg in self.client.receive_response():  # replaces: loop.py
            if isinstance(msg, AssistantMessage):
                if msg.usage:  # one entry per model call (deduplicated by message id)
                    usage_by_call[msg.message_id or str(len(usage_by_call))] = msg.usage  # replaces: tokens.py
                for b in msg.content:
                    if isinstance(b, ToolUseBlock):
                        tools_called.append(b.name.removeprefix(f"mcp__{tools.SERVER}__"))
                    elif isinstance(b, TextBlock):
                        texts.append(b.text)
            elif isinstance(msg, ResultMessage):
                result = msg

        total = result.total_cost_usd or 0.0  # replaces: tokens.py (running total per session)
        sdk_cost = total - self._last_total_cost if total >= self._last_total_cost else total
        self._last_total_cost = total
        save_session(result.session_id, total)  # replaces: history.py
        # ResultMessage.usage = all model calls of THIS turn, with final output counts.
        # (AssistantMessage.usage is captured mid-stream, so its output count is too low.)
        u = result.usage or {}  # replaces: tokens.py
        tokens = {  # replaces: tokens.py
            "input": u.get("input_tokens", 0) or 0,
            "cache_read": u.get("cache_read_input_tokens", 0) or 0,
            "cache_write": u.get("cache_creation_input_tokens", 0) or 0,
            "output": u.get("output_tokens", 0) or 0,
        }
        text = result.result or "\n".join(texts)
        log(f"tokens={tokens} sdk_cost=${sdk_cost:.4f} tools={tools_called}")
        log(f"assistant: {text[:200]}")
        return {
            "text": text, "tools_called": tools_called,
            "model_calls": len(usage_by_call), "tokens": tokens,
            "cost_usd": round(sdk_cost, 6),  # what Claude Code reports (includes its own extra calls)
            "cost_usd_by_tokens": pricing.cost(tokens),  # same formula as the API version
            "seconds": round(result.duration_ms / 1000, 2),
            "sdk_num_turns": result.num_turns,
            "sdk_model_usage": {k: str(v) for k, v in (result.model_usage or {}).items()},
        }