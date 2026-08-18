"""Import reviewed Bangaaru Naanelu entries into the Melimi MASTER lexicon.

Usage:
    python scripts/import_bangaaru_naanelu.py path/to/reviewed_entries.json
    python scripts/import_bangaaru_naanelu.py path/to/reviewed_entries.json --dry-run

The input is deliberately a reviewed JSON file, not the raw PDF. This keeps
OCR/extraction errors outside the authoritative runtime layer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.melimi.main_dictionary import import_entries, manifest, validate_entry


def load_entries(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        return payload["entries"]
    raise ValueError("Input must be a JSON array or an object containing an 'entries' array.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import reviewed Bangaaru Naanelu entries.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--replace", action="store_true", help="Allow replacement of an existing non-main-dictionary MASTER root.")
    args = parser.parse_args()

    entries = load_entries(args.input)
    for item in entries:
        validate_entry(item)

    print(json.dumps({"manifest": manifest(), "entries": len(entries), "dry_run": args.dry_run}, ensure_ascii=False, indent=2))
    if args.dry_run:
        return 0

    result = import_entries(entries, replace=args.replace)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
