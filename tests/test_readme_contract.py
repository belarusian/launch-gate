"""Golden contract tests pinning the README's documented contracts to code.

Two documented contracts are pinned here so a future README/code drift is
caught by the gate:

1. **The check command** (README "The check command"): the ``check``
   subcommand takes a ``launch_line`` positional, ``--project-dir`` and
   ``--ai-dir`` are REQUIRED, ``--script`` and ``--ss-file`` are optional,
   there is no user-facing ``--now`` flag, and the exit-code contract is
   ``0`` = all-GO, ``1`` = any-NO-GO, ``2`` = usage error.

2. **The canonical launch-registry block** (README "Canonical
   launch-registry block"): the JSON carries exactly the five documented
   fields (``project``, ``pid``, ``endpoints``, ``outer_wall_seconds``,
   ``launched_at``); ``pid`` is a string in the file (a numeric pid is
   tolerated and coerced to a string); ``outer_wall_seconds`` defaults to
   ``7200`` when absent; ``launched_at`` defaults to ``0``; and freshness is
   judged from the file **mtime** + ``outer_wall_seconds`` (NOT
   ``launched_at``). The registry dir is ``~/.four/launches``.

These tests are deterministic: no subprocess, no real clock (``now`` and
registry mtimes are injected), no live ``ss``. They intentionally introspect
the argparse parser (a private but stable CPython surface) to pin the
*documented* flag contract exactly.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
from pathlib import Path

import pytest

from launch_gate import endpoint_contention as ec
from launch_gate.cli import _registry_dir, build_parser, run
from launch_gate.prerequisites import GitState

#: The five documented registry-block fields, in the README's order.
DOCUMENTED_REGISTRY_FIELDS = (
    "project",
    "pid",
    "endpoints",
    "outer_wall_seconds",
    "launched_at",
)

#: The documented default outer wall (seconds).
DOCUMENTED_DEFAULT_OUTER_WALL = 7200

#: The documented registry directory (relative to ``$HOME``).
DOCUMENTED_REGISTRY_DIR = Path(".four") / "launches"

#: The documented check-command flags.
REQUIRED_FLAGS = ("--project-dir", "--ai-dir")
OPTIONAL_FLAGS = ("--script", "--ss-file")
ALL_FLAGS = REQUIRED_FLAGS + OPTIONAL_FLAGS


# ---------------------------------------------------------------------------
# 1. The check command — exact parser flags (the documented contract).
# ---------------------------------------------------------------------------


def _subparsers_action(parser):
    """Return the ``_SubParsersAction`` from a top-level parser."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise AssertionError("no subparsers action found")


def _check_subparser():
    """Return the ``check`` subparser from :func:`build_parser`."""
    parser = build_parser()
    sub = _subparsers_action(parser)
    check = sub.choices["check"]
    return parser, check


def _flag_actions(check):
    """Map each option string to its argparse action on the ``check`` parser.

    The auto-added ``-h``/``--help`` action is excluded: it is not part of the
    documented check-command contract.
    """
    flags = {}
    for action in check._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        for opt in action.option_strings:
            flags[opt] = action
    return flags


def test_check_subcommand_exists_and_is_required() -> None:
    parser, check = _check_subparser()
    sub = _subparsers_action(parser)
    # The only subcommand is ``check`` and it is required (no subcommand -> usage error).
    assert set(sub.choices) == {"check"}
    assert sub.required is True
    assert check is not None


def test_check_positional_is_launch_line() -> None:
    _, check = _check_subparser()
    positionals = [a for a in check._actions if not a.option_strings]
    assert [a.dest for a in positionals] == ["launch_line"]


def test_check_flags_match_documented_set_exactly() -> None:
    _, check = _check_subparser()
    flags = _flag_actions(check)
    # Exactly the four documented flags — no more, no fewer.
    assert set(flags) == set(ALL_FLAGS)


def test_check_required_and_optional_flags_match_documented() -> None:
    _, check = _check_subparser()
    flags = _flag_actions(check)
    for flag in REQUIRED_FLAGS:
        assert flags[flag].required is True, f"{flag} must be required"
    for flag in OPTIONAL_FLAGS:
        assert flags[flag].required is False, f"{flag} must be optional"


def test_check_has_no_user_facing_now_flag() -> None:
    # The README documents no ``--now`` flag; freshness ``now`` is internal only.
    _, check = _check_subparser()
    flags = _flag_actions(check)
    assert "--now" not in flags
    assert not any("now" in opt for opt in flags)


