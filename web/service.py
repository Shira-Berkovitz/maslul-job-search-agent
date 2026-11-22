"""Everything the web app does, without any web framework.
server.py only maps HTTP routes to these methods (so this file can be tested offline)."""
import json
import threading

from API.agent import JobHuntAgent
from API.harness.history import History
from shared import checks, memory_store, store
from shared.paths import data_dir

FILE = "service.py"
CONTEXT_PREFIX = "<context>"
SUMMARY_PREFIX = "Summary of our earlier conversation"


def log(msg: str) -> None:
    print(f"[web/{FILE}] {msg}")


def _empty_stats() -> dict:
    return {"turns": 0, "model_calls": 0, "cost_usd": 0.0,
            "input": 0, "cache_read": 0, "cache_write": 0, "output": 0}


class JobHuntService:
    def __init__(self, make_client, model: str = "claude-opus-5-5", effort: str = "medium"):
        self.make_client = make_client
        self.model = model
        self.effort = effort
        self._agent = None
        self._lock = threading.Lock()  # one conversation, one turn at a time

    # ---------- helpers ----------
    def _stats_file(self):
        return data_dir() / "web_stats.json"

    def _load_stats(self) -> dict:
        f = self._stats_file()
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else _empty_stats()

    def _save_stats(self, stats: dict) -> None:
        self._stats_file().write_text(json.dumps(stats), encoding="utf-8")

    def _agent_instance(self) -> JobHuntAgent:
        if self._agent is None:
            self._agent = JobHuntAgent(self.make_client(), model=self.model, effort=self.effort)
        return self._agent

    # ---------- what the page shows ----------
    def state(self) -> dict:
        stats = self._load_stats()
        all_in = stats["input"] + stats["cache_read"] + stats["cache_write"]
        stats["cache_pct"] = round(100 * stats["cache_read"] / all_in) if all_in else 0
        return {
            "applications": store.load(),
            "preferences": memory_store.load()["preferences"],
            "stats": stats,
        }

    def history(self) -> list[dict]:
        """The saved conversation as chat bubbles: user text, then the assistant's final
        answer with the tools it used. Context blocks and tool results are hidden."""
        bubbles: list[dict] = []
        turn = None
        for e in History().read_all():
            role, content = e.get("role"), e.get("content")
            if role == "user":
                if isinstance(content, list) and content and content[0].get("type") == "tool_result":
                    continue
                text = content if isinstance(content, str) else content[-1].get("text", "")
                if text.startswith(SUMMARY_PREFIX) or text.startswith(CONTEXT_PREFIX):
                    continue
                if turn:
                    bubbles.append(turn)
                bubbles.append({"role": "user", "text": text})
                turn = {"role": "assistant", "text": "", "tools": []}
            elif role == "assistant" and turn is not None:
                blocks = content if isinstance(content, list) else [{"type": "text", "text": content}]
                for b in blocks:
                    if b.get("type") == "tool_use":
                        turn["tools"].append(b["name"])
                    elif b.get("type") == "text" and b.get("text", "").strip():
                        turn["text"] = b["text"]
        if turn and turn["text"]:
            bubbles.append(turn)
        return bubbles

    # ---------- actions ----------
    def chat(self, message: str) -> dict:
        message = message.strip()
        if not message:
            raise ValueError("ההודעה ריקה")
        with self._lock:
            r = self._agent_instance().ask(message)
            u = r["usage"]
            stats = self._load_stats()
            stats["turns"] += 1
            stats["model_calls"] += u["model_calls"]
            stats["cost_usd"] = round(stats["cost_usd"] + u["cost_usd"], 6)
            for k in ("input", "cache_read", "cache_write", "output"):
                stats[k] += u[k]
            self._save_stats(stats)
        all_in = u["input"] + u["cache_read"] + u["cache_write"]
        log(f"turn done: {r['tools_called']} ${u['cost_usd']}")
        return {
            "reply": r["text"],
            "tools": r["tools_called"],
            "meta": {"model_calls": u["model_calls"], "tokens": all_in + u["output"],
                     "cost_usd": u["cost_usd"], "seconds": r["seconds"],
                     "cache_pct": round(100 * u["cache_read"] / all_in) if all_in else 0},
            "state": self.state(),
        }

    def move(self, app_id: int, status: str) -> dict:
        """Manual drag-and-drop on the board (no model call)."""
        store.set_status(str(app_id), status)
        log(f"moved #{app_id} to {status}")
        return self.state()

    def reset(self) -> dict:
        with self._lock:
            checks.clean_state()
            self._agent = None
        log("all data cleared")
        return self.state()
