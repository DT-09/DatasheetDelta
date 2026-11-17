from pathlib import Path
import json
import math
import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .core import compare, extract, report_csv

VERSION = "1.2.0"
MAX_FILE_BYTES = 15 * 1024 * 1024
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".docx", ".pdf", ".txt", ".md"}

app = FastAPI(
    title="DatasheetDelta",
    version=VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

origins = [
    item.strip().rstrip("/")
    for item in os.getenv(
        "CORS_ORIGINS",
        "https://datasheetdelta.pages.dev,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

@app.middleware("http")
async def private_response_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
    return response

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "product": "DatasheetDelta",
        "version": VERSION,
        "max_file_bytes": MAX_FILE_BYTES,
        "storage": "ephemeral",
    }

async def read_document(upload: UploadFile):
    name = (upload.filename or "document").replace("\\", "/").split("/")[-1]
    if len(name) > 180:
        raise HTTPException(400, "File name is too long.")
    if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Unsupported document format.")
    content = await upload.read(MAX_FILE_BYTES + 1)
    if not content:
        raise HTTPException(400, f"{name} is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, f"{name} exceeds the 15 MB per-file limit.")
    try:
        fields, warnings = extract(name, content)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return name, fields, warnings

async def build_report(reference: UploadFile, revised: UploadFile, tolerance: float):
    if not math.isfinite(tolerance) or tolerance < 0:
        raise HTTPException(422, "Tolerance must be a finite, non-negative number.")
    reference_name, reference_fields, reference_warnings = await read_document(reference)
    revised_name, revised_fields, revised_warnings = await read_document(revised)
    result = compare(reference_name, reference_fields, revised_name, revised_fields, tolerance)
    result["warnings"] = reference_warnings + revised_warnings
    result["processing"] = {
        "persistence": "none",
        "extraction": "best-effort label/value parsing",
        "review_required": True,
    }
    return result

@app.post("/api/investigations")
async def investigate(
    reference: UploadFile = File(...),
    revised: UploadFile = File(...),
    tolerance: float = Form(0),
):
    return await build_report(reference, revised, tolerance)

@app.post("/api/reports/{kind}")
async def export_report(
    kind: str,
    reference: UploadFile = File(...),
    revised: UploadFile = File(...),
    tolerance: float = Form(0),
):
    if kind not in {"json", "csv"}:
        raise HTTPException(404, "Use /api/reports/json or /api/reports/csv.")
    result = await build_report(reference, revised, tolerance)
    body = json.dumps(result, indent=2) if kind == "json" else report_csv(result)
    media_type = "application/json" if kind == "json" else "text/csv"
    return Response(
        body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="datasheetdelta.{kind}"'},
    )

app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
