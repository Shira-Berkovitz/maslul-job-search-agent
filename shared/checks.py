"""Scenario helpers shared by API/main.py and SDK/main.py:
clean start, pass/fail checks (mostly on saved STATE), totals, line counting."""
import json
import shutil

from shared import memory_store, store
from shared.paths import data_dir


def clean_state() -> None:
    """Every run starts from a clean state."""
    d = data_dir()
    shutil.rmtree(d)
    d.mkdir(parents=True)


def _memory_text() -> str:
    return json.dumps(memory_store.load(), ensure_ascii=False).lower()


def run_checks(checks: list[dict], turns: list[dict], extra: dict) -> list[dict]:
    """turns: the per-turn results. extra: facts collected by main.py
    (e.g. how many messages session 2 loaded)."""
    out = []
    for c in checks:
        kind = c["type"]
        try:
            if kind == "memory_contains_any":
                passed = any(v.lower() in _memory_text() for v in c["values"])
            elif kind == "memory_not_contains":
                passed = not any(v.lower() in _memory_text() for v in c["values"])
            elif kind == "app_status":
                passed = store.find(c["company"])["status"] == c["status"]
            elif kind == "tool_called":
                ts = [t for t in turns if "turn" not in c or t["turn"] == c["turn"]]
                passed = any(c["tool"] in t["tools_called"] for t in ts)
            elif kind == "session2_loaded_state":
                passed = extra.get("session2_loaded", 0) > 0
            elif kind == "response_mentions_any":
                text = next(t["response"] for t in turns if t["turn"] == c["turn"]).lower()
                passed = any(v.lower() in text for v in c["values"])
            else:
                raise ValueError(f"unknown check type {kind}")
            detail = ""
        except Exception as e:
            passed, detail = False, f"{type(e).__name__}: {e}"
        out.append({"name": c["name"], "type": kind, "passed": passed, "detail": detail})
        print(f"[checks.py] {'PASS' if passed else 'FAIL'} {c['name']} {detail}")
    return out


def totals(turns: list[dict]) -> dict:
    keys = ("input", "cache_read", "cache_write", "output")
    t = {k: sum(x["tokens"][k] for x in turns) for k in keys}
    t["model_calls"] = sum(x["model_calls"] for x in turns)
    t["cost_usd"] = round(sum(x["cost_usd"] for x in turns), 6)
    t["seconds"] = round(sum(x["seconds"] for x in turns), 2)
    all_input = t["input"] + t["cache_read"] + t["cache_write"]
    t["cache_hit_pct"] = round(100 * t["cache_read"] / all_input, 1) if all_input else 0.0
    return t


def count_code_lines(path) -> int:
    """Lines of code: not empty, not a comment."""
    n = 0
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#"):
            n += 1
    return n