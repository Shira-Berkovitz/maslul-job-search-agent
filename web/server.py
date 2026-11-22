"""Web app for the job-search agent (FastAPI).
Run from the project folder:
    python web/server.py
then open http://127.0.0.1:8000
Needs ANTHROPIC_API_KEY in the same terminal. Data is kept in data_web/
(separate from data/, which every scenario run wipes)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("JOBHUNT_DATA_DIR", str(ROOT / "data_web"))

try:
    import truststore
    truststore.inject_into_ssl()  # Windows certificate store (needed behind NetFree)
except ImportError:
    pass

import anthropic  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from web.service import JobHuntService  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
service = JobHuntService(anthropic.Anthropic, model=os.environ.get("JOBHUNT_MODEL", "claude-opus-5-5"))
app = FastAPI(title="Maslul – job search agent")


class ChatIn(BaseModel):
    message: str


class MoveIn(BaseModel):
    status: str


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/state")
def get_state():
    return service.state()


@app.get("/api/history")
def get_history():
    return service.history()


@app.post("/api/chat")
def chat(body: ChatIn):
    try:
        return service.chat(body.message)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except anthropic.AuthenticationError:
        raise HTTPException(502, "המפתח ל-API חסר או לא תקין. הגדירי ANTHROPIC_API_KEY בטרמינל והפעילי את השרת מחדש.")
    except anthropic.APIConnectionError:
        raise HTTPException(502, "אין חיבור לשרת של Anthropic. בדקי את החיבור לאינטרנט ואת הסינון.")
    except anthropic.APIStatusError as e:
        raise HTTPException(502, f"המודל החזיר שגיאה ({e.status_code}). נסי שוב בעוד רגע.")


@app.patch("/api/applications/{app_id}")
def move(app_id: int, body: MoveIn):
    try:
        return service.move(app_id, body.status)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.post("/api/reset")
def reset():
    return service.reset()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8765"))
    print(f"Open http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port)
