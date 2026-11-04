from __future__ import annotations
import csv, io, math, re
from dataclasses import asdict, dataclass
from pathlib import Path

@dataclass
class Field:
    name: str
    value: str
    number: float | None
    unit: str | None
    source: str
    excerpt: str
    dimension: str | None = None
    base_unit: str | None = None

@dataclass
class Finding:
    parameter: str
    status: str
    reference: str | None
    revised: str | None
    reference_source: str | None
    revised_source: str | None
    explanation: str

ALIASES = {
    "max pressure": "maximum_pressure", "maximum pressure": "maximum_pressure",
    "operating pressure": "operating_pressure", "rated voltage": "rated_voltage",
    "max temperature": "maximum_temperature", "maximum temperature": "maximum_temperature",
    "operating temperature": "operating_temperature", "ip rating": "ingress_protection",
}
# Factors convert source units once to canonical base units.
UNITS = {
    "mm": ("length", 1.0, "mm"), "cm": ("length", 10.0, "mm"),
    "m": ("length", 1000.0, "mm"), "in": ("length", 25.4, "mm"),
    "inch": ("length", 25.4, "mm"), "inches": ("length", 25.4, "mm"),
    "pa": ("pressure", 1.0, "Pa"), "kpa": ("pressure", 1000.0, "Pa"),
    "mpa": ("pressure", 1_000_000.0, "Pa"), "bar": ("pressure", 100_000.0, "Pa"),
    "psi": ("pressure", 6894.757293, "Pa"),
    "v": ("voltage", 1.0, "V"), "mv": ("voltage", .001, "V"), "kv": ("voltage", 1000.0, "V"),
    "a": ("current", 1.0, "A"), "ma": ("current", .001, "A"),
    "w": ("power", 1.0, "W"), "kw": ("power", 1000.0, "W"),
    "hz": ("frequency", 1.0, "Hz"), "khz": ("frequency", 1000.0, "Hz"),
    "mhz": ("frequency", 1_000_000.0, "Hz"),
    "kg": ("mass", 1.0, "kg"), "g": ("mass", .001, "kg"),
    "°c": ("temperature", 1.0, "°C"), "c": ("temperature", 1.0, "°C"),
    "%": ("percentage", 1.0, "%"),
}
NUMBER = re.compile(r"^\s*([-+]?(?:\d{1,3}(?:,\d{3})+|\d+)?(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*([^\d\s].*?)?\s*$")

def _normalise_name(label: str) -> str:
    label = re.sub(r"\s+", " ", label.strip().lower()).rstrip(":")
    return ALIASES.get(label, re.sub(r"[^a-z0-9]+", "_", label).strip("_"))

def _field(label, value, source, excerpt):
    name = _normalise_name(str(label or ""))
    value = str(value or "").strip()
    if not name or not value:
        return None
    if name == "parameter" and value.casefold() in {"value", "description", "specification value"}:
        return None
    match = NUMBER.match(value)
    if not match or not match.group(1):
        return Field(name, value, None, None, source, excerpt)
    try:
        number = float(match.group(1).replace(",", ""))
    except ValueError:
        return Field(name, value, None, None, source, excerpt)
    if not math.isfinite(number):
        return Field(name, value, None, None, source, excerpt)
    unit = (match.group(2) or "").strip()
    info = UNITS.get(unit.casefold())
    if info:
        dimension, factor, base_unit = info
        return Field(name, value, number * factor, unit, source, excerpt, dimension, base_unit)
    return Field(name, value, number, unit or None, source, excerpt)

