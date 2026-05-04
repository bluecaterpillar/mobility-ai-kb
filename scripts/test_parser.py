"""CLI: parse an Arval PDF and print the extracted JSON.

Usage:
    python scripts/test_parser.py data/mattina_napoli.pdf

Reads the Anthropic API key from .streamlit/secrets.toml ([anthropic].api_key)
or from the ANTHROPIC_API_KEY environment variable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow `from lib.parser import ...` when invoked as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.parser import PARSER_MODEL, parse_arval_pdf_file  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/test_parser.py <path/to/quote.pdf>", file=sys.stderr)
        return 2

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}", file=sys.stderr)
        return 1

    print(f"Parsing {pdf_path} with {PARSER_MODEL}...", file=sys.stderr)
    parsed = parse_arval_pdf_file(pdf_path)
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
