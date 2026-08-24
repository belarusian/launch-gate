"""Orchestration of the four launch-gate checks.

This package is the **orchestration** layer. It bundles the four named checks
(redirect-safety, endpoint-contention, wall-sizing, prerequisites) behind a single
:func:`run_checks` entry point so the CLI and any library caller share one
deterministic path. It also re-exports the
:class:`~launch_gate.models.CheckResult` value object under the short name
:data:`Check`.

The package exposes a machine-readable contract for the orchestration result:

- :data:`CHECK_ORDER` — the four stable check names, in the exact order
  :func:`run_checks` returns them.
- :func:`verdict_of` — a pure predicate returning ``True`` iff every check in a
  result tuple is GO (the all-GO verdict). It mirrors
  :attr:`launch_gate.models.Report.all_go`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from launch_gate.endpoint_contention import check_endpoint_contention
from launch_gate.models import CheckResult
from launch_gate.prerequisites import GitState, check_prerequisites
from launch_gate.redirect_safety import check_redirect_safety
from launch_gate.wall_sizing import check_wall_sizing

#: The per-check result value object, re-exported under a short name.
Check = CheckResult

#: The four stable check names, in the exact order :func:`run_checks` returns
#: them. This is the authoritative ordering contract for the orchestration
#: result and the report's per-check table rows.
CHECK_ORDER: tuple[str, ...] = (
    "redirect-safety",
    "endpoint-contention",
    "wall-sizing",
    "prerequisites",
)

__all__ = [
    "Check",
    "CheckResult",
    "CHECK_ORDER",
    "run_checks",
    "verdict_of",
]


def verdict_of(checks: Sequence[CheckResult]) -> bool:
    """Return the all-GO verdict for a tuple of check results.

    This is the pure predicate the CLI and any library caller share for
    "did every check pass?". It mirrors
    :attr:`launch_gate.models.Report.all_go`: an empty tuple is **not** all-GO
    (at least one check must have run and be GO).

    Args:
        checks: The ordered check results (e.g. the tuple returned by
            :func:`run_checks`).

    Returns:
        ``True`` iff ``checks`` is non-empty and every check's ``go`` is
        ``True``; ``False`` otherwise (including the empty tuple).
    """
    return bool(checks) and all(c.go for c in checks)


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
    git_state: GitState | None = None,
    tool_available: Callable[[str], bool] | None = None,
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
        git_state: An optional pre-collected :class:`GitState` for the
            prerequisites check. When ``None``, it is collected from
            ``project_dir`` (which shells out to ``git``). Supplying it keeps
            the orchestration path deterministic and subprocess-free.
        tool_available: An optional ``tool -> bool`` callable for the
            prerequisites check's auxiliary-tool probe. When ``None``, the
            default import-spec probe is used.

    Returns:
        A tuple of four :class:`CheckResult` in the stable order given by
        :data:`CHECK_ORDER` (``redirect-safety``, ``endpoint-contention``,
        ``wall-sizing``, ``prerequisites``). The order is a contract: the report
        renderer lays out the per-check table rows in exactly this order, and
        :func:`verdict_of` folds the tuple over in this order.
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
        check_prerequisites(
            ai_dir,
            project_dir,
            git_state=git_state,
            tool_available=tool_available,
        ),
    )
