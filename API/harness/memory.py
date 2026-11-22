"""Long-term memory: where it is stored and how it is retrieved.
Stored in data/memory.json (via shared/memory_store.py).
Written by the model through the save_preference tool.
Retrieved once per turn, in compact form, and injected by context.py."""
from shared import memory_store

FILE = "memory.py"


def log(msg: str) -> None:
    print(f"[{FILE}] {msg}")


def retrieve() -> str:
    """Returns all saved preferences as one short line."""
    prefs = memory_store.load()["preferences"]
    log(f"retrieved {len(prefs)} preference(s) from memory.json")
    return memory_store.compact()