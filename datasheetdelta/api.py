from pathlib import Path
import json
import math
import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .core import compare, extract, report_csv

app = FastAPI(title="DatasheetDelta", version="1.1.0")
MAX_FILE_BYTES = 15 * 1024 * 1024
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

origins = [
    item.strip()
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

@app.get("/api/health")
def health():
    return {"status": "ok", "product": "DatasheetDelta", "version": app.version}

async def read_document(upload: UploadFile):
    name = upload.filename or "document"
    if Path(name).suffix.lower() not in {".csv", ".xlsx", ".docx", ".pdf", ".txt", ".md"}:
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
    return result

@app.post("/api/investigations")
async def investigate(reference: UploadFile = File(...), revised: UploadFile = File(...),
                      tolerance: float = Form(0)):
    return await build_report(reference, revised, tolerance)

@app.post("/api/reports/{kind}")
async def export_report(kind: str, reference: UploadFile = File(...), revised: UploadFile = File(...),
                        tolerance: float = Form(0)):
    if kind not in {"json", "csv"}:
        raise HTTPException(404, "Use /api/reports/json or /api/reports/csv.")
    result = await build_report(reference, revised, tolerance)
    body = json.dumps(result, indent=2) if kind == "json" else report_csv(result)
    media_type = "application/json" if kind == "json" else "text/csv"
    return Response(body, media_type=media_type,
                    headers={"Content-Disposition": f"attachment; filename=datasheetdelta.{kind}"})

app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
