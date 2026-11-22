"""Context window management: when the conversation gets too long,
summarize ALL of it with the model and continue from the summary.
The summary is APPENDED to history as an event (history stays append-only)."""
import json

FILE = "compaction.py"

SUMMARY_PROMPT = ("Summarize this conversation between a user and a job-search assistant. "
                  "Keep: every decision and preference, applications discussed and their "
                  "statuses, and open questions. Be brief, use bullet points.")


def log(msg: str) -> None:
    print(f"[{FILE}] {msg}")


def estimate_tokens(messages: list[dict]) -> int:
    """Rough estimate: ~4 characters per token."""
    return len(json.dumps(messages, ensure_ascii=False)) // 4


def _as_text(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        content = m["content"]
        if isinstance(content, str):
            lines.append(f"{m['role']}: {content}")
            continue
        for b in content:
            if b.get("type") == "text":
                lines.append(f"{m['role']}: {b['text']}")
            elif b.get("type") == "tool_use":
                lines.append(f"{m['role']} called {b['name']}({b.get('input')})")
            elif b.get("type") == "tool_result":
                lines.append(f"tool result: {b.get('content')}")
    return "\n".join(lines)


def maybe_compact(client, messages: list[dict], *, history, meter, model: str,
                  threshold: int) -> list[dict]:
    """Returns the messages to use from now on (the same list if no compaction was needed)."""
    size = estimate_tokens(messages)
    if size < threshold:
        log(f"~{size} tokens < threshold {threshold}, no compaction")
        return messages
    log(f"~{size} tokens >= threshold {threshold}, summarizing {len(messages)} messages")
    resp = client.messages.create(
        model=model, max_tokens=1024, system=SUMMARY_PROMPT,
        messages=[{"role": "user", "content": _as_text(messages)}],
    )
    meter.record(resp.usage)
    summary = "".join(getattr(b, "text", None) or (b.get("text", "") if isinstance(b, dict) else "")
                      for b in resp.content)
    history.append({"event": "compaction", "summary": summary})
    log(f"summary: {len(summary)} chars")
    return [
        {"role": "user", "content": f"Summary of our earlier conversation:\n{summary}"},
        {"role": "assistant", "content": "Understood, I have the summary."},
    ]