"""What goes into each turn.
- The system prompt is STATIC (never changes) so it can be cached.
- Dynamic info (memory + a one-line state summary) is attached to the user's message,
  NOT the full list of applications: the model pulls details with list_applications.
- When a session starts, the messages are rebuilt from history (from the last compaction)."""
from datetime import date

from API.harness import memory
from shared import tools_impl

FILE = "context.py"

SYSTEM_PROMPT = """You are a job-search tracking assistant.
You help the user track job applications, statuses and preferences.

Rules:
- Use the tools to read or change data. Never invent applications.
- When the user states a lasting preference or decision, save it with save_preference.
- The saved preferences are given to you in <context> on every turn.
- If a request contradicts a saved preference, point out the conflict and ask which one
  is correct. Do not silently overwrite the preference.
- To see applications, call list_applications (the context has only a summary).
- Keep answers short. Answer in the user's language."""


def log(msg: str) -> None:
    print(f"[{FILE}] {msg}")


def build_user_message(user_text: str) -> dict:
    """The user's message + a small <context> block with only what is relevant."""
    ctx = (f"<context>\ntoday: {date.today().isoformat()}\n"
           f"preferences: {memory.retrieve()}\n"
           f"applications: {tools_impl.summary_line()}\n</context>")
    log(f"context block: {len(ctx)} chars")
    return {"role": "user", "content": [{"type": "text", "text": ctx},
                                        {"type": "text", "text": user_text}]}


def messages_from_history(entries: list[dict]) -> list[dict]:
    """Rebuild the message list from history.jsonl, starting at the last compaction."""
    start, summary = 0, None
    for i, e in enumerate(entries):
        if e.get("event") == "compaction":
            start, summary = i + 1, e["summary"]
    messages = []
    if summary:
        messages += [
            {"role": "user", "content": f"Summary of our earlier conversation:\n{summary}"},
            {"role": "assistant", "content": "Understood, I have the summary."},
        ]
    messages += [e for e in entries[start:] if "role" in e]
    log(f"loaded {len(messages)} message(s) from history (compacted={summary is not None})")
    return messages