"""SDK version of the tools: @tool + create_sdk_mcp_server.
The domain code itself is in shared/ (the same code the API version uses)."""
from claude_agent_sdk import create_sdk_mcp_server, tool

from shared import memory_store, tools_impl
from shared.paths import data_dir

FILE = "tools.py"
SERVER = "jobs"
STATUS = {"type": "string", "enum": ["saved", "applied", "interview", "offer", "rejected"]}


def log(msg: str) -> None:
    print(f"[SDK/{FILE}] {msg}")


def workspace():
    """The folder Claude Code runs in (cwd). Its CLAUDE.md is the memory."""
    d = data_dir() / "sdk_workspace"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_claude_md() -> None:  # replaces: memory.py
    prefs = memory_store.load()["preferences"]  # replaces: memory.py
    lines = ["# Job search memory", "", "Saved user preferences (from earlier sessions):"]  # replaces: memory.py
    lines += [f"- {k}: {v}" for k, v in prefs.items()] or ["- (none yet)"]  # replaces: memory.py
    (workspace() / "CLAUDE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")  # replaces: memory.py
    log(f"CLAUDE.md updated ({len(prefs)} preference(s))")


def _run(name: str, func, args: dict) -> dict:  # replaces: tools.py
    log(f"tool {name}({args})")
    try:  # replaces: tools.py
        return {"content": [{"type": "text", "text": func(**args)}]}  # replaces: tools.py
    except Exception as e:  # replaces: tools.py
        log(f"{name} failed: {e}")
        return {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}],  # replaces: tools.py
                "is_error": True}  # replaces: tools.py


@tool("add_application", "Add a new job application to the tracker.", {  # replaces: tools.py
    "type": "object",
    "properties": {"company": {"type": "string"}, "role": {"type": "string"},
                   "url": {"type": "string"}, "status": STATUS},
    "required": ["company", "role"]})
async def add_application(args):
    return _run("add_application", tools_impl.add_application, args)


@tool("update_status", "Change the status of an existing application, by company name or #id.", {  # replaces: tools.py
    "type": "object",
    "properties": {"company_or_id": {"type": "string"}, "status": STATUS},
    "required": ["company_or_id", "status"]})
async def update_status(args):
    return _run("update_status", tools_impl.update_status, args)


@tool("list_applications", "List applications in a compact format. Optionally filter by status.", {  # replaces: tools.py
    "type": "object", "properties": {"status": {"type": "string"}}})
async def list_applications(args):
    return _run("list_applications", tools_impl.list_applications, args)


@tool("save_preference", "Save a long-term user preference or decision (survives between "  # replaces: tools.py
      "sessions). Returns the previous value if one existed.", {
    "type": "object",
    "properties": {"key": {"type": "string"}, "value": {"type": "string"}},
    "required": ["key", "value"]})
async def save_preference(args):
    result = _run("save_preference", tools_impl.save_preference, args)
    if not result.get("is_error"):
        write_claude_md()  # replaces: memory.py
    return result


@tool("fetch_job_posting", "Download a job posting from the internet and return its text (trimmed).", {  # replaces: tools.py
    "type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]})
async def fetch_job_posting(args):
    return _run("fetch_job_posting", tools_impl.fetch_job_posting, args)


ALL_TOOLS = [add_application, update_status, list_applications, save_preference,
             fetch_job_posting]
server = create_sdk_mcp_server(name=SERVER, tools=ALL_TOOLS)  # replaces: tools.py
ALLOWED_TOOLS = [f"mcp__{SERVER}__{t.name}" for t in ALL_TOOLS]  # replaces: tools.py