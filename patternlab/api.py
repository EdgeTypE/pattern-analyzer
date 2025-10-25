"""FastAPI-based minimal REST API for PatternLab.

Accepts file uploads or base64 payloads at /analyze and returns job ids.
/report/{job_id} returns result.

This module also mounts a self-hosted static UI under /ui and provides a root
redirect so visiting http://localhost:8000 opens the UI.
"""
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import base64
import uuid
import asyncio
from .engine import Engine
import os

app = FastAPI(title="PatternLab API")
engine = Engine()

# Allow the self-hosted UI to call the API from the same host during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Mount static UI at /ui (serve index.html and assets)
_static_dir = os.path.join(os.path.dirname(__file__), "static_ui")
app.mount("/ui", StaticFiles(directory=_static_dir, html=True), name="ui")

# Redirect root to the UI for convenience
@app.get("/", include_in_schema=False)
async def _root_redirect():
    return RedirectResponse(url="/ui/")

# Also handle common legacy/documentation path "/pattern-analyzer/" by redirecting
# users to the self-hosted UI so visiting the server root shows the app rather
# than the docs site when both are present on the same host.
@app.get("/pattern-analyzer/", include_in_schema=False)
async def _legacy_pattern_analyzer_redirect():
    return RedirectResponse(url="/ui/")

# In-memory jobs store. For production use persistent storage.
jobs: Dict[str, Dict[str, Any]] = {}

class AnalyzePayload(BaseModel):
    base64_data: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

async def _run_analysis(job_id: str, data_bytes: bytes, config: Optional[Dict[str, Any]]):
    jobs[job_id] = {"status": "running", "result": None, "error": None}
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, engine.analyze, data_bytes, config or {})
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = result
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)

@app.post("/analyze")
async def analyze(background_tasks: BackgroundTasks, payload: Optional[AnalyzePayload] = Body(None), file: UploadFile = File(None)):
    """Start an analysis job. Accepts either multipart file upload (form) or JSON body with base64_data."""
    data_bytes = None
    config = {}
    if file is not None:
        data_bytes = await file.read()
    elif payload is not None and payload.base64_data:
        try:
            data_bytes = base64.b64decode(payload.base64_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"invalid_base64:{e}")
        config = payload.config or {}
    else:
        raise HTTPException(status_code=400, detail="no_input_provided: provide file or base64_data")

    job_id = uuid.uuid4().hex
    jobs[job_id] = {"status": "pending", "result": None, "error": None}
    background_tasks.add_task(_run_analysis, job_id, data_bytes, config)
    return {"job_id": job_id, "status": "pending", "report_url": f"/report/{job_id}"}

@app.get("/report/{job_id}")
async def report(job_id: str):
    """Fetch job status and result. Returns JSON report when job completed."""
    entry = jobs.get(job_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    if entry["status"] == "completed":
        return {"job_id": job_id, "status": "completed", "report": entry["result"]}
    if entry["status"] in ("running", "pending"):
        return {"job_id": job_id, "status": entry["status"]}
    return {"job_id": job_id, "status": "error", "error": entry.get("error")}

@app.get("/artefact", include_in_schema=False)
async def artefact(path: str):
    """
    Serve an artefact file by absolute path (development helper).
    Security: only allows files inside the current workspace directory to be served.
    Usage: /artefact?path=/absolute/path/to/file.png
    """
    # Resolve and restrict to workspace root for safety
    file_path = os.path.abspath(path)
    workspace_root = os.path.abspath(os.getcwd())
    if not file_path.startswith(workspace_root):
        raise HTTPException(status_code=403, detail="forbidden: path outside workspace")
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="not_found")
    return FileResponse(file_path)

@app.get("/health")
async def health():
    return {"status": "ok"}