"""The agent loop: call the model, run tools, repeat while stop_reason == "tool_use"."""
from API.harness import caching
from API.harness import tools as tools_mod

FILE = "loop.py"


def log(msg: str) -> None:
    print(f"[{FILE}] {msg}")


def _to_dict(block) -> dict:
    """SDK block objects -> plain dicts (so they can be saved to JSON)."""
    if isinstance(block, dict):
        return block
    return block.model_dump(exclude_none=True)


def run_turn(client, messages: list[dict], *, system, tools, meter, history,
             model: str, max_tokens: int = 2048, extra: dict | None = None,
             max_iterations: int = 10) -> dict:
    """Runs one user turn to the end. `messages` must already end with the user message.
    Returns {"text", "tools_called", "model_calls"}."""
    tools_called: list[str] = []
    calls = 0
    while calls < max_iterations:
        log(f"calling model (call #{calls + 1}, {len(messages)} messages)")
        sys_c, tools_c, msgs_c = caching.apply(system, tools, messages)
        resp = client.messages.create(model=model, system=sys_c, tools=tools_c,
                                      messages=msgs_c, max_tokens=max_tokens, **(extra or {}))
        calls += 1
        meter.record(resp.usage)

        content = [_to_dict(b) for b in resp.content]
        assistant_msg = {"role": "assistant", "content": content}
        messages.append(assistant_msg)
        history.append(assistant_msg)
        log(f"stop_reason={resp.stop_reason}")

        if resp.stop_reason != "tool_use":
            text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
            return {"text": text, "tools_called": tools_called, "model_calls": calls}

        # Run every tool_use block, and send ALL results back in ONE user message
        results = []
        for b in content:
            if b.get("type") == "tool_use":
                tools_called.append(b["name"])
                results.append(tools_mod.dispatch(b["id"], b["name"], b.get("input", {})))
        results_msg = {"role": "user", "content": results}
        messages.append(results_msg)
        history.append(results_msg)
        log(f"sent {len(results)} tool_result(s) in one message")

    log("max_iterations reached, stopping")
    return {"text": "[stopped: too many tool calls]", "tools_called": tools_called,
            "model_calls": calls}