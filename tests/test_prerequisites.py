"""Unit tests for :mod:`launch_gate.prerequisites`.

Stdlib-only and fully in-process: the git state and the tool-availability
probe are **injected** (``git_state`` and ``tool_available``), so no real git
subprocess or host import is ever exercised. Every test asserts the exact
``result.lines`` in addition to the ``go`` verdict.
"""

from __future__ import annotations

from pathlib import Path

from launch_gate.prerequisites import GitState, check_prerequisites

# Fixed evidence lines for a present, non-empty runner prompt + gate log.
_PROMPT_OK = "runner prompt present and non-empty: runner-prompt.md."
_GATE_OK = "gate log present and non-empty: gate-log.md."

# Fixed evidence lines when no auxiliary tool is importable on the host.
_TOOLS_NONE = (
    "fourseer: not available on this host.",
    "spoke_lint: not available on this host.",
    "loop_doctor: not available on this host.",
)


def _make_ai(
    ai_dir: Path,
    *,
    runner: bool = True,
    gate: bool = True,
    runner_empty: bool = False,
    gate_empty: bool = False,
) -> None:
    """Create a runner prompt and/or gate log under ``ai_dir``."""
    ai_dir.mkdir(parents=True, exist_ok=True)
    if runner:
        body = "" if runner_empty else "prompt body\n"
        (ai_dir / "runner-prompt.md").write_text(body, encoding="utf-8")
    if gate:
        body = "" if gate_empty else "log body\n"
        (ai_dir / "gate-log.md").write_text(body, encoding="utf-8")


def _go_git() -> GitState:
    """A clean, on-main, in-sync git state (no build branches)."""
    return GitState(True, "main", True, 0, 0, True, ())


def _no_tools(tool: str) -> bool:
    return False


def _all_tools(tool: str) -> bool:
    return True


def test_runner_and_gate_present_non_empty(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai)
    result = check_prerequisites(ai, tmp_path, git_state=_go_git(), tool_available=_no_tools)
    assert result.go is True
    assert result.lines == (
        _PROMPT_OK,
        _GATE_OK,
        "on branch main.",
        "working tree is clean.",
        "main is in sync with origin/main.",
        *_TOOLS_NONE,
    )


def test_runner_missing(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai, runner=False)
    result = check_prerequisites(ai, tmp_path, git_state=_go_git(), tool_available=_no_tools)
    assert result.go is False
    assert result.lines == (
        "NO-GO: no runner prompt found in ai/.",
        _GATE_OK,
        "on branch main.",
        "working tree is clean.",
        "main is in sync with origin/main.",
        *_TOOLS_NONE,
    )


def test_runner_empty(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai, runner_empty=True)
    result = check_prerequisites(ai, tmp_path, git_state=_go_git(), tool_available=_no_tools)
    assert result.go is False
    assert result.lines == (
        "NO-GO: runner prompt runner-prompt.md is empty.",
        _GATE_OK,
        "on branch main.",
        "working tree is clean.",
        "main is in sync with origin/main.",
        *_TOOLS_NONE,
    )


def test_gate_missing(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai, gate=False)
    result = check_prerequisites(ai, tmp_path, git_state=_go_git(), tool_available=_no_tools)
    assert result.go is False
    assert result.lines == (
        _PROMPT_OK,
        "NO-GO: no gate log found in ai/.",
        "on branch main.",
        "working tree is clean.",
        "main is in sync with origin/main.",
        *_TOOLS_NONE,
    )


def test_gate_empty(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai, gate_empty=True)
    result = check_prerequisites(ai, tmp_path, git_state=_go_git(), tool_available=_no_tools)
    assert result.go is False
    assert result.lines == (
        _PROMPT_OK,
        "NO-GO: gate log gate-log.md is empty.",
        "on branch main.",
        "working tree is clean.",
        "main is in sync with origin/main.",
        *_TOOLS_NONE,
    )


def test_git_on_main_clean_synced_is_go(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai)
    result = check_prerequisites(ai, tmp_path, git_state=_go_git(), tool_available=_no_tools)
    assert result.go is True
    assert result.lines[2:5] == (
        "on branch main.",
        "working tree is clean.",
        "main is in sync with origin/main.",
    )


