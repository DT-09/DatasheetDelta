# DatasheetDelta

**Engineering change intelligence.** Compare supplier datasheets and engineering specifications. Review a traceable register of extracted changes and the source locations behind them.

> **Development status:** This repository is under active development. It is not a released or production-validated product. Do not treat this branch as DatasheetDelta 1.0.

## Product purpose

DatasheetDelta helps engineering, procurement and supplier-quality teams investigate revisions to technical documents. It extracts explicit parameter/value pairs, compares two revisions, preserves source locations and produces a reviewable change register.

It is an investigation aid, not an engineering decision-maker. A changed value is not automatically a defect, deviation, safety issue or non-compliance.

## Current development capabilities

- Deterministic extraction from CSV, XLSX, DOCX, text-based PDF, TXT and Markdown.
- Source provenance at row, worksheet, table, paragraph, PDF page/line or text line level.
- Two-column label/value rows and horizontal key/value pairs in tabular inputs.
- Duplicate parameter preservation; duplicate labels are classified as ambiguous instead of silently overwritten.
- Alias normalization for a small set of common engineering labels.
- Conservative unit conversion for common length, pressure, voltage, current, power, frequency, mass, temperature and percentage values.
- Added, removed, changed, unchanged, unit-mismatch and ambiguous classifications.
- JSON and CSV reports, CLI and FastAPI browser workspace.
- Optional authenticated SQLite persistence for extracted reports and reviewer decisions.
- Append-only review events linked by a SHA-256 hash chain, with integrity checks when an investigation is reopened.
- Explicit deletion of an investigation and its associated report and review history.

These capabilities are deliberately narrow. Do not infer support for arbitrary engineering document layouts.

## Local setup

Python 3.10 or newer:

    python -m venv .venv
    # Windows: .venv\\Scripts\\activate
    # macOS/Linux: source .venv/bin/activate
    pip install -e ".[all]"
    uvicorn datasheetdelta.api:app --reload

Open http://127.0.0.1:8000. API health is at /api/health; API documentation is at /api/docs.

Without DATASHEETDELTA_ACCESS_TOKEN, the app runs in development mode: comparisons and exports work, but investigations and review events are not saved. To enable persistence and the review ledger, configure a long random token and a database path:

    # macOS/Linux
    export DATASHEETDELTA_ACCESS_TOKEN="your-long-random-secret"
    export DATASHEETDELTA_DB="$PWD/data/datasheetdelta.sqlite3"

    # PowerShell
    $env:DATASHEETDELTA_ACCESS_TOKEN="your-long-random-secret"
    $env:DATASHEETDELTA_DB="$PWD/data/datasheetdelta.sqlite3"

Enter the same token in the browser workspace. It is sent as a bearer token and retained only in that browser tab's session storage. The token is required for comparisons, exports and review routes whenever configured.

The reviewer name is self-reported. The current shared-token model is suitable only for a trusted, single-operator deployment; it is not multi-user identity, role-based authorization or enterprise SSO.

## CLI

    datasheetdelta examples/reference.csv examples/revised.csv --out reports/revision
    datasheetdelta examples/reference.csv examples/revised.csv --tolerance 0.01 --out reports/revision

This writes JSON and CSV reports using the supplied output prefix.

## API

- GET /api/health
- POST /api/investigations (multipart fields: reference, revised, optional tolerance)
- GET /api/investigations/{id}
- POST /api/investigations/{id}/reviews
- DELETE /api/investigations/{id}
- POST /api/reports/json
- POST /api/reports/csv

Review decisions are confirmed_change, not_material or needs_follow_up. Each event records a reviewer-entered name, timestamp, note and parameter. Events are append-only through the application and hash-chained. This detects accidental or ordinary in-database edits; it is not cryptographic proof against a database administrator who can rewrite the database and recompute the chain. Deleting an investigation deletes its review history too.

The numeric tolerance is absolute and applies only to compatible numeric dimensions after normalization. It is not a percentage tolerance or an engineering acceptance threshold.

## Extraction boundaries

- Scanned PDFs are not OCR-processed.
- Complex multi-column layouts, merged cells, nested tables, footnotes, diagrams, handwritten marks and unusual reading orders may be missed.
- Extraction completeness is not guaranteed. Every finding must be checked against the source documents.
- Unit conversion is limited to the explicit conversion table in the code. Unsupported or incompatible units require manual review.
- Parameter matching is based on normalized labels and a small explicit alias map. It is not semantic engineering equivalence.

## Safety, privacy and security

DatasheetDelta does not determine engineering impact, certify compliance, establish product safety or replace qualified engineering approval. Never use its output as the sole basis for design, procurement, manufacturing or safety decisions.

Original uploaded documents are processed in request memory and are not stored by the application. When persistence is enabled, the extracted report, parameter values, source excerpts, filenames and review events are stored in SQLite. Protect the database and its backups as confidential engineering data. Deleting an investigation removes its report and review events. Hosting providers, reverse proxies and logs may have separate retention behavior.

Do not upload confidential, personal, export-controlled or otherwise restricted documents unless the deployment has been reviewed and approved for that data. Do not expose the development service to untrusted users. The shared bearer token is not a substitute for per-user authentication, authorization, rate limiting, parser sandboxing, malware scanning or deployment-level controls.

Only synthetic example files are included. No customer usage, accuracy rate, recovery, savings or validation result is claimed.

## Run tests

    pip install -e ".[all]"
    pytest

## Container

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the complete Docker Compose deployment, persistent-volume backup and Cloudflare hosting boundary. Cloudflare Pages alone cannot run the Python API or SQLite review ledger.


## Release policy

The project will receive one public 1.0 release only after the release gate in [docs/RELEASE_GATE.md](docs/RELEASE_GATE.md) is satisfied. Development commits and CI runs are not public product releases.

## License

MIT.
