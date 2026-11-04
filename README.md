# DatasheetDelta

**Engineering revision intelligence.** Compare two technical document revisions, preserve source provenance, and produce an evidence-linked change register for qualified engineering review.

DatasheetDelta is an evidence-gathering tool. It does **not** decide whether a change is safe, material, compliant, or acceptable.

## Product workflow

1. Upload a reference and revised document.
2. Extract supported label/value fields.
3. Normalize a conservative set of units to canonical base units.
4. Classify fields as added, removed, changed, unchanged, or unit mismatch.
5. Inspect original values, source locations, warnings, and comparison explanations.
6. Search and filter findings, then export JSON or CSV for engineering review.

## Supported inputs and limits

| Format | Supported extraction |
|---|---|
| CSV | First two columns as label and value |
| XLSX | First two columns per row, across worksheets |
| DOCX | Two-cell table rows and Label: value paragraphs |
| Text PDF | Extractable Label: value lines |
| TXT / Markdown | Label: value lines |

Scanned PDFs require OCR; OCR is not included. Complex multi-column layouts, merged tables, footnotes, graphics, images, and implicit relationships may not be extracted. Duplicate normalized labels are reported as warnings; only the first occurrence is included in the comparison register. Review every source occurrence.

## Architecture

- **Website:** static HTML, CSS and JavaScript in `web/`, deployable to Cloudflare Pages.
- **Analysis API:** Python 3.10+ and FastAPI in `datasheetdelta/`, deployable as a separate web service.
- **Local mode:** FastAPI serves the website and API from one origin.
- **Production mode:** the Pages website calls `https://datasheetdelta-api.onrender.com` by default. If the API service uses another hostname, set `window.DATASHEETDELTA_API` before `app.js` in `web/index.html`.

The API allows CORS from `https://datasheetdelta.pages.dev` by default. Set `CORS_ORIGINS` to a comma-separated allowlist when deploying another front-end origin.

## Deploy

### 1. Deploy the API

Use the repository's `render.yaml` blueprint to create the Python web service. It installs the API and document parser dependencies, starts Uvicorn, and checks `/api/health`. The expected service hostname is `https://datasheetdelta-api.onrender.com`.

If the hosting provider assigns a different hostname, update `API_BASE` in `web/app.js` or set `window.DATASHEETDELTA_API` in the HTML before the app script.

### 2. Deploy the website

Deploy the `web/` directory to the existing Cloudflare Pages project. The website and API are separate deployments; a successful Pages deployment alone does not mean document analysis is online.

### 3. Verify production

- Open `https://datasheetdelta-api.onrender.com/api/health` and confirm JSON status `ok`.
- Open `https://datasheetdelta.pages.dev` and confirm the analysis-service indicator reports online.
- Run the included sample to inspect the report UI (the sample is synthetic).
- Upload two small, non-confidential CSV fixtures and verify source rows, findings, filters, and both exports.
- Confirm unsupported formats and files over 15 MB are rejected.

## Run locally

~~~bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[api,documents,test]"
uvicorn datasheetdelta.api:app --reload
~~~

Open http://127.0.0.1:8000. API health: http://127.0.0.1:8000/api/health.

## CLI

~~~bash
datasheetdelta examples/reference.csv examples/revised.csv --out reports/revision
~~~

Creates JSON and CSV reports.

## API

- `GET /api/health`
- `POST /api/investigations` — multipart fields `reference`, `revised`, optional `tolerance`
- `POST /api/reports/json` — same inputs; downloads JSON
- `POST /api/reports/csv` — same inputs; downloads CSV

Maximum upload size: 15 MB per file. Files are processed in request memory and are not persisted by this application. Deploy behind HTTPS, restrict access as required by your organization, and obtain approval before uploading confidential, export-controlled, or otherwise restricted material. Do not assume a public demo deployment is an approved document-processing environment.

## Unit handling

Supported dimensions include length, pressure, voltage, current, power, frequency, mass, temperature, and percentage. Values are converted once to canonical base units for comparison. Original values and units remain in the report.

The optional numeric tolerance is an **absolute tolerance in canonical base units**. It is not a percentage tolerance. One tolerance applied across unlike dimensions is a convenience, not an engineering policy. For mixed-dimension reviews, keep tolerance at zero and assess values individually.

## Validation

~~~bash
pip install -e ".[api,documents,test]"
pytest
~~~

The test suite covers source provenance, equivalent-unit comparisons, numeric changes, incompatible dimensions, unknown units, duplicate labels, summary counts, tolerance validation, text extraction, API health, multipart investigations, upload rejection, and CSV export.

## Product boundaries

- Extracted values may be incomplete or wrong; verify them against original documents.
- A detected difference is not automatically a defect, safety issue, supplier breach, or cost impact.
- No compliance certification, engineering sign-off, or automated materiality assessment.
- No OCR, authentication, persistent storage, audit log, or approval workflow.
- Sample values are synthetic, not customer evidence or performance validation.

## License

MIT.
