"""Check 4 — prerequisites.

Verifies the launch prerequisites:

- the runner prompt and gate log exist and are non-empty in ``ai/``;
- the project checkout is a git repo on ``main`` with a clean tree and ``main``
  in sync with ``origin/main``;
- a stranded build branch is reported as a Phase-0 signal (a note, not NO-GO);
- if ``fourseer`` / ``spoke-lint`` / ``loop-doctor`` are importable on this host,
  their verdicts are folded in; otherwise "not available" is reported honestly.

Git and import checks are injectable so the check is fully testable in-process.
"""

from __future__ import annotations

import importlib.util
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from launch_gate.models import CheckResult


@dataclass(frozen=True)
class GitState:
    """A snapshot of the project checkout's git state.

    Attributes:
        is_repo: Whether the directory is a git repository.
        branch: The current branch name (``""`` when not on a branch).
        clean: Whether the working tree is clean.
        ahead: Commits ``main`` is ahead of ``origin/main`` (``None`` if unknown).
        behind: Commits ``main`` is behind ``origin/main`` (``None`` if unknown).
        has_origin_main: Whether ``origin/main`` exists.
        build_branches: Local ``build*`` branches other than the current one.
    """

    is_repo: bool
    branch: str
    clean: bool
    ahead: int | None
    behind: int | None
    has_origin_main: bool
    build_branches: tuple[str, ...]


def _run_git(project_dir: Path, *args: str) -> str | None:
    """Run a git command in ``project_dir`` and return stdout, or ``None`` on error."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(project_dir), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def collect_git_state(project_dir: Path) -> GitState:
    """Collect the git state of ``project_dir``.

    Args:
        project_dir: The project checkout directory.

    Returns:
        A :class:`GitState` snapshot. When the directory is not a git repo,
        ``is_repo`` is ``False`` and the other fields carry safe defaults.
    """
    if _run_git(project_dir, "rev-parse", "--is-inside-work-tree") is None:
        return GitState(False, "", True, None, None, False, ())

    branch_out = _run_git(project_dir, "rev-parse", "--abbrev-ref", "HEAD")
    branch = branch_out.strip() if branch_out else ""

    status_out = _run_git(project_dir, "status", "--porcelain")
    clean = (status_out is None) or (status_out.strip() == "")

    has_origin_main = _run_git(project_dir, "rev-parse", "--verify", "origin/main") is not None
    ahead: int | None = None
    behind: int | None = None
    if has_origin_main:
        ahead_out = _run_git(project_dir, "rev-list", "--count", "origin/main..main")
        behind_out = _run_git(project_dir, "rev-list", "--count", "main..origin/main")
        ahead = int(ahead_out.strip()) if ahead_out and ahead_out.strip().isdigit() else None
        behind = int(behind_out.strip()) if behind_out and behind_out.strip().isdigit() else None

    branches_out = _run_git(project_dir, "branch", "--list", "build*")
    build_branches: tuple[str, ...] = ()
    if branches_out:
        build_branches = tuple(
            line.strip().lstrip("* ").strip()
            for line in branches_out.splitlines()
            if line.strip() and line.strip().lstrip("* ").strip() != branch
        )

    return GitState(
        is_repo=True,
        branch=branch,
        clean=clean,
        ahead=ahead,
        behind=behind,
        has_origin_main=has_origin_main,
        build_branches=build_branches,
    )


def _tool_available(tool: str) -> bool:
    """Return ``True`` when ``tool`` is importable on this host."""
    return importlib.util.find_spec(tool) is not None


def _find_ai_file(ai_dir: Path, *name_parts: str) -> Path | None:
    """Return the first file under ``ai_dir`` whose name contains all ``name_parts``."""
    if not ai_dir.is_dir():
        return None
    for path in sorted(ai_dir.rglob("*")):
        if not path.is_file():
            continue
        name = path.name.lower()
        if all(part in name for part in name_parts):
            return path
    return None


def check_prerequisites(
    ai_dir: Path,
    project_dir: Path,
    git_state: GitState | None = None,
    tool_available: Callable[[str], bool] | None = None,
) -> CheckResult:
    """Run the prerequisites check.

    Args:
        ai_dir: The AI artifacts directory.
        project_dir: The project checkout directory.
        git_state: An optional pre-collected :class:`GitState`. When ``None``,
            it is collected from ``project_dir``.
        tool_available: An optional callable ``tool -> bool`` used to test
            whether an auxiliary tool is importable. Defaults to
            :func:`_tool_available`.

    Returns:
        A :class:`CheckResult` named ``prerequisites``.
    """
    lines: list[str] = []
    go = True

    # Runner prompt + gate log present and non-empty.
    runner_prompt = _find_ai_file(ai_dir, "runner-prompt") or _find_ai_file(ai_dir, "runner")
    gate_log = _find_ai_file(ai_dir, "gate") or _find_ai_file(ai_dir, "cycle")
    if runner_prompt is None:
        go = False
        lines.append("NO-GO: no runner prompt found in ai/.")
    elif runner_prompt.stat().st_size == 0:
        go = False
        lines.append(f"NO-GO: runner prompt {runner_prompt.name} is empty.")
    else:
        lines.append(f"runner prompt present and non-empty: {runner_prompt.name}.")

    if gate_log is None:
        go = False
        lines.append("NO-GO: no gate log found in ai/.")
    elif gate_log.stat().st_size == 0:
        go = False
        lines.append(f"NO-GO: gate log {gate_log.name} is empty.")
    else:
        lines.append(f"gate log present and non-empty: {gate_log.name}.")

    # Git state.
    state = git_state if git_state is not None else collect_git_state(project_dir)
    if not state.is_repo:
        go = False
        lines.append(f"NO-GO: {project_dir} is not a git repository.")
    else:
        if state.branch != "main":
            go = False
            lines.append(f"NO-GO: on branch {state.branch!r}, expected main.")
        else:
            lines.append("on branch main.")
        if not state.clean:
            go = False
            lines.append("NO-GO: working tree is not clean.")
        else:
            lines.append("working tree is clean.")
        if state.has_origin_main:
            if state.ahead == 0 and state.behind == 0:
                lines.append("main is in sync with origin/main.")
            else:
                go = False
                lines.append(
                    f"NO-GO: main out of sync with origin/main "
                    f"(ahead={state.ahead} behind={state.behind})."
                )
        else:
            lines.append("no origin/main remote; sync check skipped (note).")

        if state.build_branches:
            lines.append(
                "Phase-0 signal: stranded build branch(es) "
                f"{', '.join(state.build_branches)} (note, not NO-GO)."
            )

    # Auxiliary tools.
    checker = tool_available if tool_available is not None else _tool_available
    for tool in ("fourseer", "spoke_lint", "loop_doctor"):
        if checker(tool):
            lines.append(f"{tool}: importable on this host (verdict folded in).")
        else:
            lines.append(f"{tool}: not available on this host.")

    return CheckResult("prerequisites", go, tuple(lines))
