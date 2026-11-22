"""Conversation history, saved to disk. Append-only (JSONL: one message per line)."""
import json

from shared.paths import data_dir

FILE = "history.py"


def log(msg: str) -> None:
    print(f"[{FILE}] {msg}")


class History:
    def __init__(self, name: str = "history.jsonl"):
        self.path = data_dir() / name

    def append(self, entry: dict) -> None:
        """entry is a message ({"role", "content"}) or an event ({"event": ...})."""
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        log(f"appended {entry.get('role') or entry.get('event')}")

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]