"""Command-line interface for launch_gate.

This is a **thin orchestration layer**: all check semantics live in the four
check modules (:mod:`launch_gate.redirect_safety`,
:mod:`launch_gate.endpoint_contention`, :mod:`launch_gate.wall_sizing`,
:mod:`launch_gate.prerequisites`) and all rendering lives in
:mod:`launch_gate.report`. This module only:

1. parses command-line arguments (a ``check`` subcommand),
2. reads the driver script and any ``cycles.out`` history,
3. runs the four checks,
4. renders the report (:func:`launch_gate.report.render_report`) and prints it,
5. returns a process exit code.

The exit-code contract is load-bearing for later automation:

- ``0`` — all checks GO.
- ``1`` — any check NO-GO.
- ``2`` — usage error: a subcommand is missing/unrecognized, or a required
  input (``--project-dir`` / ``--ai-dir``) is missing. An error message is
  written to stderr and no exception escapes :func:`run`.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from launch_gate.endpoint_contention import check_endpoint_contention
from launch_gate.models import CheckResult, Report
from launch_gate.prerequisites import check_prerequisites
from launch_gate.redirect_safety import check_redirect_safety
from launch_gate.report import render_report
from launch_gate.wall_sizing import check_wall_sizing


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser.

    Pure function: no side effects, no I/O. The returned parser exposes a single
    **required** subcommand, ``check``:

    - ``launch_line`` (positional): the driver invocation string.
    - ``--project-dir`` (required): the project checkout directory.
    - ``--ai-dir`` (required): the AI artifacts directory.
    - ``--script``: the driver script the launch line runs.
    - ``--ss-file``: a pre-captured ``ss`` snapshot file.

    A call with no subcommand (or an unrecognized one) is a usage error; argparse
    reports it and :func:`run` translates that into exit code ``2``.
    """
    parser = argparse.ArgumentParser(
        prog="launch-gate",
        description="Deterministic launch gate for four pipelines.",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="{check}",
        required=True,
        title="subcommands",
    )
    check = subparsers.add_parser(
        "check",
        help="Gate a four pipeline launch and print a deterministic report.",
        description=(
            "Run the four launch checks (redirect-safety, endpoint-contention, "
            "wall-sizing, prerequisites) and print a deterministic GO/NO-GO "
            "report. Exit code 0 when all-GO, 1 when any-NO-GO, 2 on usage error."
        ),
    )
    check.add_argument("launch_line", help="The driver invocation string.")
    check.add_argument("--project-dir", required=True, help="Project checkout dir.")
    check.add_argument("--ai-dir", required=True, help="AI artifacts dir.")
    check.add_argument("--script", help="Driver script the launch line runs.")
    check.add_argument("--ss-file", help="Pre-captured `ss` snapshot file.")
    return parser


def _read_text(path: Path | None) -> str | None:
    """Return the text of ``path``, or ``None`` when it is absent/unreadable."""
    if path is None or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _find_cycles_out(project_dir: Path, ai_dir: Path) -> Path | None:
    """Return a ``cycles.out`` under ``project_dir`` or ``ai_dir``, if any."""
    for base in (project_dir, ai_dir):
        if not base.is_dir():
            continue
        for name in ("cycles.out", "ai/cycles.out"):
            candidate = base / name
            if candidate.is_file():
                return candidate
    return None


def _driver_lineage() -> set[int]:
    """Return the current process's own pid lineage (best-effort, self only).

    The checked driver is not running under launch-gate, so its lineage is not
    knowable here; we return the current process pid so that a socket owned by
    *this* process is never miscounted as foreign.
    """
    return {os.getpid()}


def _registry_dir() -> Path:
    """Return the launch-registry directory (``~/.four/launches``)."""
    return Path.home() / ".four" / "launches"


def _run_check(args: argparse.Namespace) -> int:
    """Execute the ``check`` subcommand and return its exit code.

    Args:
        args: The parsed ``check`` subcommand namespace.

    Returns:
        ``0`` when all checks are GO, ``1`` when any is NO-GO.
    """
    project_dir = Path(args.project_dir)
    ai_dir = Path(args.ai_dir)
    project_name = project_dir.name

    script_path = Path(args.script) if args.script else None
    script_text = _read_text(script_path)
    cycles_path = _find_cycles_out(project_dir, ai_dir)
    cycles_text = _read_text(cycles_path)
    ss_file = Path(args.ss_file) if args.ss_file else None
    now = time.time()

    # Header: what was checked, sources read.
    header: list[str] = []
    header.append(f"launch line: {args.launch_line}")
    header.append(f"project dir: {project_dir} (project {project_name!r})")
    header.append(f"ai dir: {ai_dir}")
    header.append(f"driver script: {script_path if script_path else '(none supplied)'}")
    header.append(f"cycles.out: {cycles_path if cycles_path else '(none found)'}")
    header.append(f"ss file: {ss_file if ss_file else '(none supplied)'}")
    header.append(f"registry dir: {_registry_dir()}")

    checks: list[CheckResult] = []
    checks.append(check_redirect_safety(args.launch_line, cycles_text))
    checks.append(
        check_endpoint_contention(
            script_text,
            _registry_dir(),
            project_name,
            now,
            ss_file=ss_file,
            driver_lineage=_driver_lineage(),
        )
    )
    checks.append(check_wall_sizing(script_text, ai_dir, project_dir))
    checks.append(check_prerequisites(ai_dir, project_dir))

    report = Report(tuple(header), tuple(checks))
    print(render_report(report))
    return 0 if report.all_go else 1


def run(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code.

    Args:
        argv: Command-line arguments (without the program name). When ``None``,
            ``sys.argv[1:]`` is used. The first token must be a subcommand
            (currently only ``check``).

    Returns:
        ``0`` when all checks are GO, ``1`` when any is NO-GO, and ``2`` on a
        usage error. In the error case an error message is written to stderr and
        no exception escapes :func:`run`.
    """
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return int(code)

    if args.command == "check":
        return _run_check(args)

    print(f"launch-gate: error: unknown subcommand {args.command!r}", file=sys.stderr)
    return 2


def main() -> int:
    """Console-script entry point.

    Thin wrapper around :func:`run` that returns its exit code.
    """
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
