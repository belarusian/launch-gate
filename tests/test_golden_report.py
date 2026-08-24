"""Golden-file test for :func:`launch_gate.report.render_report`.

Builds a fixed :class:`~launch_gate.models.Report` and asserts the rendered
output equals a committed golden string **byte-for-byte**. This pins the exact
layout so any unintended change to the report format fails the gate.

It also asserts the full ``run_checks`` path is byte-identical across runs when
``now`` is fixed (the endpoint-contention evidence embeds a wall-clock-derived
``age {int(age)}s`` value that is only stable when ``now`` is injected).
"""

from __future__ import annotations

import os
from pathlib import Path

from launch_gate.checks import run_checks
from launch_gate.models import CheckResult, Report
from launch_gate.report import render_report

#: The committed golden report, built from explicit lines joined by "\n" so the
#: expected bytes are unambiguous (no leading/trailing-newline surprises).
_GOLDEN_LINES: tuple[str, ...] = (
    "launch-gate report",
    "=" * 40,
    "launch line: nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
    "project dir: /home/u/proj (project 'proj')",
    "",
    "per-check verdicts",
    "-" * 40,
    "redirect-safety      GO",
    "    launch line appends (>>) to cycles.out.",
    "endpoint-contention  NO-GO",
    "    target endpoints: http://192.168.1.161:8080/v1.",
    "    NO-GO: other holds http://192.168.1.161:8080/v1 (fresh, age 12s < wall 7200s, pid 4242).",
    "wall-sizing          GO",
    "    outer wall (perl alarm): 21600s.",
    "prerequisites        GO",
    "    on branch main.",
    "-" * 40,
    "NO-GO",
)

GOLDEN_REPORT: str = "\n".join(_GOLDEN_LINES)


def _fixed_report() -> Report:
    """Return the fixed report whose rendering is the golden string."""
    return Report(
        header=(
            "launch line: nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
            "project dir: /home/u/proj (project 'proj')",
        ),
        checks=(
            CheckResult("redirect-safety", True, ("launch line appends (>>) to cycles.out.",)),
            CheckResult(
                "endpoint-contention",
                False,
                (
                    "target endpoints: http://192.168.1.161:8080/v1.",
                    "NO-GO: other holds http://192.168.1.161:8080/v1 "
                    "(fresh, age 12s < wall 7200s, pid 4242).",
                ),
            ),
            CheckResult("wall-sizing", True, ("outer wall (perl alarm): 21600s.",)),
            CheckResult("prerequisites", True, ("on branch main.",)),
        ),
    )


def test_render_report_matches_golden_byte_for_byte() -> None:
    out = render_report(_fixed_report())
    assert out == GOLDEN_REPORT


def test_golden_is_deterministic() -> None:
    # Two renders of the same fixed report are byte-identical.
    assert render_report(_fixed_report()) == render_report(_fixed_report())


def _make_fresh_foreign_registry(registry_dir: Path) -> None:
    """Create a fresh, foreign registry entry with a precisely set mtime.

    The entry targets the same endpoint as the checked driver, belongs to a
    different project, and is fresh (age 12s < wall 7200s) so the
    endpoint-contention check reports a deterministic ``age 12s`` line.
    """
    registry_dir.mkdir(parents=True, exist_ok=True)
    entry = registry_dir / "other.json"
    entry.write_text(
        '{"project": "other", "pid": "4242", '
        '"endpoints": ["http://192.168.1.161:8080/v1"], '
        '"outer_wall_seconds": 7200, "launched_at": 999988}',
        encoding="utf-8",
    )
    # Pin the mtime so ``now - mtime`` is exactly 12.0 for now=1_000_000.0.
    os.utime(entry, (999_988.0, 999_988.0))


def test_run_checks_report_is_byte_identical_for_fixed_now(tmp_path: Path) -> None:
    """Two full ``run_checks`` runs with the same fixed ``now`` render identically.

    The endpoint-contention evidence embeds a wall-clock-derived value
    (``age {int(age)}s``). With ``now`` injected and the registry mtime pinned,
    that value is fixed, so the rendered report is byte-identical across runs.
    """
    registry_dir = tmp_path / "registry"
    _make_fresh_foreign_registry(registry_dir)
    ai_dir = tmp_path / "ai"
    ai_dir.mkdir()
    project_dir = tmp_path / "myproj"
    project_dir.mkdir()

    script_text = "export FIVE_BASE_URL=http://192.168.1.161:8080/v1\n"
    fixed_now = 1_000_000.0

    def render_once() -> str:
        checks = run_checks(
            "nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
            None,
            script_text,
            registry_dir,
            "myproj",
            fixed_now,
            ai_dir,
            project_dir,
            ss_file=None,
            driver_lineage=set(),
        )
        return render_report(Report(("header line",), checks))

    first = render_once()
    second = render_once()
    assert first == second
    # The wall-clock-derived value is pinned by the fixed now.
    assert "age 12s" in first


# ---------------------------------------------------------------------------
# Cycle 13 — byte-exact golden for an ALL-GO report (TICKET-044).
# The no-GO golden above pins the NO-GO path; this pins the ALL-GO path
# (including the final "ALL-GO" line) byte-for-byte.
# ---------------------------------------------------------------------------

_GOLDEN_ALL_GO_LINES: tuple[str, ...] = (
    "launch-gate report",
    "=" * 40,
    "launch line: nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
    "project dir: /home/u/proj (project 'proj')",
    "",
    "per-check verdicts",
    "-" * 40,
    "redirect-safety      GO",
    "    launch line appends (>>) to cycles.out.",
    "endpoint-contention  GO",
    "    no occupancy data; GO.",
    "wall-sizing          GO",
    "    outer wall (perl alarm): 21600s.",
    "prerequisites        GO",
    "    on branch main.",
    "-" * 40,
    "ALL-GO",
)

GOLDEN_REPORT_ALL_GO: str = "\n".join(_GOLDEN_ALL_GO_LINES)


def _all_go_report() -> Report:
    """Return the fixed all-GO report whose rendering is the all-GO golden."""
    return Report(
        header=(
            "launch line: nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
            "project dir: /home/u/proj (project 'proj')",
        ),
        checks=(
            CheckResult("redirect-safety", True, ("launch line appends (>>) to cycles.out.",)),
            CheckResult("endpoint-contention", True, ("no occupancy data; GO.",)),
            CheckResult("wall-sizing", True, ("outer wall (perl alarm): 21600s.",)),
            CheckResult("prerequisites", True, ("on branch main.",)),
        ),
    )


def test_render_report_all_go_matches_golden_byte_for_byte() -> None:
    out = render_report(_all_go_report())
    assert out == GOLDEN_REPORT_ALL_GO


def test_all_go_golden_final_line_is_all_go() -> None:
    out = render_report(_all_go_report())
    assert out.split("\n")[-1] == "ALL-GO"
