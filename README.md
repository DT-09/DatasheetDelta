# DatasheetDelta

**Engineering specification revision comparison with source provenance and human review.**

DatasheetDelta compares two revisions of a supplier datasheet or engineering specification. It extracts recognizable label/value fields, records where each value was found, normalizes a conservative set of units, and produces a change register. Duplicate parameter labels are preserved and marked ambiguous rather than silently discarded.

## Capabilities

- CSV, XLSX, DOCX, text-based PDF, TXT and Markdown ingestion.
- Source locations by row, worksheet, table, paragraph, PDF page/line or text line.
- Label canonicalization for a small, explicit alias set.
- Conservative unit conversion for length, pressure, voltage, current, power, frequency, mass, capacitance, temperature, percentage and rotational speed.
- Added, removed, changed, unchanged, unit-mismatch and ambiguous classifications.
- JSON, CSV and evidence-rich PDF exports, command-line interface and FastAPI upload service.
- Browser workspace with filtering, reviewer decisions, reviewer notes and an annotated JSON review-package export.
- Per-file upload limit, extension allowlist, request-memory processing and non-root Docker runtime.

## Quick start

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[api,documents,reports,test]"
uvicorn datasheetdelta.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. API documentation is at /api/docs; health check is /api/health.

## CLI

```bash
datasheetdelta examples/reference.csv examples/revised.csv --out reports/revision
```

Creates JSON, CSV and PDF reports. Numeric tolerance is expressed in normalized base units where the dimensions are known:

```bash
datasheetdelta reference.csv revised.csv --tolerance 0.01 --out reports/revision
```

## API

- `GET /api/health`
- `POST /api/investigations` — multipart fields `reference`, `revised`, optional `tolerance`
- `POST /api/reports/json` — same multipart fields, returns JSON attachment
- `POST /api/reports/csv` — same multipart fields, returns CSV attachment
- `POST /api/reports/pdf` — same multipart fields, returns a paginated evidence report

The API accepts CSV, XLSX, DOCX, PDF, TXT and MD files up to 15 MB each. Invalid extensions, empty files and malformed documents return explicit HTTP errors.

## Comparison semantics

A parameter is compared only when its extracted label can be canonicalized. Supported numeric units are converted to a common base for their dimension. Fahrenheit is converted to Celsius for temperature comparison. If dimensions cannot be reconciled, the result is flagged for review rather than silently converted.

The tolerance is an absolute threshold in normalized base units. It is not a percentage tolerance. Parameters without a known dimension are compared conservatively.

Duplicate occurrences of a parameter are retained and marked `ambiguous`. A duplicate is not automatically paired by row order; the reviewer must inspect its source locations.

## Human review

The browser interface lets a reviewer mark a finding as confirmed, requiring investigation, not applicable or not reviewed, add a note, and provide a self-reported reviewer name. The exported review-package JSON includes the decisions, notes, reviewer name and export timestamp. These decisions are held in browser memory until exported. They are not stored on the server. A reviewer must preserve the exported package in the organization's approved document-control system.

## Extraction boundaries

This is deterministic label/value extraction, not a general-purpose engineering document understanding engine.

- Scanned PDFs require OCR; OCR is not included.
- Drawings, CAD, images, footnotes, multi-column reading order, complex merged tables and free-form layouts may not be extracted.
- XLSX formulas are read using cached values; a workbook without recalculated cached values may yield blanks.
- Label aliases and supported units are explicit and finite.
- Extraction completeness is not guaranteed. Absence of a finding does not prove that no other document change exists.

Always compare the result against the source documents. A difference is not automatically a defect, a safety issue or a non-compliance. DatasheetDelta does not calculate engineering impact, certify compliance, or replace qualified engineering approval.

## Data handling and deployment

The API processes uploaded file bytes in request memory and does not intentionally persist source documents. Reviewer decisions remain client-side until exported. Hosting providers, reverse proxies and platform logs may have their own retention policies; configure those separately. Do not upload confidential, personal, export-controlled or otherwise restricted documents unless the deployment has been approved for that data.

Run locally for private evaluation. For a container build:

```bash
docker build -t datasheetdelta .
docker run --rm -p 8000:8000 datasheetdelta
```

The container runs as a non-root user and includes a health check. Production deployment still requires TLS, access control, operational monitoring, backup policy for exported review records, dependency review and organization-specific security assessment.

## Development and tests

```bash
pip install -e ".[api,documents,reports,test]"
pytest -q
```

CI tests Python 3.10–3.13. The synthetic examples are test fixtures, not customer documents or validation evidence.

## Release status

This repository branch is an engineering candidate, not a claim of externally validated production readiness. Before a public 1.0 release, complete the acceptance gate in [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md), including realistic document corpus testing, security review, deployment verification and review by engineering users.

## License

MIT.
