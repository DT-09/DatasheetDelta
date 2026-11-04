# DatasheetDelta

**Engineering change intelligence for technical document revisions.**

DatasheetDelta compares two revisions of a supplier datasheet or engineering specification. It extracts supported label/value fields, preserves source locations, normalizes a conservative set of units, and produces a reviewable change register.

It is an evidence-gathering tool. It does **not** decide whether a change is safe, material, compliant, or acceptable.

## Product workflow

1. Upload a reference and revised document.
2. Extract explicit label/value pairs from supported structures.
3. Normalize supported numeric units to canonical base units.
4. Classify fields as added, removed, changed, unchanged, or unit mismatch.
5. Inspect original values, source locations, warnings, and comparison explanations.
6. Export the register as JSON or CSV for qualified engineering review.

## Supported inputs

| Format | Supported extraction |
|---|---|
| CSV | First two columns as label and value |
| XLSX | First two populated columns per row, across worksheets |
| DOCX | Two-cell table rows and Label: value paragraphs |
| Text PDF | Extractable Label: value lines |
| TXT / Markdown | Label: value lines |

Scanned PDFs require OCR. OCR is not included. Complex multi-column layouts, merged tables, footnotes, graphics, images, and implicit relationships may not be extracted. Duplicate normalized labels are reported as warnings; only the first occurrence is included in the comparison register. Review every source occurrence.

## Unit handling

Supported dimensions include length, pressure, voltage, current, power, frequency, mass, temperature, and percentage. Values are converted once to canonical base units for comparison. Original values and units remain in the report.

The optional numeric tolerance is an **absolute tolerance in canonical base units**. It is not a percentage tolerance and should be set deliberately for the parameter being reviewed. One tolerance value applied across unlike dimensions is a convenience, not an engineering policy. For mixed-dimension reviews, keep tolerance at zero and assess values individually.

Unknown or incompatible units are marked unit_mismatch; the engine does not guess conversions. Text values are compared conservatively after trimming and case-folding.

## Run locally

Python 3.10+.

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

Creates reports/revision.json and reports/revision.csv.

## API

- GET /api/health
- POST /api/investigations — multipart fields reference, revised, optional tolerance
- POST /api/reports/json — same inputs; downloads JSON
- POST /api/reports/csv — same inputs; downloads CSV

Maximum upload size: 15 MB per file. Files are read into request memory and are not persisted by this application. Deploy behind HTTPS, apply access controls appropriate to your organization, and obtain approval before uploading confidential, export-controlled, or otherwise restricted material. Do not assume a public demo deployment is an approved document-processing environment.

## Validation

~~~bash
pip install -e ".[documents,test]"
pytest
~~~

Tests cover extraction provenance, equivalent-unit comparisons, numeric changes, incompatible dimensions, unknown units, duplicate labels, summary counts, tolerance validation, and text extraction.

## Deployment

The Dockerfile builds the FastAPI service and static workspace:

~~~bash
docker build -t datasheetdelta .
docker run --rm -p 8000:8000 datasheetdelta
~~~

No customer integrations, persistent storage, OCR, authentication, audit log, or engineering approval workflow are included. These are explicit product boundaries, not implied capabilities.

## Engineering and commercial boundaries

- Extracted values may be incomplete or wrong; verify them against original documents.
- A detected difference is not automatically a defect, safety issue, supplier breach, or cost impact.
- No compliance certification, engineering sign-off, or automated materiality assessment is provided.
- Sample files are synthetic and are not customer evidence or performance validation.

## License

MIT.
