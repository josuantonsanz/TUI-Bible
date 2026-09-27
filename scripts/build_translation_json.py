"""Build a verse-translation JSON file for OpenGNT Interface from a local source.

This is a thin command-line wrapper around
:mod:`opengnt_interface.translation_source`, which the setup command also uses
to derive the importer JSON from the bundled ``startup/bibliaEsp.pk``.

Usage:
    python scripts/build_translation_json.py --input SOURCE --output startup/spanish_bible.json
    python scripts/build_translation_json.py --input SOURCE.json --format json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Adjust path to ensure imports work when run directly from a checkout.
sys.path.append(str(Path(__file__).resolve().parent.parent))

from opengnt_interface.translation_source import (  # noqa: E402,F401
    SOURCE_BOOK_IDS,
    convert,
    infer_format,
    load_source,
    write_translation_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path, help="Local source file you have the right to use")
    parser.add_argument("--output", type=Path, default=Path("startup/spanish_bible.json"), help="Destination JSON file")
    parser.add_argument("--format", choices=("auto", "pickle", "json"), default="auto", help="Source format (default: infer from the extension)")
    args = parser.parse_args()

    fmt = None if args.format == "auto" else args.format

    if not args.input.is_file():
        print(f"error: source file not found: {args.input}", file=sys.stderr)
        return 1

    try:
        result = write_translation_json(args.input, args.output, fmt)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    total_verses = sum(len(verses) for book in result.values() for verses in book["chapters"].values())
    print(f"Wrote {len(result)} books / {total_verses} verses to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
