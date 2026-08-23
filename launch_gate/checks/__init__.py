"""Orchestration of the four launch-gate checks.

This package is the **orchestration** layer. It bundles the four named checks
(redirect-safety, endpoint-contention, wall-sizing, prerequisites) behind a single
:func:`run_checks` entry point so the CLI and any library caller share one
deterministic path. It also re-exports the
:class:`~launch_gate.models.CheckResult` value object under the short name
:data:`Check`.
"""

from __future__ import annotations

from pathlib import Path

from launch_gate.endpoint_contention import check_endpoint_contention
from launch_gate.models import CheckResult
from launch_gate.prerequisites import check_prerequisites
from launch_gate.redirect_safety import check_redirect_safety
from launch_gate.wall_sizing import check_wall_sizing

#: The per-check result value object, re-exported under a short name.
Check = CheckResult

__all__ = [
    "Check",
    "CheckResult",
    "run_checks",
]


def run_checks(
    launch_line: str,
    cycles_out_text: str | None,
    script_text: str | None,
    registry_dir: Path,
    project_name: str,
    now: float,
    ai_dir: Path,
    project_dir: Path,
    ss_file: Path | None = None,
    driver_lineage: set[int] | None = None,
) -> tuple[CheckResult, ...]:
    """Run the four named launch-gate checks in stable order.

    This is the single orchestration path shared by the CLI and any library
    caller. It gathers no I/O of its own: every input is supplied by the caller
    (which is what keeps the result deterministic and testable in-process).

    Args:
        launch_line: The driver invocation string.
        cycles_out_text: The text of an existing ``cycles.out``, or ``None`` when
            there is no history file.
        script_text: The driver script text, or ``None`` when not supplied.
        registry_dir: The ``~/.four/launches`` directory to scan.
        project_name: The basename of the checked ``--project-dir``.
        now: The current epoch (seconds), used for registry freshness math.
        ai_dir: The AI artifacts directory.
        project_dir: The project checkout directory.
        ss_file: An optional pre-captured ``ss`` snapshot file.
        driver_lineage: The checked driver's own pid lineage (for socket
            attribution). Defaults to the empty set.

    Returns:
        A tuple of four :class:`CheckResult` in stable order:
        ``redirect-safety``, ``endpoint-contention``, ``wall-sizing``,
        ``prerequisites``.
    """
    return (
        check_redirect_safety(launch_line, cycles_out_text),
        check_endpoint_contention(
            script_text,
            registry_dir,
            project_name,
            now,
            ss_file=ss_file,
            driver_lineage=driver_lineage,
        ),
        check_wall_sizing(script_text, ai_dir, project_dir),
        check_prerequisites(ai_dir, project_dir),
    )
