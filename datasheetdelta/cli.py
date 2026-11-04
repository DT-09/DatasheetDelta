from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import compare, extract, report_csv

def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two engineering specification revisions.")
    parser.add_argument("reference", help="Reference/original document")
    parser.add_argument("revised", help="Revised document")
    parser.add_argument("--out", default="datasheetdelta-report", help="Output path prefix (default: datasheetdelta-report)")
    parser.add_argument("--tolerance", type=float, default=0.0, help="Absolute tolerance in normalized base units")
    args = parser.parse_args()
    if args.tolerance < 0:
        parser.error("--tolerance must be non-negative")
    reference, revised = Path(args.reference), Path(args.revised)
    for path in (reference, revised):
        if not path.is_file():
            parser.error(f"Input file does not exist: {path}")
    try:
        old_fields, old_warnings = extract(reference.name, reference.read_bytes())
        new_fields, new_warnings = extract(revised.name, revised.read_bytes())
        result = compare(reference.name, old_fields, revised.name, new_fields, args.tolerance)
    except (OSError, ValueError) as exc:
        print(f"DatasheetDelta: {exc}", file=sys.stderr)
        return 2
    result["warnings"] = old_warnings + new_warnings
    result["tolerance"] = {"value": args.tolerance, "basis": "normalized base units where dimensions are known"}
    base = Path(args.out)
    base.parent.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = base.with_suffix(".json"), base.with_suffix(".csv")
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    csv_path.write_text(report_csv(result), encoding="utf-8-sig", newline="")
    print(f"Compared {len(result['findings'])} parameters.")
    print(f"JSON: {json_path}")
    print(f"CSV:  {csv_path}")
    print("Human engineering review is required before relying on any finding.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
