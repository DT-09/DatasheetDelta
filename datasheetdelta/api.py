from __future__ import annotations

import json
import math
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .core import compare, extract, report_csv

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".docx", ".pdf", ".txt", ".md"}
WEB_DIRECTORY = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(
    title="DatasheetDelta",
    version="0.1.0-dev",
    description=(
        "Deterministic engineering-document revision comparison. "
        "Findings require qualified human review and are not engineering approval."
    ),
    docs_url="/api/docs",
    redoc_url=None,
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "product": "DatasheetDelta", "mode": "development"}


async def read_doc(upload: UploadFile) -> tuple[str, list, list[str]]:
    filename = Path(upload.filename or "document").name
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type. Accepted: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
        )
    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail=f"{filename} is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Maximum file size is 15 MB per document.")
    try:
        fields, warnings = extract(filename, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Parser/library errors are returned as a safe client error; internals stay in server logs.
        raise HTTPException(
            status_code=422,
            detail=f"{filename} could not be parsed. Check that it is a valid, supported document.",
        ) from exc
    return filename, fields, warnings


def validate_tolerance(tolerance: float) -> None:
    if not math.isfinite(tolerance) or tolerance < 0:
        raise HTTPException(status_code=422, detail="Tolerance must be a finite, non-negative number.")


async def build_result(reference: UploadFile, revised: UploadFile, tolerance: float) -> dict:
    validate_tolerance(tolerance)
    reference_name, reference_fields, reference_warnings = await read_doc(reference)
    revised_name, revised_fields, revised_warnings = await read_doc(revised)
    result = compare(
        reference_name, reference_fields, revised_name, revised_fields, tolerance
    )
    result["warnings"] = reference_warnings + revised_warnings
    return result


@app.post("/api/investigations")
async def investigate(
    reference: UploadFile = File(...),
    revised: UploadFile = File(...),
    tolerance: float = Form(0.0),
) -> dict:
    return await build_result(reference, revised, tolerance)


@app.post("/api/reports/{kind}")
async def export_report(
    kind: str,
    reference: UploadFile = File(...),
    revised: UploadFile = File(...),
    tolerance: float = Form(0.0),
) -> Response:
    if kind not in {"json", "csv"}:
        raise HTTPException(status_code=404, detail="Report format must be json or csv.")
    result = await build_result(reference, revised, tolerance)
    if kind == "json":
        body = json.dumps(result, indent=2, ensure_ascii=False)
        media_type = "application/json"
    else:
        body = report_csv(result)
        media_type = "text/csv; charset=utf-8"
    return Response(
        body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="datasheetdelta.{kind}"'},
    )


app.mount("/", StaticFiles(directory=str(WEB_DIRECTORY), html=True), name="web")