# ---------------------------------------------------------------------------
# 1b. The check command — the documented exit-code contract (0 / 1 / 2).
# ---------------------------------------------------------------------------


def _git_state_on_main() -> GitState:
    """A clean, on-``main`` checkout with no origin/main (a note, not NO-GO)."""
    return GitState(
        is_repo=True,
        branch="main",
        clean=True,
        ahead=None,
        behind=None,
        has_origin_main=False,
        build_branches=(),
    )


def _git_state_not_a_repo() -> GitState:
    """A directory that is not a git repository (prerequisites NO-GO)."""
    return GitState(
        is_repo=False,
        branch="",
        clean=True,
        ahead=None,
        behind=None,
        has_origin_main=False,
        build_branches=(),
    )


def _make_ai_dir(ai_dir: Path) -> None:
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "runner-prompt.md").write_text("prompt body\n", encoding="utf-8")
    (ai_dir / "gate-log.md").write_text("log body\n", encoding="utf-8")


def test_exit_code_0_all_go(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # All four checks GO. The git state is injected (no subprocess, no real
    # clock): a clean checkout on main with no origin/main is a note, not NO-GO.
    proj = tmp_path / "myproj"
    proj.mkdir()
    ai = tmp_path / "ai"
    _make_ai_dir(ai)
    rc = run(
        [
            "check",
            "nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
            "--project-dir", str(proj),
            "--ai-dir", str(ai),
        ],
        now=1_000_000.0,
        git_state=_git_state_on_main(),
    )
    assert rc == 0
    assert "ALL-GO" in capsys.readouterr().out


def test_exit_code_1_any_no_go(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # A project dir that is not a git repo makes prerequisites NO-GO. The git
    # state is injected (no subprocess, no real clock).
    proj = tmp_path / "myproj"
    proj.mkdir()
    ai = tmp_path / "ai"
    _make_ai_dir(ai)
    rc = run(
        [
            "check",
            "nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
            "--project-dir", str(proj),
            "--ai-dir", str(ai),
        ],
        now=1_000_000.0,
        git_state=_git_state_not_a_repo(),
    )
    assert rc == 1
    assert "NO-GO" in capsys.readouterr().out


@pytest.mark.parametrize(
    "argv",
    [
        [],  # no subcommand
        ["frobnicate"],  # unrecognized subcommand
        ["check", "nohup ./run.sh >> cycles.out 2>&1 &", "--ai-dir", "/tmp/ai"],  # missing --project-dir
        ["check", "nohup ./run.sh >> cycles.out 2>&1 &", "--project-dir", "/tmp/p"],  # missing --ai-dir
    ],
    ids=["no-subcommand", "bad-subcommand", "missing-project-dir", "missing-ai-dir"],
)
def test_exit_code_2_usage_error(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    rc = run(argv, now=1_000_000.0)
    assert rc == 2
    assert capsys.readouterr().err != ""


# ---------------------------------------------------------------------------
# 2. The canonical launch-registry block — field set + semantics.
# ---------------------------------------------------------------------------


def _write_registry(reg_dir: Path, name: str, data: dict, mtime: float) -> Path:
    """Write a registry JSON file with a controlled mtime and return its path."""
    reg_dir.mkdir(parents=True, exist_ok=True)
    f = reg_dir / name
    f.write_text(json.dumps(data), encoding="utf-8")
    os.utime(f, (mtime, mtime))
    return f


def test_registry_dataclass_field_set_matches_documented() -> None:
    # The RegistryEntry content fields (excluding the parser-added path/mtime)
    # are exactly the five documented fields, in the README's order.
    fields = [f.name for f in dataclasses.fields(ec.RegistryEntry)]
    content_fields = [f for f in fields if f not in ("path", "mtime")]
    assert content_fields == list(DOCUMENTED_REGISTRY_FIELDS)


def test_registry_block_parses_all_five_fields(tmp_path: Path) -> None:
    f = _write_registry(
        tmp_path,
        "myproj.json",
        {
            "project": "myproj",
            "pid": "4242",
            "endpoints": ["http://192.168.1.161:8080/v1"],
            "outer_wall_seconds": 7200,
            "launched_at": 1_700_000_000,
        },
        mtime=1_700_000_000.0,
    )
    entry = ec._parse_registry_file(f)
    assert entry is not None
    assert entry.project == "myproj"
    assert entry.pid == "4242"
    assert entry.endpoints == ("http://192.168.1.161:8080/v1",)
    assert entry.outer_wall_seconds == 7200
    assert entry.launched_at == 1_700_000_000


def test_registry_pid_is_string_in_file(tmp_path: Path) -> None:
    # The documented contract: pid is a string in the file.
    f = _write_registry(
        tmp_path, "p.json", {"project": "p", "pid": "4242"}, mtime=1_700_000_000.0
    )
    entry = ec._parse_registry_file(f)
    assert entry is not None
    assert isinstance(entry.pid, str)
    assert entry.pid == "4242"


def test_registry_numeric_pid_is_tolerated_and_coerced_to_string(tmp_path: Path) -> None:
    # A driver that writes a bare numeric pid (the pre-fix bash block) is
    # tolerated: the parser coerces it to a string.
    f = _write_registry(
        tmp_path, "p.json", {"project": "p", "pid": 4242}, mtime=1_700_000_000.0
    )
    entry = ec._parse_registry_file(f)
    assert entry is not None
    assert isinstance(entry.pid, str)
    assert entry.pid == "4242"


def test_registry_default_outer_wall_is_7200_when_absent(tmp_path: Path) -> None:
    f = _write_registry(
        tmp_path, "p.json", {"project": "p", "pid": "1"}, mtime=1_700_000_000.0
    )
    entry = ec._parse_registry_file(f)
    assert entry is not None
    assert entry.outer_wall_seconds == DOCUMENTED_DEFAULT_OUTER_WALL


def test_registry_default_outer_wall_is_7200_when_non_numeric(tmp_path: Path) -> None:
    f = _write_registry(
        tmp_path,
        "p.json",
        {"project": "p", "pid": "1", "outer_wall_seconds": "not-a-number"},
        mtime=1_700_000_000.0,
    )
    entry = ec._parse_registry_file(f)
    assert entry is not None
    assert entry.outer_wall_seconds == DOCUMENTED_DEFAULT_OUTER_WALL


def test_registry_default_launched_at_is_0_when_absent(tmp_path: Path) -> None:
    f = _write_registry(
        tmp_path, "p.json", {"project": "p", "pid": "1"}, mtime=1_700_000_000.0
    )
    entry = ec._parse_registry_file(f)
    assert entry is not None
    assert entry.launched_at == 0


def test_registry_freshness_uses_mtime_not_launched_at(tmp_path: Path) -> None:
    # A file whose launched_at is ancient but whose mtime is fresh is FRESH
    # (freshness is mtime + outer_wall, NOT launched_at).
    fresh_mtime = 1_700_000_000.0
    now = 1_700_000_100.0  # 100s after mtime -> fresh (wall 7200)
    f = _write_registry(
        tmp_path,
        "other.json",
        {
            "project": "other",
            "pid": "1",
            "endpoints": ["http://192.168.1.161:8080/v1"],
            "outer_wall_seconds": 7200,
            "launched_at": 1_000_000_000,  # ancient, but must be ignored
        },
        mtime=fresh_mtime,
    )
    go, lines, covered = ec.scan_registry(tmp_path, ["http://192.168.1.161:8080/v1"], "myproj", now)
    assert covered is True
    assert go is False  # fresh foreign entry -> NO-GO (proves mtime, not launched_at, was used)
    assert any("fresh" in line for line in lines)


def test_registry_stale_by_mtime_even_with_fresh_launched_at(tmp_path: Path) -> None:
    # A file whose launched_at is recent but whose mtime is old is STALE.
    now = 1_700_000_000.0
    f = _write_registry(
        tmp_path,
        "other.json",
        {
            "project": "other",
            "pid": "1",
            "endpoints": ["http://192.168.1.161:8080/v1"],
            "outer_wall_seconds": 7200,
            "launched_at": int(now),  # recent, but must be ignored
        },
        mtime=now - 10_000,  # 10000s old -> stale (wall 7200)
    )
    go, lines, covered = ec.scan_registry(tmp_path, ["http://192.168.1.161:8080/v1"], "myproj", now)
    assert covered is True
    assert go is True  # stale -> not counted
    assert any("stale" in line for line in lines)


def test_registry_dir_is_home_four_launches() -> None:
    # The documented path: ~/.four/launches/<project>.json (dir part).
    assert _registry_dir() == Path.home() / DOCUMENTED_REGISTRY_DIR
