from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import compare, extract, report_csv


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two engineering specification revisions."
    )
    parser.add_argument("reference", help="Path to the original/reference document")
    parser.add_argument("revised", help="Path to the revised document")
    parser.add_argument("--out", default="datasheetdelta-report", help="Output filename prefix")
    parser.add_argument(
        "--tolerance", type=float, default=0.0,
        help="Absolute tolerance in normalized base units for compatible numeric values",
    )
    args = parser.parse_args()

    reference_path = Path(args.reference)
    revised_path = Path(args.revised)
    if not reference_path.is_file():
        parser.error(f"Reference document does not exist: {reference_path}")
    if not revised_path.is_file():
        parser.error(f"Revised document does not exist: {revised_path}")

    try:
        reference_fields, reference_warnings = extract(
            reference_path.name, reference_path.read_bytes()
        )
        revised_fields, revised_warnings = extract(
            revised_path.name, revised_path.read_bytes()
        )
        result = compare(
            reference_path.name, reference_fields,
            revised_path.name, revised_fields, args.tolerance,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    result["warnings"] = reference_warnings + revised_warnings
    output_prefix = Path(args.out)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    output_prefix.with_suffix(".json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    output_prefix.with_suffix(".csv").write_text(
        report_csv(result), encoding="utf-8-sig", newline=""
    )
    counts = {}
    for finding in result["findings"]:
        counts[finding["status"]] = counts.get(finding["status"], 0) + 1
    print(f"Compared {len(result['findings'])} parameters.")
    print("Statuses: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    print(f"Reports saved with prefix: {output_prefix}")


if __name__ == "__main__":
    main()
