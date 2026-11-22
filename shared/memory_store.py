"""Long-term memory: user preferences that survive between sessions."""
import json

from shared.paths import data_dir


def _file():
    return data_dir() / "memory.json"


def load() -> dict:
    f = _file()
    if not f.exists():
        return {"preferences": {}}
    return json.loads(f.read_text(encoding="utf-8"))


def set_preference(key: str, value: str) -> str | None:
    """Saves a preference. Returns the previous value (None if it is new)."""
    mem = load()
    key = key.strip().lower()
    old = mem["preferences"].get(key)
    mem["preferences"][key] = value
    _file().write_text(json.dumps(mem, ensure_ascii=False, indent=2), encoding="utf-8")
    return old


def compact() -> str:
    """Short text version, to inject into the context."""
    prefs = load()["preferences"]
    if not prefs:
        return "no saved preferences"
    return "; ".join(f"{k}={v}" for k, v in prefs.items())