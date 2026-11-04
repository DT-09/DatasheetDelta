from __future__ import annotations

import hmac
import json
import math
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .core import compare, extract, report_csv
from . import store

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".docx", ".pdf", ".txt", ".md"}
PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
WEB_DIRECTORY = PROJECT_DIRECTORY / "web"
EXAMPLES_DIRECTORY = PROJECT_DIRECTORY / "examples"

app = FastAPI(
    title="DatasheetDelta",
    version="0.1.0-dev",
    description=(
        "Deterministic engineering-document revision comparison. "
        "Findings require qualified human review and are not engineering approval."
    ),
    docs_url=None,
    redoc_url=None,
)


class ReviewInput(BaseModel):
    parameter: str = Field(min_length=1, max_length=200)
    decision: Literal["confirmed_change", "not_material", "needs_follow_up"]
    reviewer: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=4000)


def check_access(authorization: str | None, *, review: bool = False) -> bool:
    expected = os.getenv("DATASHEETDELTA_ACCESS_TOKEN", "")
    if review and not expected:
        raise HTTPException(
            status_code=503,
            detail="Review storage is disabled. Configure DATASHEETDELTA_ACCESS_TOKEN first.",
        )
    if expected:
        scheme, separator, supplied = (authorization or "").partition(" ")
        if (
            not separator
            or scheme.lower() != "bearer"
            or not hmac.compare_digest(supplied.encode('utf-8'), expected.encode('utf-8'))
        ):
            raise HTTPException(status_code=401, detail="A valid bearer access token is required.")
        return True
    return False



@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
        "base-uri 'self'; frame-ancestors 'none'"
    )
    return response

@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "product": "DatasheetDelta",
        "mode": "protected" if os.getenv("DATASHEETDELTA_ACCESS_TOKEN") else "development",
        "access_token_required": bool(os.getenv("DATASHEETDELTA_ACCESS_TOKEN")),
    }


async def read_doc(upload: UploadFile) -> tuple[str, list, list[str]]:
    raw_name = (upload.filename or "document").replace("\\", "/")
    filename = Path(raw_name).name
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
        raise HTTPException(
            status_code=422,
            detail=f"{filename} could not be parsed. Check that it is a valid, supported document.",
        ) from exc
    return filename, fields, warnings


def parse_tolerances(raw: str) -> dict[str, float]:
    try:
        tolerances = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Tolerances must be valid JSON.") from exc
    if not isinstance(tolerances, dict):
        raise HTTPException(status_code=422, detail="Tolerances must be a JSON object.")
    return tolerances


async def build_result(
    reference: UploadFile,
    revised: UploadFile,
    tolerances_json: str,
) -> dict:
    tolerances = parse_tolerances(tolerances_json)
    reference_name, reference_fields, reference_warnings = await read_doc(reference)
    revised_name, revised_fields, revised_warnings = await read_doc(revised)
    try:
        result = compare(
            reference_name, reference_fields, revised_name, revised_fields, tolerances
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result["warnings"] = reference_warnings + revised_warnings
    return result


@app.post("/api/investigations")
async def investigate(
    reference: UploadFile = File(...),
    revised: UploadFile = File(...),
    tolerances: str = Form("{}"),
    authorization: str | None = Header(default=None),
) -> dict:
    access_enabled = check_access(authorization)
    result = await build_result(reference, revised, tolerances)
    result["review_enabled"] = access_enabled
    if access_enabled:
        metadata = store.save_investigation(result)
        result.update(metadata)
    return result


@app.get("/api/investigations/{investigation_id}")
def read_investigation(
    investigation_id: str,
    authorization: str | None = Header(default=None),
) -> dict:
    check_access(authorization, review=True)
    record = store.get_investigation(investigation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    return record


@app.post("/api/investigations/{investigation_id}/reviews")
def create_review(
    investigation_id: str,
    payload: ReviewInput,
    authorization: str | None = Header(default=None),
) -> dict:
    check_access(authorization, review=True)
    try:
        event = store.add_review(
            investigation_id,
            payload.parameter,
            payload.decision,
            payload.reviewer,
            payload.note,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record = store.get_investigation(investigation_id)
    return {
        "event": event,
        "review_chain_valid": record["review_chain_valid"] if record else False,
    }


@app.delete("/api/investigations/{investigation_id}")
def remove_investigation(
    investigation_id: str,
    authorization: str | None = Header(default=None),
) -> dict:
    check_access(authorization, review=True)
    if not store.delete_investigation(investigation_id):
        raise HTTPException(status_code=404, detail="Investigation not found.")
    return {"deleted": True, "investigation_id": investigation_id}


@app.post("/api/reports/{kind}")
async def export_report(
    kind: str,
    reference: UploadFile = File(...),
    revised: UploadFile = File(...),
    tolerance: float = Form(0.0),
    authorization: str | None = Header(default=None),
) -> Response:
    check_access(authorization)
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


app.mount("/examples", StaticFiles(directory=str(EXAMPLES_DIRECTORY)), name="examples")
app.mount("/", StaticFiles(directory=str(WEB_DIRECTORY), html=True), name="web")
