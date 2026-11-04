# DatasheetDelta

**Engineering change intelligence.** Compare supplier datasheets and engineering specifications. Review a traceable register of extracted changes and the source locations behind them.

> **Development status:** This repository is under active development. It is not a released or production-validated product. Do not treat the current branch as DatasheetDelta 1.0.

## Product purpose

DatasheetDelta is designed to help engineering, procurement and supplier-quality teams investigate revisions to technical documents. It extracts explicit parameter/value pairs, compares the two revisions, preserves source locations and produces a reviewable change register.

It is an investigation aid, not an engineering decision-maker. A changed value is not automatically a defect, deviation, safety issue or non-compliance.

## Current development capabilities

- Deterministic extraction from CSV, XLSX, DOCX, text-based PDF, TXT and Markdown.
- Source provenance at row, worksheet, table, paragraph, PDF page/line or text line level.
- Two-column label/value rows and horizontal key/value pairs in tabular inputs.
- Duplicate parameter preservation; duplicate labels are classified as ambiguous instead of silently overwritten.
- Alias normalization for a small set of common engineering labels.
- Conservative unit conversion for common length, pressure, voltage, current, power, frequency, mass, temperature and percentage values.
- Added, removed, changed, unchanged, unit-mismatch and ambiguous classifications.
- JSON and CSV reports, command-line interface and optional FastAPI browser workspace.
- Upload size/type checks and in-memory request processing; this application does not persist uploaded documents.

These capabilities are deliberately narrow. Do not infer support for arbitrary engineering document layouts.

## Local setup

Python 3.10 or newer:

    python -m venv .venv
    # Windows: .venv\Scripts\activate
    # macOS/Linux: source .venv/bin/activate
    pip install -e ".[all]"
    uvicorn datasheetdelta.api:app --reload

Open http://127.0.0.1:8000. API health is available at /api/health; interactive API documentation is at /api/docs.

## CLI

    datasheetdelta examples/reference.csv examples/revised.csv --out reports/revision

This writes JSON and CSV reports using the supplied output prefix.

## API

- GET /api/health
- POST /api/investigations (multipart fields: reference, revised, optional tolerance)
- POST /api/reports/json
- POST /api/reports/csv

The numeric tolerance is absolute and applies only to compatible numeric dimensions after normalization. It is not a percentage tolerance or an engineering acceptance threshold.

## Extraction boundaries

- Scanned PDFs are not OCR-processed.
- Complex multi-column layouts, merged cells, nested tables, footnotes, diagrams, handwritten marks and unusual reading orders may be missed.
- Extraction completeness is not guaranteed. Every finding must be checked against the source documents.
- Unit conversion is limited to the explicit conversion table in the code. Unsupported or incompatible units require manual review.
- Parameter matching is based on normalized labels and a small explicit alias map. It is not semantic engineering equivalence.
- The current implementation does not provide a persistent review/approval workflow, multi-user collaboration, enterprise identity, customer integrations or a validated audit system.

## Safety, privacy and security

DatasheetDelta does not determine engineering impact, certify compliance, establish product safety or replace qualified engineering approval. Never use its output as the sole basis for design, procurement, manufacturing or safety decisions.

The API processes each upload in request memory and does not intentionally store source documents. Hosting providers, reverse proxies and logs may have their own retention behavior. Do not upload confidential, personal, export-controlled or otherwise restricted documents unless the deployment has been reviewed and approved for that data.

Only synthetic example files are included. No customer usage, accuracy rate, recovery, savings or validation result is claimed.

## Run tests

    pip install -e ".[all]"
    pytest

## Container

    docker build -t datasheetdelta .
    docker run --rm -p 8000:8000 datasheetdelta

The container serves the browser workspace and API from one process. Review the deployment's network controls, TLS termination, upload limits and logging policy before exposing it publicly.

## Release policy

The project will receive one public 1.0 release only after the release gate in [docs/RELEASE_GATE.md](docs/RELEASE_GATE.md) is satisfied. Development commits and CI runs are not public product releases.

## License

MIT.
