# DatasheetDelta

**Engineering change intelligence.** Compare supplier datasheets and engineering specifications, then review a traceable register of what changed and where each extracted value came from.

## Included in this release
- Deterministic label/value extraction from CSV, XLSX, DOCX, text-based PDF, TXT and Markdown.
- Source provenance by row, sheet, table, paragraph, page or line.
- Conservative normalization for common length, pressure, voltage, current, power, frequency, mass, temperature and percentage units.
- Added, removed, changed, unchanged and ambiguous-unit classifications.
- JSON and CSV exports; CLI; optional FastAPI upload service; responsive browser workspace.
- Dockerfile and synthetic sample documents.

## Run locally
Python 3.10+.

    python -m venv .venv
    # Windows: .venv\\Scripts\\activate
    # macOS/Linux: source .venv/bin/activate
    pip install -e ".[api,documents,test]"
    uvicorn datasheetdelta.api:app --reload

Serve the static interface from the web directory with a same-origin reverse proxy that routes /api to the FastAPI service. The UI expects /api/investigations. API health: /api/health.

## CLI
    datasheetdelta examples/reference.csv examples/revised.csv --out reports/revision

Creates JSON and CSV reports. API routes: POST /api/investigations; POST /api/reports/json; POST /api/reports/csv; GET /api/health.

## Extraction contract and limitations
The first release targets explicit two-column label/value tables or Label: value text. Scanned PDFs require OCR, which is not included. Complex layouts, merged cells, footnotes, multi-column tables and ambiguous labels may be missed. Only a conservative set of units is normalized. Check extracted fields against source documents before relying on a comparison.

A difference is not automatically a defect or safety issue. DatasheetDelta does not determine engineering impact, certify compliance, or replace qualified engineering approval. Uploads are processed in request memory and are not persisted by this application. Do not upload confidential or export-controlled documents to an unapproved deployment. Sample CSVs are synthetic, not customer data or validation evidence.

## Tests
    pip install -e ".[documents,test]"
    pytest

## Deployment
Build the API container with Dockerfile and deploy to a Python container host. Serve web/ as static assets and route /api/* to the API. No live deployment, customer integration or external storage is claimed.

## License
MIT.
