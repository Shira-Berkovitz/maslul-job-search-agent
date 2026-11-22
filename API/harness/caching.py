"""Prompt caching: where to put cache_control breakpoints.
Cache order is tools -> system -> messages, so we mark:
  1. the last tool          (caches all tool schemas)
  2. the system prompt      (caches tools + system)
  3. the last message       (caches the whole conversation so far)
Copies are returned, so history on disk is never changed."""
import copy

FILE = "caching.py"
CACHE = {"type": "ephemeral"}


def log(msg: str) -> None:
    print(f"[{FILE}] {msg}")


def apply(system: str, tools: list[dict], messages: list[dict]):
    tools_c = copy.deepcopy(tools)
    tools_c[-1]["cache_control"] = CACHE

    system_c = [{"type": "text", "text": system, "cache_control": CACHE}]

    msgs_c = copy.deepcopy(messages)
    last = msgs_c[-1]
    if isinstance(last["content"], str):
        last["content"] = [{"type": "text", "text": last["content"]}]
    last["content"][-1]["cache_control"] = CACHE

    log("breakpoints: last tool, system, last message")
    return system_c, tools_c, msgs_c