"""Job applications storage: a single JSON file."""
import json
from datetime import date

from shared.paths import data_dir

STATUSES = ("saved", "applied", "interview", "offer", "rejected")


def _file():
    return data_dir() / "applications.json"


def load() -> list[dict]:
    f = _file()
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8"))


def save(apps: list[dict]) -> None:
    _file().write_text(json.dumps(apps, ensure_ascii=False, indent=2), encoding="utf-8")


def add(company: str, role: str, url: str = "", status: str = "applied") -> dict:
    if status not in STATUSES:
        raise ValueError(f"unknown status '{status}'. allowed: {', '.join(STATUSES)}")
    apps = load()
    app = {
        "id": max((a["id"] for a in apps), default=0) + 1,
        "company": company.strip(),
        "role": role.strip(),
        "url": url,
        "status": status,
        "updated": date.today().isoformat(),
    }
    apps.append(app)
    save(apps)
    return app


def find(company_or_id: str) -> dict:
    apps = load()
    key = str(company_or_id).strip().lower()
    for a in apps:
        if str(a["id"]) == key or a["company"].lower() == key:
            return a
    raise KeyError(f"no application matching '{company_or_id}'")


def set_status(company_or_id: str, status: str) -> tuple[dict, str]:
    if status not in STATUSES:
        raise ValueError(f"unknown status '{status}'. allowed: {', '.join(STATUSES)}")
    apps = load()
    target = find(company_or_id)
    for a in apps:
        if a["id"] == target["id"]:
            old = a["status"]
            a["status"] = status
            a["updated"] = date.today().isoformat()
            save(apps)
            return a, old
    raise KeyError(company_or_id)