def extract(filename: str, content: bytes):
    ext = Path(filename).suffix.lower()
    fields, warnings = [], []
    def add(label, value, location, excerpt):
        field = _field(label, value, location, excerpt)
        if field:
            fields.append(field)
    if ext == ".csv":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("CSV must be UTF-8 encoded.") from exc
        for index, row in enumerate(csv.reader(io.StringIO(text)), 1):
            if len(row) >= 2:
                add(row[0], row[1], f"row {index}", f"{row[0]}: {row[1]}")
    elif ext in {".txt", ".md"}:
        try:
            lines = content.decode("utf-8-sig").splitlines()
        except UnicodeDecodeError as exc:
            raise ValueError(f"{ext[1:].upper()} must be UTF-8 encoded.") from exc
        for index, line in enumerate(lines, 1):
            if ":" in line:
                label, value = line.split(":", 1)
                add(label, value, f"line {index}", line)
    elif ext == ".xlsx":
        try:
            import openpyxl
        except ImportError as exc:
            raise ValueError("Install document support: pip install 'datasheetdelta[documents]'") from exc
        workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
        for sheet in workbook.worksheets:
            for index, row in enumerate(sheet.iter_rows(values_only=True), 1):
                if len(row) >= 2 and row[0] is not None and row[1] is not None:
                    add(row[0], row[1], f"{sheet.title}!row {index}", f"{row[0]}: {row[1]}")
    elif ext == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise ValueError("Install document support: pip install 'datasheetdelta[documents]'") from exc
        document = Document(io.BytesIO(content))
        for table_index, table in enumerate(document.tables, 1):
            for row_index, row in enumerate(table.rows, 1):
                if len(row.cells) >= 2:
                    add(row.cells[0].text, row.cells[1].text, f"table {table_index}, row {row_index}",
                        f"{row.cells[0].text}: {row.cells[1].text}")
        for index, paragraph in enumerate(document.paragraphs, 1):
            if ":" in paragraph.text:
                label, value = paragraph.text.split(":", 1)
                add(label, value, f"paragraph {index}", paragraph.text)
    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("Install document support: pip install 'datasheetdelta[documents]'") from exc
        reader = PdfReader(io.BytesIO(content))
        for page_index, page in enumerate(reader.pages, 1):
            for line_index, line in enumerate((page.extract_text() or "").splitlines(), 1):
                if ":" in line:
                    label, value = line.split(":", 1)
                    add(label, value, f"page {page_index}, line {line_index}", line)
        if not fields:
            warnings.append("No text fields found. Scanned PDFs need OCR; OCR is not included.")
    else:
        raise ValueError("Supported formats: CSV, XLSX, DOCX, text PDF, TXT and MD.")
    grouped = {}
    for field in fields:
        grouped.setdefault(field.name, []).append(field)
    unique = []
    for name, candidates in grouped.items():
        if len(candidates) > 1:
            locations = ", ".join(item.source for item in candidates[:5])
            warnings.append(f"Duplicate field '{name}' at {locations}. Only the first occurrence is compared; review all source occurrences.")
        unique.append(candidates[0])
    if not unique:
        warnings.append(f"No label/value fields extracted from {filename}. Use a two-column table or Label: value lines.")
    return unique, warnings

def compare(reference_name, old, revised_name, new, tolerance=0):
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Tolerance must be a finite, non-negative number in canonical base units.")
    reference, revised = {item.name: item for item in old}, {item.name: item for item in new}
    findings = []
    for key in sorted(reference.keys() | revised.keys()):
        before, after = reference.get(key), revised.get(key)
        if before is None:
            status, explanation = "added", "Field appears only in revised document."
        elif after is None:
            status, explanation = "removed", "Field appears only in reference document."
        elif before.value.strip().casefold() == after.value.strip().casefold():
            status, explanation = "unchanged", "Extracted values are identical."
        elif before.number is not None and after.number is not None:
            if before.dimension and after.dimension:
                if before.dimension != after.dimension:
                    status, explanation = "unit_mismatch", "Values use incompatible physical dimensions; manual review required."
                else:
                    status = "unchanged" if abs(before.number - after.number) <= tolerance else "changed"
                    explanation = f"Compared in {before.base_unit}; tolerance is {tolerance:g} {before.base_unit}."
            elif (before.unit or "").casefold() == (after.unit or "").casefold():
                status = "unchanged" if abs(before.number - after.number) <= tolerance else "changed"
                explanation = "Numeric values use the same unclassified unit."
            else:
                status, explanation = "unit_mismatch", "Units are unknown or not comparable; manual review required."
        else:
            status, explanation = "changed", "Text or value differs; assess engineering materiality."
        findings.append(asdict(Finding(key, status, before.value if before else None,
            after.value if after else None, before.source if before else None,
            after.source if after else None, explanation)))
    counts = {status: sum(1 for item in findings if item["status"] == status)
              for status in ("changed", "added", "removed", "unchanged", "unit_mismatch")}
    return {"reference_file": reference_name, "revised_file": revised_name, "findings": findings,
        "summary": {"total": len(findings), **counts, "review_required": True},
        "warnings": [], "review_required": True, "method": "deterministic label/value comparison",
        "tolerance_base_units": tolerance}

def report_csv(result):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["parameter", "status", "reference", "revised", "reference_source",
        "revised_source", "explanation"])
    for finding in result["findings"]:
        writer.writerow([finding[key] for key in ("parameter", "status", "reference", "revised",
            "reference_source", "revised_source", "explanation")])
    return stream.getvalue()
