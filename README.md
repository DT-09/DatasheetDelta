# DatasheetDelta

**Engineering revision intelligence.** Compare two technical document revisions, preserve source provenance, and produce an evidence-linked change register for qualified engineering review.

DatasheetDelta is deliberately conservative. It identifies candidate differences in supported label/value fields. It does **not** decide whether a change is safe, material, compliant, contractually acceptable, or suitable for a particular application.

## What it does

1. Accept a reference revision and a revised document.
2. Extract supported label/value fields and retain their source locations.
3. Normalize supported physical units to canonical units.
4. Classify each parameter as added, removed, changed, unchanged, or unit mismatch.
5. Surface duplicate-field and extraction warnings.
6. Search and filter the resulting register.
7. Export the findings as JSON or CSV, or use the local CLI.

## Supported inputs

| Format | Supported extraction | Provenance |
|---|---|---|
| CSV | First two columns as label and value | Row |
| XLSX | First two columns per row, across worksheets | Sheet and row |
| DOCX | Two-cell table rows and `Label: value` paragraphs | Table/row or paragraph |
| Text PDF | Extractable `Label: value` lines | Page and line |
| TXT / Markdown | `Label: value` lines | Line |

This is structured-field extraction, not general document understanding. Scanned PDFs require OCR; OCR is not included. Complex multi-column layouts, merged tables, footnotes, graphics, images, formulas without cached values, and implicit relationships may not be extracted. Duplicate normalized labels are reported; only the first occurrence enters the current comparison register. Review every occurrence in the source.

## Comparison method

- Labels are normalized conservatively; a small alias map handles common engineering terms.
- Supported units are converted once to canonical units before numeric comparison.
- Temperature supports Celsius and Fahrenheit.
- Different physical dimensions are never compared as if they were the same quantity.
- Unknown or incompatible units are flagged for manual review.
- Text values are compared case-insensitively after trimming surrounding whitespace.
- The tolerance is an **absolute tolerance in canonical base units**, not a percentage.
- The same tolerance is applied across dimensions. For mixed-dimension reviews, keep it at zero and assess findings individually.

A numeric difference is not an engineering severity score. The product does not infer risk, criticality, compliance, safety, or cost impact.

## Architecture

- **Web application:** static HTML, CSS and JavaScript in `web/`.
- **Analysis API:** Python 3.10+ and FastAPI in `datasheetdelta/`.
- **Local mode:** FastAPI serves the web application and API from one origin.
- **Hosted mode:** deploy `web/` to Cloudflare Pages and the API as a separate Python service.
- **CLI:** run comparisons locally without the hosted API.

The browser defaults to `https://datasheetdelta-api.onrender.com`. Set `window.DATASHEETDELTA_API` before loading `app.js` in `web/index.html` if the API uses another hostname.

The API's default CORS allowlist includes `https://datasheetdelta.pages.dev`, `http://localhost:8000`, and `http://127.0.0.1:8000`. Set `CORS_ORIGINS` to a comma-separated allowlist for your deployment. Do not use a wildcard for a private deployment.

## Run locally

~~~bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[api,documents,test]"
uvicorn datasheetdelta.api:app --reload
~~~

Open http://127.0.0.1:8000. Health check: http://127.0.0.1:8000/api/health.

## CLI

~~~bash
datasheetdelta examples/reference.csv examples/revised.csv --out reports/revision
~~~

Creates `reports/revision.json` and `reports/revision.csv`. Tolerance is optional:

~~~bash
datasheetdelta examples/reference.csv examples/revised.csv --tolerance 0 --out reports/revision
~~~

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Service status and processing limits |
| POST | `/api/investigations` | Return a JSON comparison report |
| POST | `/api/reports/json` | Download JSON report |
| POST | `/api/reports/csv` | Download CSV register |

Multipart fields are `reference`, `revised`, and optional `tolerance`. The tolerance must be finite and non-negative.

### Processing limits

- 15 MB maximum per uploaded file.
- 100 MB maximum expanded Office archive size.
- 2,000 maximum archive entries.
- 200:1 maximum per-entry compression ratio.
- 500 maximum PDF pages.
- 20,000 maximum extracted fields per document.

Files are processed in request memory and are not persisted by the application. API responses are marked `Cache-Control: no-store`. These controls reduce avoidable exposure; they are not a substitute for deployment-level access control, isolation, monitoring, or a security review.

## Deployment

### API service

The repository includes a Render blueprint in `render.yaml`.

1. Create the service from the repository blueprint.
2. Confirm the build installs `.[api,documents]`.
3. Set `CORS_ORIGINS` to the exact production web origin.
4. Confirm the service health check at `/api/health`.
5. Confirm the deployed version reports `1.2.0`.

The blueprint currently uses the free service plan. Expect cold starts and limited operational guarantees. It is suitable for evaluation, not a production commitment for confidential engineering records.

### Web application

Deploy the `web/` directory to the existing Cloudflare Pages project. The web application and analysis API are separate deployments. A successful Pages build does not prove that the API is online.

### Release verification

- Run the complete test suite.
- Confirm the API health check and CORS origin.
- Upload non-confidential test fixtures in each supported format.
- Verify findings against the source rows, sheets, pages, and paragraphs.
- Test malformed files, unsupported extensions, oversized uploads, and exports.
- Confirm the browser shows the API as online.
- Do not upload confidential, export-controlled, personal, or otherwise restricted documents to a public demo without organizational approval and an approved processing environment.

## Validation

~~~bash
pip install -e ".[api,documents,test]"
pytest
~~~

The test suite covers extraction provenance, unit normalization, temperature conversion, incompatible and unknown units, duplicate labels, summary counts, malformed Office archives, API health, CORS, upload rejection, and CSV export.

## Product boundaries

- Extraction may be incomplete or incorrect; verify every finding against the original document.
- A detected difference is not automatically a defect, safety issue, supplier breach, or cost impact.
- No OCR, authentication, persistent storage, audit log, approval workflow, or engineering sign-off.
- No compliance certification or automated materiality assessment.
- Synthetic examples are not customer evidence or performance validation.

## License

MIT.