def test_git_wrong_branch_is_no_go(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai)
    state = GitState(True, "feature", True, 0, 0, True, ())
    result = check_prerequisites(ai, tmp_path, git_state=state, tool_available=_no_tools)
    assert result.go is False
    assert result.lines[2:5] == (
        "NO-GO: on branch 'feature', expected main.",
        "working tree is clean.",
        "main is in sync with origin/main.",
    )


def test_git_dirty_is_no_go(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai)
    state = GitState(True, "main", False, 0, 0, True, ())
    result = check_prerequisites(ai, tmp_path, git_state=state, tool_available=_no_tools)
    assert result.go is False
    assert result.lines[2:5] == (
        "on branch main.",
        "NO-GO: working tree is not clean.",
        "main is in sync with origin/main.",
    )


def test_git_out_of_sync_is_no_go(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai)
    state = GitState(True, "main", True, 1, 0, True, ())
    result = check_prerequisites(ai, tmp_path, git_state=state, tool_available=_no_tools)
    assert result.go is False
    assert result.lines[2:5] == (
        "on branch main.",
        "working tree is clean.",
        "NO-GO: main out of sync with origin/main (ahead=1 behind=0).",
    )


def test_git_no_origin_is_go_with_note(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai)
    state = GitState(True, "main", True, None, None, False, ())
    result = check_prerequisites(ai, tmp_path, git_state=state, tool_available=_no_tools)
    assert result.go is True
    assert result.lines[2:5] == (
        "on branch main.",
        "working tree is clean.",
        "no origin/main remote; sync check skipped (note).",
    )


def test_git_not_a_repo_is_no_go(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai)
    proj = tmp_path / "proj"
    state = GitState(False, "", True, None, None, False, ())
    result = check_prerequisites(ai, proj, git_state=state, tool_available=_no_tools)
    assert result.go is False
    assert result.lines[2] == f"NO-GO: {proj} is not a git repository."


def test_stranded_build_branch_note_keeps_go(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai)
    state = GitState(True, "main", True, 0, 0, True, ("build1",))
    result = check_prerequisites(ai, tmp_path, git_state=state, tool_available=_no_tools)
    assert result.go is True
    assert result.lines[2:6] == (
        "on branch main.",
        "working tree is clean.",
        "main is in sync with origin/main.",
        "Phase-0 signal: stranded build branch(es) build1 (note, not NO-GO).",
    )


def test_tools_all_available_folded_in(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai)
    result = check_prerequisites(ai, tmp_path, git_state=_go_git(), tool_available=_all_tools)
    assert result.go is True
    assert result.lines[5:] == (
        "fourseer: importable on this host (verdict folded in).",
        "spoke_lint: importable on this host (verdict folded in).",
        "loop_doctor: importable on this host (verdict folded in).",
    )


def test_tools_all_unavailable(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai)
    result = check_prerequisites(ai, tmp_path, git_state=_go_git(), tool_available=_no_tools)
    assert result.go is True
    assert result.lines[5:] == _TOOLS_NONE


def test_tools_mixed_probe_is_per_tool(tmp_path: Path) -> None:
    ai = tmp_path / "ai"
    _make_ai(ai)
    result = check_prerequisites(
        ai, tmp_path, git_state=_go_git(), tool_available=lambda t: t == "fourseer"
    )
    assert result.go is True
    assert result.lines[5:] == (
        "fourseer: importable on this host (verdict folded in).",
        "spoke_lint: not available on this host.",
        "loop_doctor: not available on this host.",
    )


# ---------------------------------------------------------------------------
# Cycle 4 edge-case sweep: forms the Cycle-3 dedicated tests did not pin.
# ---------------------------------------------------------------------------


