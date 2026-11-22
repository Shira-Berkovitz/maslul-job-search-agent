"""The domain tools. Plain Python, no Claude code here.
Every tool returns a SHORT string (token optimization).
Errors are raised as exceptions; each harness turns them into is_error."""
import html
import re
import urllib.request

from shared import memory_store, store


def add_application(company: str, role: str, url: str = "", status: str = "applied") -> str:
    a = store.add(company, role, url, status)
    return f"added #{a['id']} {a['company']} | {a['role']} | {a['status']}"


def update_status(company_or_id: str, status: str) -> str:
    a, old = store.set_status(company_or_id, status)
    return f"#{a['id']} {a['company']}: {old} -> {a['status']}"


def list_applications(status: str = "") -> str:
    apps = store.load()
    if status:
        apps = [a for a in apps if a["status"] == status]
    if not apps:
        return "no applications"
    return "\n".join(
        f"#{a['id']} {a['company']} | {a['role']} | {a['status']} | {a['updated']}" for a in apps
    )


def save_preference(key: str, value: str) -> str:
    old = memory_store.set_preference(key, value)
    if old is None:
        return f"saved {key}={value}"
    return f"updated {key}: '{old}' -> '{value}'"


def fetch_job_posting(url: str, max_chars: int = 1500) -> str:
    """External tool: downloads a job posting and returns its text, trimmed."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must start with http:// or https://")
    req = urllib.request.Request(url, headers={"User-Agent": "jobhunt-agent/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")
    raw = re.sub(r"(?is)<(script|style|nav|footer|header).*?</\1>", " ", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + " …[truncated]"
    return text or "page has no readable text"


def summary_line() -> str:
    """One line about the current state, for the context (not the full list)."""
    apps = store.load()
    if not apps:
        return "0 applications"
    counts: dict[str, int] = {}
    for a in apps:
        counts[a["status"]] = counts.get(a["status"], 0) + 1
    parts = ", ".join(f"{n} {s}" for s, n in counts.items())
    return f"{len(apps)} applications ({parts})"