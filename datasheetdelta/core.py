from __future__ import annotations

import csv
import io
import math
import re
import zipfile
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ALIASES = {
    "max pressure": "maximum_pressure",
    "maximum pressure": "maximum_pressure",
    "operating pressure": "operating_pressure",
    "rated voltage": "rated_voltage",
    "max temperature": "maximum_temperature",
    "maximum temperature": "maximum_temperature",
    "operating temperature": "operating_temperature",
    "ip rating": "ingress_protection",
}
UNITS = {
    "mm": ("length", 1.0), "cm": ("length", 10.0),
    "um": ("length", 0.001), "µm": ("length", 0.001), "μm": ("length", 0.001),
    "m": ("length", 1000.0), "in": ("length", 25.4),
    "inch": ("length", 25.4), "pa": ("pressure", 1.0),
    "kpa": ("pressure", 1000.0), "mpa": ("pressure", 1_000_000.0),
    "bar": ("pressure", 100_000.0), "psi": ("pressure", 6894.757293),
    "v": ("voltage", 1.0), "mv": ("voltage", 0.001),
    "kv": ("voltage", 1000.0), "a": ("current", 1.0),
    "ma": ("current", 0.001), "w": ("power", 1.0),
    "kw": ("power", 1000.0), "hz": ("frequency", 1.0),
    "khz": ("frequency", 1000.0), "mhz": ("frequency", 1_000_000.0),
    "kg": ("mass", 1.0), "g": ("mass", 0.001),
    "°c": ("temperature", 1.0), "degc": ("temperature", 1.0),
    "°f": ("temperature_f", 1.0), "degf": ("temperature_f", 1.0),
    "k": ("temperature_k", 1.0),
    "%": ("percentage", 1.0),
}
NUMBER = re.compile(
    r"^\s*([-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*"
    r"([A-Za-z°%µμ/²³._-]+)?\s*$"
)
HEADER_LABELS = {"parameter", "field", "property", "specification", "name", "item"}
HEADER_VALUES = {"value", "description", "specification value", "current value"}


@dataclass
class Field:
    name: str
    value: str
    number: float | None
    unit: str | None
    dimension: str | None
    source: str
    excerpt: str


@dataclass
class Finding:
    parameter: str
    status: str
    reference: str | None
    revised: str | None
    reference_source: str | None
    revised_source: str | None
    explanation: str


