from __future__ import annotations

import csv
import io
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

@dataclass(frozen=True)
class Field:
    name: str
    value: str
    number: float | None
    unit: str | None
    dimension: str | None
    source: str
    excerpt: str

@dataclass(frozen=True)
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
    "ip code": "ingress_protection", "weight": "mass", "frequency": "frequency",
}
UNITS = {
    "mm": ("length", 1.0), "cm": ("length", 10.0), "m": ("length", 1000.0),
    "in": ("length", 25.4), "inch": ("length", 25.4), "inches": ("length", 25.4),
    "pa": ("pressure", 1.0), "kpa": ("pressure", 1_000.0),
    "mpa": ("pressure", 1_000_000.0), "bar": ("pressure", 100_000.0),
    "psi": ("pressure", 6894.757293), "v": ("voltage", 1.0),
    "mv": ("voltage", .001), "kv": ("voltage", 1000.0),
    "a": ("current", 1.0), "ma": ("current", .001),
    "w": ("power", 1.0), "kw": ("power", 1000.0),
    "hz": ("frequency", 1.0), "khz": ("frequency", 1000.0),
    "mhz": ("frequency", 1_000_000.0), "kg": ("mass", 1.0),
    "g": ("mass", .001), "mg": ("mass", .000001),
    "°c": ("temperature", 1.0), "c": ("temperature", 1.0),
    "°f": ("temperature_f", 1.0), "f": ("temperature_f", 1.0),
    "%": ("percentage", 1.0), "rpm": ("rotational_speed", 1.0),
}
NUMBER = re.compile(r"^\s*([-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|[-+]?\.\d+)\s*([A-Za-z°%µμ/²³._-]+)?\s*$")
HEADER_LABELS = {"parameter", "field", "property", "specification", "characteristic", "item", "description"}
HEADER_VALUES = {"value", "values", "description", "specification value", "unit", "units"}

def canonical_name(label: str) -> str:
    clean = re.sub(r"\s+", " ", label.strip().lower()).strip(" :")
    return ALIASES.get(clean, re.sub(r"[^a-z0-9]+", "_", clean).strip("_"))

def _field(label: object, value: object, source: str, excerpt: str) -> Field | None:
    if label is None or value is None:
        return None
    raw_label, raw_value = str(label).strip(), str(value).strip()
    if not raw_label or not raw_value:
        return None
    if raw_label.lower() in HEADER_LABELS and raw_value.lower() in HEADER_VALUES:
        return None
    name = canonical_name(raw_label)
    if not name:
        return None
    match = NUMBER.match(raw_value)
    if not match:
        return Field(name, raw_value, None, None, None, source, excerpt[:500])
    number = float(match.group(1).replace(",", ""))
    unit = match.group(2)
    normalized_unit = (unit or "").lower().replace("μ", "µ")
    spec = UNITS.get(normalized_unit)
    if spec:
        dimension, factor = spec
        if dimension == "temperature_f":
            number = (number - 32.0) * 5.0 / 9.0
            dimension = "temperature"
        else:
            number *= factor
        return Field(name, raw_value, number, unit, dimension, source, excerpt[:500])
    return Field(name, raw_value, number, unit, None, source, excerpt[:500])

def _add(fields: list[Field], label: object, value: object, source: str, excerpt: str) -> None:
    item = _field(label, value, source, excerpt)
    if item:
        fields.append(item)

def _pairs_from_rows(rows: Iterable[tuple], prefix: str, fields: list[Field]) -> None:
    for row_no, row in enumerate(rows, 1):
        cells = list(row)
        values = ["" if value is None else str(value).strip() for value in cells]
        values = [value for value in values]
        if len(values) < 2:
            continue
        # Support ordinary two-column tables and repeated label/value pairs.
        for offset in range(0, len(values) - 1, 2):
            label, value = values[offset], values[offset + 1]
            if label and value:
                source = f"{prefix}row {row_no}" if prefix.endswith("!") else f"{prefix}row {row_no}"
                _add(fields, label, value, source, f"{label}: {value}")

