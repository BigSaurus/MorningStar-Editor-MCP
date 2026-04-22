from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import morningstar_mc8_mcp as mc8


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or verify the MC8 MCP tool reference Markdown file."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the checked-in reference differs from freshly generated output.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    output_path = ROOT / "MC8_MCP_TOOL_REFERENCE.md"
    rendered = mc8.generate_tool_reference_markdown()

    if args.check:
        existing = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        if existing != rendered:
            print(f"OUT OF DATE: {output_path}")
            return 1
        print(f"OK: {output_path}")
        return 0

    output_path.write_text(rendered, encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())