from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from . import __version__
from .core import AnalysisError, analyze
from .render import render_html, render_markdown, render_text


def main(argv=None):
    parser = argparse.ArgumentParser(description="Explain which Python files a change may reach, with import evidence.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository or source tree root")
    parser.add_argument("--base", help="Compare this commit to the working tree (default HEAD)")
    parser.add_argument("--changed", nargs="+", help="Explicit repository-relative paths; no Git required")
    parser.add_argument("--source-root", action="append", help="Import root, repeatable (default src and . if src exists)")
    parser.add_argument("--format", choices=["text", "json", "markdown", "html"], default="text")
    parser.add_argument("--output", type=Path, help="Write a report to a file instead of stdout")
    parser.add_argument("--strict", action="store_true", help="Exit 2 if analysis has warnings (not a safety verdict)")
    args = parser.parse_args(argv)
    try:
        result = analyze(args.root, args.changed, args.base, args.source_root)
        output = {"text": render_text, "json": lambda r: json.dumps(r, indent=2, ensure_ascii=True),
                  "markdown": render_markdown, "html": render_html}[args.format](result)
        if args.output:
            args.output.write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 2 if args.strict and result["warnings"] else 0
    except (AnalysisError, OSError) as exc:
        print(f"impact-trail: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
