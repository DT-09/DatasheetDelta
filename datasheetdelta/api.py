from __future__ import annotations

import json
import math
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .core import compare, extract, report_csv
from .reports import report_pdf

MAX_FILE_BYTES = 15 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".docx", ".pdf", ".txt", ".md"}
BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="DatasheetDelta",
    version="0.2.0-dev",
    description="Evidence-led comparison of engineering specification revisions. Human review remains mandatory.",
    docs_url="/api/docs",
    redoc_url=None,
)

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "product": "DatasheetDelta", "version": "0.2.0-dev"}

async def read_document(upload: UploadFile) -> tuple[str, list, list[str]]:
    filename = Path(upload.filename or "document").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}.")
    content = await upload.read(MAX_FILE_BYTES + 1)
    await upload.close()
    if not content:
        raise HTTPException(status_code=400, detail=f"{filename} is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=f"{filename} exceeds the 15 MB per-file limit.")
    try:
        fields, warnings = extract(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process {filename}: {type(exc).__name__}.") from exc
    return filename, fields, warnings

async def build_result(reference: UploadFile, revised: UploadFile, tolerance: float) -> dict:
    if not math.isfinite(tolerance) or tolerance < 0:
        raise HTTPException(status_code=422, detail="Tolerance must be a finite, non-negative number.")
    reference_name, reference_fields, reference_warnings = await read_document(reference)
    revised_name, revised_fields, revised_warnings = await read_document(revised)
    result = compare(reference_name, reference_fields, revised_name, revised_fields, tolerance)
    result["warnings"] = reference_warnings + revised_warnings
    result["tolerance"] = {"value": tolerance, "basis": "normalized base units where dimensions are known"}
    return result

@app.post("/api/investigations")
async def investigate(
    reference: UploadFile = File(...),
    revised: UploadFile = File(...),
    tolerance: float = Form(0),
) -> dict:
    return await build_result(reference, revised, tolerance)

@app.post("/api/reports/{kind}")
async def export_report(
    kind: str,
    reference: UploadFile = File(...),
    revised: UploadFile = File(...),
    tolerance: float = Form(0),
) -> Response:
    if kind not in {"json", "csv", "pdf"}:
        raise HTTPException(status_code=404, detail="Available report formats: json, csv, pdf.")
    result = await build_result(reference, revised, tolerance)
    try:
        body = (json.dumps(result, indent=2, ensure_ascii=False) if kind == "json"
                else report_csv(result) if kind == "csv" else report_pdf(result))
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    media_type = {"json": "application/json; charset=utf-8", "csv": "text/csv; charset=utf-8", "pdf": "application/pdf"}[kind]
    return Response(body, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="datasheetdelta-report.{kind}"'})

if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
