import json
import os
from pathlib import Path

import google.auth
import google.auth.transport.requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests

app = FastAPI(title="Book Concierge Agent Frontend")

# Load configuration defaults
ROOT_DIR = Path(__file__).resolve().parent.parent

# Read default resource name from deployment_metadata.json if available
DEFAULT_RESOURCE_NAME = "projects/600540399751/locations/us-east1/reasoningEngines/3830810661357617152"
metadata_file = ROOT_DIR / "deployment_metadata.json"
if metadata_file.exists():
    try:
        with open(metadata_file, "r") as f:
            data = json.load(f)
            if "remote_agent_runtime_id" in data:
                DEFAULT_RESOURCE_NAME = data["remote_agent_runtime_id"]
    except Exception:
        pass

AGENT_ENGINE_RESOURCE_NAME = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME", DEFAULT_RESOURCE_NAME
)
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")

# Determine GCP location from resource name (e.g. projects/.../locations/us-east1/...)
location = "us-east1"
if "locations/" in AGENT_ENGINE_RESOURCE_NAME:
    location = AGENT_ENGINE_RESOURCE_NAME.split("locations/")[1].split("/")[0]

SERVICE_URL = f"https://{location}-aiplatform.googleapis.com/v1/{AGENT_ENGINE_RESOURCE_NAME}"


# Use remote Reasoning Engine service by default, unless USE_LOCAL_AGENT is set to true
USE_LOCAL_AGENT = os.environ.get("USE_LOCAL_AGENT", "false").lower() == "true"

try:
    if USE_LOCAL_AGENT:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
        from app.agent import root_agent

        local_session_service = InMemorySessionService()
        local_runner = Runner(agent=root_agent, app_name="app", session_service=local_session_service)
        HAS_LOCAL_AGENT = True
    else:
        HAS_LOCAL_AGENT = False
except Exception as e:
    print(f"Warning: Local agent runner init failed: {e}")
    HAS_LOCAL_AGENT = False


def get_auth_headers() -> dict[str, str]:
    """Obtains fresh GCP authentication headers."""
    try:
        credentials, _ = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        return {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        }
    except Exception:
        return {"Content-Type": "application/json"}


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str = "web-user"


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "agent_engine_resource_name": AGENT_ENGINE_RESOURCE_NAME,
        "agent_directory": AGENT_DIRECTORY,
        "has_local_agent": HAS_LOCAL_AGENT,
    }


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session_id = req.session_id

    # Stream via Local ADK Runner if available
    if HAS_LOCAL_AGENT:
        if not session_id:
            try:
                session = await local_runner.session_service.create_session(app_name="app", user_id=req.user_id)
                session_id = session.id
            except Exception:
                session_id = f"session_{os.urandom(4).hex()}"

        async def local_sse_generator():
            yield f"data: {json.dumps({'session_id': session_id, 'type': 'metadata'})}\n\n"
            msg_content = types.Content(
                parts=[types.Part.from_text(text=req.message)],
                role="user"
            )
            try:
                async for event in local_runner.run_async(
                    user_id=req.user_id,
                    session_id=session_id,
                    new_message=msg_content
                ):
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                yield f"data: {json.dumps({'text': part.text})}\n\n"
            except Exception as ex:
                yield f"data: {json.dumps({'error': str(ex)})}\n\n"

        return StreamingResponse(local_sse_generator(), media_type="text/event-stream")

    # Fallback to Remote Reasoning Engine query
    headers = get_auth_headers()
    if not session_id:
        create_resp = requests.post(
            f"{SERVICE_URL}:query",
            headers=headers,
            json={
                "class_method": "async_create_session",
                "input": {"user_id": req.user_id},
            },
            timeout=30,
        )
        if not create_resp.ok:
            raise HTTPException(
                status_code=create_resp.status_code,
                detail=f"Session creation failed: {create_resp.text}",
            )
        session_id = create_resp.json().get("output", {}).get("id")
        if not session_id:
            raise HTTPException(status_code=500, detail="No session ID returned")

    stream_payload = {
        "class_method": "async_stream_query",
        "input": {
            "user_id": req.user_id,
            "session_id": session_id,
            "message": req.message,
        },
    }

    def sse_generator():
        yield f"data: {json.dumps({'session_id': session_id, 'type': 'metadata'})}\n\n"
        resp = requests.post(
            f"{SERVICE_URL}:streamQuery",
            headers=headers,
            json=stream_payload,
            stream=True,
            timeout=120,
        )

        if not resp.ok:
            err_msg = json.dumps({"error": f"Agent query failed: {resp.text}"})
            yield f"data: {err_msg}\n\n"
            return

        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                chunk = json.loads(line)
                yield f"data: {json.dumps(chunk)}\n\n"
            except Exception:
                yield f"data: {json.dumps({'text': line})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


# Mount static directory
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def read_root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        with open(index_path, "r") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Book Concierge Agent Frontend</h1>")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)



