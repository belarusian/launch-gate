"""In-process tests for :func:`launch_gate.cli.run`.

Drives the CLI directly (no subprocess) and pins the exit-code contract:

- ``0`` — all checks GO.
- ``1`` — any check NO-GO.
- ``2`` — usage error (missing/unrecognized subcommand, missing required flag).

Usage errors must write a message to stderr and no exception may escape.
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


def test_exit_2_no_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    rc = run([])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.err != ""


def test_exit_2_unrecognized_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    rc = run(["frobnicate"])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.err != ""


def test_exit_2_missing_project_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ai = tmp_path / "ai"
    ai.mkdir()
    rc = run(["check", "nohup ./run.sh >> cycles.out 2>&1 &", "--ai-dir", str(ai)])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.err != ""


def test_exit_2_missing_ai_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    proj = tmp_path / "myproj"
    proj.mkdir()
    rc = run(
        ["check", "nohup ./run.sh >> cycles.out 2>&1 &", "--project-dir", str(proj)]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.err != ""
