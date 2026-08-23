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
