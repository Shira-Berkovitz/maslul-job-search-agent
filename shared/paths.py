"""Where the agent's data lives on disk (shared by API and SDK)."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    # Can be overridden (e.g. in tests) with the JOBHUNT_DATA_DIR env var
    d = Path(os.environ.get("JOBHUNT_DATA_DIR", PROJECT_ROOT / "data"))
    d.mkdir(parents=True, exist_ok=True)
    return d