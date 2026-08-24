"""In-process tests for :func:`launch_gate.cli.run`.

Drives the CLI directly (no subprocess) and pins the exit-code contract:

- ``0`` — all checks GO.
- ``1`` — any check NO-GO.
- ``2`` — usage error (missing/unrecognized subcommand, missing required flag).

Usage errors must write a *clear* message to stderr (naming the offending
token/flag) and no exception may escape. ``--help`` must exit ``0`` with the
usage on stdout.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from launch_gate.cli import run


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def _make_git_repo_on_main(path: Path) -> None:
    """Create a git repo on ``main`` with a clean tree (no origin/main)."""
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    (path / "README.md").write_text("hi\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "init")


def _make_ai_dir(ai_dir: Path) -> None:
    """Create a non-empty runner prompt and gate log under ``ai_dir``."""
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "runner-prompt.md").write_text("prompt body\n", encoding="utf-8")
    (ai_dir / "gate-log.md").write_text("log body\n", encoding="utf-8")


def test_exit_0_all_go(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    if shutil.which("git") is None:
        pytest.skip("git not available")
    proj = tmp_path / "myproj"
    proj.mkdir()
    _make_git_repo_on_main(proj)
    ai = tmp_path / "ai"
    _make_ai_dir(ai)

    rc = run(
        [
            "check",
            "nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
            "--project-dir",
            str(proj),
            "--ai-dir",
            str(ai),
        ],
        now=1_000_000.0,
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert "ALL-GO" in captured.out
    assert captured.err == ""


def test_exit_1_any_no_go(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # A project dir that is not a git repo makes prerequisites NO-GO.
    proj = tmp_path / "myproj"
    proj.mkdir()
    ai = tmp_path / "ai"
    _make_ai_dir(ai)

    rc = run(
        [
            "check",
            "nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
            "--project-dir",
            str(proj),
            "--ai-dir",
            str(ai),
        ],
        now=1_000_000.0,
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "NO-GO" in captured.out


# ---------------------------------------------------------------------------
# Cycle 13 — pin the usage-error + --help exit-code contract (TICKET-043).
# ---------------------------------------------------------------------------


def test_help_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    # --help writes the usage to stdout and exits 0 (no stderr, no exception).
    rc = run(["--help"])
    captured = capsys.readouterr()
    assert rc == 0
    # The subcommand usage is present on stdout.
    assert "check" in captured.out
    assert "{check}" in captured.out
    assert captured.err == ""


def test_exit_2_no_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    rc = run([])
    captured = capsys.readouterr()
    assert rc == 2
    # The stderr message names the required subcommand token.
    assert "{check}" in captured.err
    assert "required" in captured.err


def test_exit_2_unrecognized_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    rc = run(["frobnicate"])
    captured = capsys.readouterr()
    assert rc == 2
    # The stderr message names the offending token.
    assert "frobnicate" in captured.err
    assert "invalid choice" in captured.err


def test_exit_2_missing_project_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ai = tmp_path / "ai"
    ai.mkdir()
    rc = run(["check", "nohup ./run.sh >> cycles.out 2>&1 &", "--ai-dir", str(ai)])
    captured = capsys.readouterr()
    assert rc == 2
    # The stderr message names the missing flag.
    assert "--project-dir" in captured.err
    assert "required" in captured.err


def test_exit_2_missing_ai_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    proj = tmp_path / "myproj"
    proj.mkdir()
    rc = run(
        ["check", "nohup ./run.sh >> cycles.out 2>&1 &", "--project-dir", str(proj)]
    )
    captured = capsys.readouterr()
    assert rc == 2
    # The stderr message names the missing flag.
    assert "--ai-dir" in captured.err
    assert "required" in captured.err


def test_run_is_byte_identical_for_fixed_now(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two full ``run(..., now=fixed)`` calls render byte-identical reports.

    ``git_state`` and ``tool_available`` are injected (no git subprocess, no
    host import probe) and ``--script`` is omitted (so endpoint-contention
    reports "no occupancy data" without scanning the registry or ``ss``). With
    ``now`` fixed and the project/ai dirs under our control, the rendered
    report is byte-identical across runs.
    """
    from launch_gate.prerequisites import GitState

    proj = tmp_path / "myproj"
    proj.mkdir()
    ai = tmp_path / "ai"
    ai.mkdir()
    (ai / "runner-prompt.md").write_text("prompt\n", encoding="utf-8")
    (ai / "gate-log.md").write_text("log\n", encoding="utf-8")

    git_state = GitState(True, "main", True, 0, 0, True, ())

    def run_once() -> str:
        rc = run(
            [
                "check",
                "nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
                "--project-dir",
                str(proj),
                "--ai-dir",
                str(ai),
            ],
            now=1_000_000.0,
            git_state=git_state,
            tool_available=lambda tool: False,
        )
        assert rc == 0
        return capsys.readouterr().out

    first = run_once()
    second = run_once()
    assert first == second
    # The report is a real, non-trivial all-GO report.
    assert "ALL-GO" in first
    assert "launch-gate report" in first
