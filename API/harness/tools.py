"""Tool schemas (JSON) + dispatch. Errors go back to the model as is_error."""
from shared import tools_impl

FILE = "tools.py"


def log(msg: str) -> None:
    print(f"[{FILE}] {msg}")


TOOLS = [
    {
        "name": "add_application",
        "description": "Add a new job application to the tracker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "role": {"type": "string"},
                "url": {"type": "string", "description": "Link to the job posting (optional)"},
                "status": {
                    "type": "string",
                    "enum": ["saved", "applied", "interview", "offer", "rejected"],
                },
            },
            "required": ["company", "role"],
        },
    },
    {
        "name": "update_status",
        "description": "Change the status of an existing application, by company name or #id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_or_id": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["saved", "applied", "interview", "offer", "rejected"],
                },
            },
            "required": ["company_or_id", "status"],
        },
    },
    {
        "name": "list_applications",
        "description": "List applications in a compact format. Optionally filter by status.",
        "input_schema": {
            "type": "object",
            "properties": {"status": {"type": "string"}},
        },
    },
    {
        "name": "save_preference",
        "description": "Save a long-term user preference or decision (survives between sessions). "
        "Returns the previous value if one existed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "e.g. work_mode, min_salary, location"},
                "value": {"type": "string"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "fetch_job_posting",
        "description": "Download a job posting from the internet and return its text (trimmed).",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
]

_FUNCS = {
    "add_application": tools_impl.add_application,
    "update_status": tools_impl.update_status,
    "list_applications": tools_impl.list_applications,
    "save_preference": tools_impl.save_preference,
    "fetch_job_posting": tools_impl.fetch_job_posting,
}


def dispatch(tool_use_id: str, name: str, args: dict) -> dict:
    """Runs one tool and returns a tool_result block. Never raises."""
    log(f"dispatch {name}({args})")
    func = _FUNCS.get(name)
    if func is None:
        log(f"unknown tool {name}")
        return {"type": "tool_result", "tool_use_id": tool_use_id,
                "content": f"unknown tool '{name}'", "is_error": True}
    try:
        result = func(**args)
        return {"type": "tool_result", "tool_use_id": tool_use_id, "content": result}
    except Exception as e:  # the error goes back to the model, not to the user
        log(f"{name} failed: {e}")
        return {"type": "tool_result", "tool_use_id": tool_use_id,
                "content": f"{type(e).__name__}: {e}", "is_error": True}