def test_both_missing_reports_runner_then_gate(tmp_path: Path) -> None:
    # When neither artifact exists, the runner-prompt NO-GO line precedes the
    # gate-log NO-GO line (fixed order), and the verdict is NO-GO.
    ai = tmp_path / "ai"
    ai.mkdir()
    result = check_prerequisites(ai, tmp_path, git_state=_go_git(), tool_available=_no_tools)
    assert result.go is False
    assert result.lines[:2] == (
        "NO-GO: no runner prompt found in ai/.",
        "NO-GO: no gate log found in ai/.",
    )


def test_file_matching_prefers_sorted_first_substring_match(tmp_path: Path) -> None:
    # The gate-log search is a substring match over ``rglob`` in sorted order:
    # the first file whose name contains "gate" wins. A decoy that sorts before
    # the real log is returned (documenting the current heuristic).
    ai = tmp_path / "ai"
    ai.mkdir()
    (ai / "a-gate-notes.md").write_text("decoy\n", encoding="utf-8")
    (ai / "cycle-001-spoke-lint-gate.md").write_text("real log\n", encoding="utf-8")
    (ai / "runner-prompt.md").write_text("prompt\n", encoding="utf-8")
    result = check_prerequisites(ai, tmp_path, git_state=_go_git(), tool_available=_no_tools)
    assert result.go is True
    assert result.lines[1] == "gate log present and non-empty: a-gate-notes.md."


def test_gate_log_falls_back_to_cycle_substring(tmp_path: Path) -> None:
    # A gate log named only with "cycle" (no "gate") is still found via the
    # ``_find_ai_file(ai_dir, "cycle")`` fallback.
    ai = tmp_path / "ai"
    ai.mkdir()
    (ai / "cycle-001-spoke-lint-gate.md").write_text("log\n", encoding="utf-8")
    (ai / "runner-prompt.md").write_text("prompt\n", encoding="utf-8")
    result = check_prerequisites(ai, tmp_path, git_state=_go_git(), tool_available=_no_tools)
    assert result.go is True
    assert result.lines[1] == "gate log present and non-empty: cycle-001-spoke-lint-gate.md."


def test_multiple_stranded_branches_joined_in_one_note(tmp_path: Path) -> None:
    # Several stranded build branches are joined into a single Phase-0 note
    # (comma-separated, in the order given) and the verdict stays GO.
    ai = tmp_path / "ai"
    _make_ai(ai)
    state = GitState(True, "main", True, 0, 0, True, ("build1", "build2", "build3"))
    result = check_prerequisites(ai, tmp_path, git_state=state, tool_available=_no_tools)
    assert result.go is True
    assert result.lines[5] == (
        "Phase-0 signal: stranded build branch(es) build1, build2, build3 (note, not NO-GO)."
    )


def test_tool_fold_in_is_fixed_order_per_tool(tmp_path: Path) -> None:
    # The three tools are probed in the fixed order fourseer, spoke_lint,
    # loop_doctor, each reported independently of the others.
    ai = tmp_path / "ai"
    _make_ai(ai)
    result = check_prerequisites(
        ai,
        tmp_path,
        git_state=_go_git(),
        tool_available=lambda t: t in ("spoke_lint", "loop_doctor"),
    )
    assert result.go is True
    assert result.lines[5:] == (
        "fourseer: not available on this host.",
        "spoke_lint: importable on this host (verdict folded in).",
        "loop_doctor: importable on this host (verdict folded in).",
    )


def test_file_matching_skips_subdirectories(tmp_path: Path) -> None:
    # A *directory* whose name matches the gate substring must be skipped by
    # the file-matching heuristic (only files are candidates); the real gate
    # log file is still found.
    ai = tmp_path / "ai"
    ai.mkdir()
    (ai / "gate-notes").mkdir()  # a directory named like a gate
    (ai / "gate-notes" / "inner.md").write_text("not a gate log\n", encoding="utf-8")
    (ai / "real-gate.md").write_text("log\n", encoding="utf-8")
    (ai / "runner-prompt.md").write_text("prompt\n", encoding="utf-8")
    result = check_prerequisites(ai, tmp_path, git_state=_go_git(), tool_available=_no_tools)
    assert result.go is True
    assert result.lines[1] == "gate log present and non-empty: real-gate.md."