def extract(filename: str, content: bytes) -> tuple[list[Field], list[str]]:
    ext = Path(filename).suffix.lower()
    fields: list[Field] = []
    warnings: list[str] = []
    if not content:
        raise ValueError("The document is empty.")
    if ext == ".csv":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("CSV must be UTF-8 encoded.") from exc
        rows = list(csv.reader(io.StringIO(text)))
        _pairs_from_rows(rows, "", fields)
    elif ext in {".txt", ".md"}:
        try:
            lines = content.decode("utf-8-sig").splitlines()
        except UnicodeDecodeError as exc:
            raise ValueError("Text documents must be UTF-8 encoded.") from exc
        for line_no, line in enumerate(lines, 1):
            match = re.match(r"^\s*([^:=]{1,120}?)\s*[:=]\s*(.*?)\s*$", line)
            if match:
                _add(fields, match.group(1), match.group(2), f"line {line_no}", line)
            else:
                parts = re.split(r"\s{2,}", line.strip())
                if len(parts) == 2:
                    _add(fields, parts[0], parts[1], f"line {line_no}", line)
    elif ext == ".xlsx":
        try:
            import openpyxl
        except ImportError as exc:
            raise ValueError("Install spreadsheet support: pip install 'datasheetdelta[documents]'.") from exc
        try:
            workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
            for sheet in workbook.worksheets:
                _pairs_from_rows(sheet.iter_rows(values_only=True), f"{sheet.title}!", fields)
            workbook.close()
        except Exception as exc:
            raise ValueError(f"Could not read XLSX document: {exc}") from exc
    elif ext == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise ValueError("Install Word document support: pip install 'datasheetdelta[documents]'.") from exc
        try:
            document = Document(io.BytesIO(content))
            for table_no, table in enumerate(document.tables, 1):
                _pairs_from_rows(([cell.text for cell in row.cells] for row in table.rows), f"table {table_no}, ", fields)
            for paragraph_no, paragraph in enumerate(document.paragraphs, 1):
                match = re.match(r"^\s*([^:=]{1,120}?)\s*[:=]\s*(.*?)\s*$", paragraph.text)
                if match:
                    _add(fields, match.group(1), match.group(2), f"paragraph {paragraph_no}", paragraph.text)
        except Exception as exc:
            raise ValueError(f"Could not read DOCX document: {exc}") from exc
    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("Install PDF support: pip install 'datasheetdelta[documents]'.") from exc
        try:
            reader = PdfReader(io.BytesIO(content), strict=False)
            if reader.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported. Export an unlocked copy.")
            for page_no, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                for line_no, line in enumerate(text.splitlines(), 1):
                    match = re.match(r"^\s*([^:=]{1,120}?)\s*[:=]\s*(.*?)\s*$", line)
                    if match:
                        _add(fields, match.group(1), match.group(2), f"page {page_no}, line {line_no}", line)
                    else:
                        parts = re.split(r"\s{2,}", line.strip())
                        if len(parts) == 2:
                            _add(fields, parts[0], parts[1], f"page {page_no}, line {line_no}", line)
            if not fields:
                warnings.append("No extractable text fields found. This may be a scanned PDF; OCR is not enabled.")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Could not read PDF document: {exc}") from exc
    else:
        raise ValueError("Supported formats: CSV, XLSX, DOCX, text PDF, TXT and MD.")
    counts = Counter(field.name for field in fields)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    if duplicates:
        warnings.append("Repeated parameter labels were preserved and flagged for review: " + ", ".join(duplicates))
    if not fields:
        warnings.append(f"No label/value fields were extracted from {filename}. Use a two-column table or Label: value lines.")
    return fields, warnings

def _group(fields: list[Field]) -> dict[str, list[Field]]:
    result: dict[str, list[Field]] = defaultdict(list)
    for field in fields:
        result[field.name].append(field)
    return result

def compare(reference_name: str, old: list[Field], revised_name: str, new: list[Field], tolerance: float = 0.0) -> dict:
    if tolerance < 0:
        raise ValueError("Tolerance must be non-negative.")
    a, b = _group(old), _group(new)
    findings: list[Finding] = []
    for key in sorted(a.keys() | b.keys()):
        left, right = a.get(key, []), b.get(key, [])
        if len(left) > 1 or len(right) > 1:
            findings.append(Finding(key, "ambiguous", " | ".join(x.value for x in left) or None,
                " | ".join(x.value for x in right) or None,
                " | ".join(x.source for x in left) or None,
                " | ".join(x.source for x in right) or None,
                "Duplicate parameter labels prevent a safe one-to-one comparison. Review every source occurrence."))
            continue
        x, y = (left[0] if left else None), (right[0] if right else None)
        if x is None:
            status, explanation = "added", "Field appears only in the revised document."
        elif y is None:
            status, explanation = "removed", "Field appears only in the reference document."
        elif x.value == y.value:
            status, explanation = "unchanged", "Extracted values are textually identical."
        elif x.number is not None and y.number is not None:
            if x.dimension and y.dimension and x.dimension == y.dimension:
                delta = abs(x.number - y.number)
                status = "unchanged" if delta <= tolerance else "changed"
                explanation = f"Compared after conversion to the common {x.dimension} base unit; absolute difference {delta:.6g}."
            elif x.unit and y.unit and x.unit.lower() != y.unit.lower():
                status, explanation = "unit_mismatch", "Units are missing, unknown or dimensionally incompatible; manual review required."
            else:
                status, explanation = "changed", "Numeric value differs; unit equivalence could not be established."
        else:
            status, explanation = "changed", "Text or value differs; assess engineering materiality."
        findings.append(Finding(key, status, x.value if x else None, y.value if y else None,
            x.source if x else None, y.source if y else None, explanation))
    return {
        "schema_version": "1.0",
        "reference_file": reference_name,
        "revised_file": revised_name,
        "findings": [asdict(item) for item in findings],
        "warnings": [],
        "review_required": True,
        "method": "deterministic label/value extraction and comparison",
        "limitations": [
            "Extraction is limited to recognizable label/value structures.",
            "A missing finding does not prove that no other document change exists.",
            "Engineering impact, compliance and safety significance are not inferred."
        ],
    }

def report_csv(result: dict) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["parameter", "status", "reference", "revised", "reference_source", "revised_source", "explanation"])
    for finding in result["findings"]:
        writer.writerow([finding[key] for key in ("parameter", "status", "reference", "revised", "reference_source", "revised_source", "explanation")])
    return stream.getvalue()
