"""Command-line interface for launch_gate.

Subcommand surface (built out across cycles):

    launch-gate check <launch-line> --project-dir <proj> --ai-dir <ai>
                      [--script <driver.sh>] [--ss-file <file>]

Exit codes: 0 = all-GO, 1 = any-NO-GO, 2 = usage error.
"""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="launch-gate",
        description="Deterministic launch gate for four pipelines.",
    )
    sub = parser.add_subparsers(dest="command")
    check = sub.add_parser("check", help="Gate a four pipeline launch.")
    check.add_argument("launch_line", help="The driver invocation string.")
    check.add_argument("--project-dir", required=True, help="Project checkout dir.")
    check.add_argument("--ai-dir", required=True, help="AI artifacts dir.")
    check.add_argument("--script", help="Driver script the launch line runs.")
    check.add_argument("--ss-file", help="Pre-captured `ss` snapshot file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_usage(sys.stderr)
        return 2
    # The four checks and the report are implemented in later cycles.
    print("launch-gate: check not yet implemented (cycle 1 scaffolding)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