def _normalise_label(label: str) -> str:
    cleaned = re.sub(r"\s+", " ", label.strip().lower()).rstrip(":")
    return ALIASES.get(cleaned, re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_"))


def _field(label: str, value: str, source: str, excerpt: str) -> Field | None:
    if not label.strip() or not value.strip():
        return None
    clean_label = re.sub(r"\s+", " ", label.strip().lower()).rstrip(":")
    clean_value = value.strip()
    if clean_label in HEADER_LABELS and clean_value.lower() in HEADER_VALUES:
        return None
    name = _normalise_label(label)
    if not name:
        return None
    match = NUMBER.match(clean_value)
    if not match:
        return Field(name, clean_value, None, None, None, source, excerpt)
    number = float(match.group(1).replace(",", ""))
    unit = match.group(2)
    unit_key = (unit or "").lower()
    unit_info = UNITS.get(unit_key)
    if unit_info:
        dimension, factor = unit_info
        if dimension == "temperature_f":
            return Field(name, clean_value, (number - 32.0) * 5.0 / 9.0, unit, "temperature", source, excerpt)
        if dimension == "temperature_k":
            return Field(name, clean_value, number - 273.15, unit, "temperature", source, excerpt)
        return Field(name, clean_value, number * factor, unit, dimension, source, excerpt)
    return Field(name, clean_value, number, unit, "unknown" if unit else None, source, excerpt)


def _add(fields: list[Field], label: object, value: object, source: str, excerpt: str) -> None:
    field = _field(str(label or ""), str(value or ""), source, excerpt)
    if field:
        fields.append(field)


def _extract_pairs(rows: Iterable[tuple], fields: list[Field], prefix: str) -> None:
    header: tuple[int, int, int | None] | None = None
    for row_number, row in enumerate(rows, 1):
        values = list(row)
        if len(values) < 2:
            continue
        cells = ["" if value is None else str(value).strip() for value in values]

        labels = [i for i, cell in enumerate(cells) if cell.strip().lower() in HEADER_LABELS]
        value_columns = [i for i, cell in enumerate(cells) if cell.strip().lower() in HEADER_VALUES]
        unit_columns = [i for i, cell in enumerate(cells) if cell.strip().lower() in {"unit", "units"}]
        if labels and value_columns:
            header = (labels[0], value_columns[0], unit_columns[0] if unit_columns else None)
            continue

        if header:
            label_column, value_column, unit_column = header
            if max(label_column, value_column, unit_column or 0) >= len(cells):
                continue
            label = cells[label_column]
            value = cells[value_column]
            if unit_column is not None and cells[unit_column]:
                unit = cells[unit_column]
                if not value.lower().endswith(unit.lower()):
                    value = f"{value} {unit}".strip()
            _add(
                fields, label, value, f"{prefix}row {row_number}",
                f"{label}: {value}",
            )
            continue

        if len(cells) == 2:
            _add(fields, cells[0], cells[1], f"{prefix}row {row_number}", f"{cells[0]}: {cells[1]}")
            continue

        # Without headers, recognize a third cell as a unit only when it is known.
        if len(cells) == 3 and cells[2].lower() in UNITS:
            value = cells[1] if cells[1].lower().endswith(cells[2].lower()) else f"{cells[1]} {cells[2]}".strip()
            _add(fields, cells[0], value, f"{prefix}row {row_number}", f"{cells[0]}: {value}")
            continue

        # Support horizontal key/value pairs while preserving each cell's column.
        for column in range(0, len(cells) - 1, 2):
            if cells[column] and cells[column + 1]:
                _add(
                    fields, cells[column], cells[column + 1],
                    f"{prefix}row {row_number}, columns {column + 1}-{column + 2}",
                    f"{cells[column]}: {cells[column + 1]}",
                )



MAX_ARCHIVE_ENTRIES = 5000
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_COMPRESSION_RATIO = 1000


def _validate_office_archive(content: bytes, required_member: str) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > MAX_ARCHIVE_ENTRIES:
                raise ValueError("Office document contains too many archive entries.")
            total_size = sum(member.file_size for member in members)
            if total_size > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                raise ValueError("Office document expands beyond the 100 MB safety limit.")
            for member in members:
                if member.file_size and (
                    member.compress_size == 0
                    or member.file_size / member.compress_size > MAX_ARCHIVE_COMPRESSION_RATIO
                ):
                    raise ValueError("Office document has a suspicious compression ratio.")
            if required_member not in archive.namelist():
                raise ValueError("Office document is missing required package content.")
    except zipfile.BadZipFile as exc:
        raise ValueError("Office document is not a valid ZIP-based document.") from exc


def extract(filename: str, content: bytes) -> tuple[list[Field], list[str]]:
    ext = Path(filename).suffix.lower()
    fields: list[Field] = []
    warnings: list[str] = []
    if ext == ".csv":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("CSV must be UTF-8 encoded.") from exc
        _extract_pairs(csv.reader(io.StringIO(text)), fields, "")
    elif ext in {".txt", ".md"}:
        try:
            lines = content.decode("utf-8-sig").splitlines()
        except UnicodeDecodeError as exc:
            raise ValueError("Text documents must be UTF-8 encoded.") from exc
        for line_number, line in enumerate(lines, 1):
            if ":" in line:
                label, value = line.split(":", 1)
                _add(fields, label, value, f"line {line_number}", line.strip())
    elif ext == ".xlsx":
        _validate_office_archive(content, "xl/workbook.xml")
        try:
            import openpyxl
        except ImportError as exc:
            raise ValueError("Install document support: pip install 'datasheetdelta[documents]'") from exc
        workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
        try:
            for sheet in workbook.worksheets:
                rows = sheet.iter_rows(values_only=True)
                _extract_pairs(rows, fields, f"{sheet.title}! ")
        finally:
            workbook.close()
    elif ext == ".docx":
        _validate_office_archive(content, "word/document.xml")
        try:
            from docx import Document
        except ImportError as exc:
            raise ValueError("Install document support: pip install 'datasheetdelta[documents]'") from exc
        document = Document(io.BytesIO(content))
        for table_number, table in enumerate(document.tables, 1):
            _extract_pairs(
                ([cell.text for cell in row.cells] for row in table.rows),
                fields,
                f"table {table_number}, ",
            )
        for paragraph_number, paragraph in enumerate(document.paragraphs, 1):
            if ":" in paragraph.text:
                label, value = paragraph.text.split(":", 1)
                _add(fields, label, value, f"paragraph {paragraph_number}", paragraph.text)
    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("Install document support: pip install 'datasheetdelta[documents]'") from exc
        reader = PdfReader(io.BytesIO(content), strict=False)
        if len(reader.pages) > 500:
            raise ValueError("PDF exceeds the 500-page processing limit.")
        for page_number, page in enumerate(reader.pages, 1):
            for line_number, line in enumerate((page.extract_text() or "").splitlines(), 1):
                if ":" in line:
                    label, value = line.split(":", 1)
                    _add(fields, label, value, f"page {page_number}, line {line_number}", line.strip())
        if not fields:
            warnings.append("No text fields found. This may be a scanned PDF; OCR is not included.")
    else:
        raise ValueError("Supported formats: CSV, XLSX, DOCX, text PDF, TXT and MD.")

    counts: dict[str, int] = defaultdict(int)
    for field in fields:
        counts[field.name] += 1
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    if duplicates:
        warnings.append(
            "Duplicate parameter labels were preserved and flagged as ambiguous: "
            + ", ".join(duplicates)
        )
    if not fields:
        warnings.append(
            f"No label/value fields extracted from {filename}. "
            "Use a two-column table or Label: value lines."
        )
    return fields, warnings


def _display(fields: list[Field]) -> tuple[str | None, str | None]:
    if not fields:
        return None, None
    return " | ".join(field.value for field in fields), " | ".join(
        f"{field.source} [{field.excerpt}]" for field in fields
    )


def _compare_one(old: Field, new: Field, tolerances: dict[str, float]) -> tuple[str, str]:
    dimension = old.dimension or "unitless"
    tolerance = tolerances.get(dimension, 0.0)
    if old.value == new.value:
        return "unchanged", "Extracted values are identical."
    if old.number is not None and new.number is not None:
        if old.dimension == new.dimension and old.dimension not in {None, "unknown"}:
            status = "unchanged" if abs(old.number - new.number) <= tolerance else "changed"
            return status, "Values compared after conversion to a common base unit."
        if old.dimension is None and new.dimension is None:
            status = "unchanged" if abs(old.number - new.number) <= tolerance else "changed"
            return status, "Unitless numeric values compared directly."
        if old.dimension == new.dimension == "unknown" and (old.unit or "").lower() == (new.unit or "").lower():
            status = "unchanged" if abs(old.number - new.number) <= tolerance else "changed"
            return status, "Values use the same unrecognized unit; compared numerically without conversion."
        if old.dimension != new.dimension:
            return "unit_mismatch", "Units are missing or belong to different dimensions; manual review required."
        return "unit_mismatch", "Units could not be safely normalized; manual review required."
    return "changed", "Text or value differs; assess materiality."


def compare(reference_name: str, old: list[Field], revised_name: str,
            new: list[Field], tolerances: dict[str, float] | None = None) -> dict:
    if tolerances is None:
        tolerances = {}
    allowed_dimensions = {
        "length", "pressure", "voltage", "current", "power", "frequency",
        "mass", "temperature", "percentage", "unitless", "unknown",
    }
    if not isinstance(tolerances, dict):
        raise ValueError("Tolerances must be a mapping of dimensions to numeric values.")
    normalized_tolerances: dict[str, float] = {}
    for dimension, value in tolerances.items():
        if dimension not in allowed_dimensions:
            raise ValueError(f"Unsupported tolerance dimension: {dimension}.")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Tolerance for {dimension} must be a finite, non-negative number.")
        try:
            numeric_value = float(value)
        except (OverflowError, ValueError):
            raise ValueError(f"Tolerance for {dimension} must be a finite, non-negative number.")
        if not math.isfinite(numeric_value) or numeric_value < 0:
            raise ValueError(f"Tolerance for {dimension} must be a finite, non-negative number.")
        normalized_tolerances[dimension] = numeric_value
    tolerances = normalized_tolerances
    left: dict[str, list[Field]] = defaultdict(list)
    right: dict[str, list[Field]] = defaultdict(list)
    for field in old:
        left[field.name].append(field)
    for field in new:
        right[field.name].append(field)
    findings: list[Finding] = []
    for key in sorted(left.keys() | right.keys()):
        a, b = left.get(key, []), right.get(key, [])
        av, asource = _display(a)
        bv, bsource = _display(b)
        if not a:
            status, explanation = "added", "Parameter appears only in the revised document."
        elif not b:
            status, explanation = "removed", "Parameter appears only in the reference document."
        elif len(a) > 1 or len(b) > 1:
            status = "ambiguous"
            explanation = "Multiple extracted entries share this parameter label. Resolve the source entries before comparison."
        else:
            status, explanation = _compare_one(a[0], b[0], tolerances)
        findings.append(Finding(key, status, av, bv, asource, bsource, explanation))
    return {
        "reference_file": reference_name,
        "revised_file": revised_name,
        "findings": [asdict(item) for item in findings],
        "warnings": [],
        "review_required": True,
        "method": "deterministic label/value extraction and comparison",
        "tolerances": {key: float(value) for key, value in sorted(tolerances.items())},
        "tolerance_policy": "absolute, dimension-specific tolerances; known dimensions use their base unit, and omitted dimensions use exact comparison",
    }


def _spreadsheet_safe(value: object) -> str:
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@", chr(9), chr(13))):
        return "'" + text
    return text


def report_csv(result: dict) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow([
        "parameter", "status", "reference", "revised",
        "reference_source", "revised_source", "explanation",
    ])
    for finding in result["findings"]:
        writer.writerow([
            _spreadsheet_safe(finding[key]) for key in (
                "parameter", "status", "reference", "revised",
                "reference_source", "revised_source", "explanation",
            )
        ])
    return stream.getvalue()
