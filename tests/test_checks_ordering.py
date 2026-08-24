"""Contract tests for the :mod:`launch_gate.checks` orchestration surface.

These pin the machine-readable contract added in Cycle 13:

- :data:`launch_gate.checks.CHECK_ORDER` — the four stable check names in the
  exact order :func:`run_checks` returns them.
- :func:`launch_gate.checks.verdict_of` — the all-GO predicate (mirrors
  :attr:`launch_gate.models.Report.all_go`).
- :func:`run_checks` returns the four checks in :data:`CHECK_ORDER` order.

All inputs are injected (``now``, ``git_state``, ``tool_available``) so the
tests are deterministic and subprocess-free (no real git, no live ``ss``).
"""

from __future__ import annotations

from pathlib import Path

from launch_gate.checks import CHECK_ORDER, run_checks, verdict_of
from launch_gate.models import CheckResult
from launch_gate.prerequisites import GitState


def _go_git() -> GitState:
    """A clean, on-main, in-sync git state (no build branches)."""
    return GitState(True, "main", True, 0, 0, True, ())


def _no_tools(tool: str) -> bool:
    return False


def _run_all_go(tmp_path: Path) -> tuple[CheckResult, ...]:
    """Run the four checks with inputs that make every check GO."""
    ai_dir = tmp_path / "ai"
    ai_dir.mkdir()
    (ai_dir / "runner-prompt.md").write_text("prompt\n", encoding="utf-8")
    (ai_dir / "gate-log.md").write_text("log\n", encoding="utf-8")
    project_dir = tmp_path / "myproj"
    project_dir.mkdir()
    registry_dir = tmp_path / "registry"  # does not exist -> no occupancy data

    return run_checks(
        "nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
        None,  # no cycles.out history
        None,  # no --script -> endpoint-contention GO (no occupancy data)
        registry_dir,
        "myproj",
        now=1_000_000.0,
        ai_dir=ai_dir,
        project_dir=project_dir,
        git_state=_go_git(),
        tool_available=_no_tools,
    )


def test_check_order_is_the_documented_contract() -> None:
    assert CHECK_ORDER == (
        "redirect-safety",
        "endpoint-contention",
        "wall-sizing",
        "prerequisites",
    )


def test_run_checks_returns_checks_in_check_order(tmp_path: Path) -> None:
    checks = _run_all_go(tmp_path)
    assert [c.name for c in checks] == list(CHECK_ORDER)


def test_verdict_of_all_go_is_true() -> None:
    checks = (
        CheckResult("redirect-safety", True, ()),
        CheckResult("endpoint-contention", True, ()),
        CheckResult("wall-sizing", True, ()),
        CheckResult("prerequisites", True, ()),
    )
    assert verdict_of(checks) is True


def test_verdict_of_any_no_go_is_false() -> None:
    checks = (
        CheckResult("redirect-safety", True, ()),
        CheckResult("endpoint-contention", False, ("NO-GO: contention.",)),
        CheckResult("wall-sizing", True, ()),
        CheckResult("prerequisites", True, ()),
    )
    assert verdict_of(checks) is False


def test_verdict_of_empty_tuple_is_false() -> None:
    # Mirrors Report.all_go: an empty tuple is not all-GO.
    assert verdict_of(()) is False


def test_verdict_of_matches_run_checks_all_go(tmp_path: Path) -> None:
    checks = _run_all_go(tmp_path)
    assert verdict_of(checks) is True
