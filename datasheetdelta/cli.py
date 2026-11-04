import argparse
import json
from pathlib import Path
from .core import compare, extract, report_csv

def main():
    parser = argparse.ArgumentParser(description="Compare engineering specification revisions.")
    parser.add_argument("reference")
    parser.add_argument("revised")
    parser.add_argument("--out", default="datasheetdelta-report")
    parser.add_argument("--tolerance", type=float, default=0,
                        help="Absolute tolerance in canonical base units (default: 0).")
    args = parser.parse_args()
    reference_path, revised_path = Path(args.reference), Path(args.revised)
    old, old_warnings = extract(reference_path.name, reference_path.read_bytes())
    new, new_warnings = extract(revised_path.name, revised_path.read_bytes())
    result = compare(reference_path.name, old, revised_path.name, new, args.tolerance)
    result["warnings"] = old_warnings + new_warnings
    base = Path(args.out)
    base.parent.mkdir(parents=True, exist_ok=True)
    base.with_suffix(".json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    base.with_suffix(".csv").write_text(report_csv(result), encoding="utf-8")
    summary = result["summary"]
    print(f"Compared {summary['total']} fields: {summary['changed']} changed, "
          f"{summary['added']} added, {summary['removed']} removed, "
          f"{summary['unchanged']} unchanged, {summary['unit_mismatch']} unit mismatches.")
    print(f"Reports saved with prefix {base}. Qualified engineering review is required.")

if __name__ == "__main__":
    main()
