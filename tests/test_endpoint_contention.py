"""Unit tests for :mod:`launch_gate.endpoint_contention` (check 2).

Pins the exact verdict (``go``) **and** the exact evidence ``lines`` for the
full endpoint-contention classification matrix (brief cases (a)-(g)), plus the
``parse_endpoints`` / ``endpoint_hostport`` / ``parse_ss`` helpers.

The tests are deterministic: registry dirs and ``ss`` files live under
``tmp_path``, ``now`` and ``driver_lineage`` are injected, and the live
``ss`` shell-out is never exercised (``run_ss`` is patched to ``None`` for the
"no socket snapshot" paths; the socket-fallback cases inject an ``ss_file``).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

from launch_gate import endpoint_contention as ec
from launch_gate.endpoint_contention import (
    check_endpoint_contention,
    endpoint_hostport,
    parse_endpoints,
    parse_ss,
)

FIXTURES = Path(__file__).parent / "fixtures"

#: The single target endpoint used throughout (the seed driver's FIVE_BASE_URL).
TARGET = "http://192.168.1.161:8080/v1"
HOSTPORT = "192.168.1.161:8080"

#: A fixed "now" so registry-age math is deterministic.
NOW = 1_700_000_000.0

#: A driver script carrying the seed FIVE_* export dialect.
SCRIPT = (
    'export FIVE_MODEL="${FIVE_MODEL:-local-model}"\n'
    f'export FIVE_BASE_URL="${{FIVE_BASE_URL:-{TARGET}}}"\n'
    f'export FIVE_LARGE_URL="${{FIVE_LARGE_URL:-{TARGET}}}"\n'
)


def _driver_script_text() -> str:
    return (FIXTURES / "driver_five_endpoints.sh").read_text(encoding="utf-8")


def _ss_foreign_text() -> str:
    return (FIXTURES / "ss_estab_foreign.txt").read_text(encoding="utf-8")


def _write_registry(
    reg_dir: Path,
    name: str,
    project: str,
    wall: int,
    mtime: float,
    endpoints: list[str] | None = None,
) -> Path:
    """Write one registry JSON file with a controlled mtime and return the dir."""
    reg_dir.mkdir(parents=True, exist_ok=True)
    f = reg_dir / name
    f.write_text(
        json.dumps(
            {
                "project": project,
                "pid": "4242",
                "endpoints": endpoints or [TARGET],
                "outer_wall_seconds": wall,
                "launched_at": 1_699_000_000,
            }
        ),
        encoding="utf-8",
    )
    os.utime(f, (mtime, mtime))
    return reg_dir


def _empty_registry(tmp_path: Path) -> Path:
    d = tmp_path / "launches"
    d.mkdir(parents=True)
    return d


def _ss_file(tmp_path: Path, text: str, name: str = "snap.txt") -> Path:
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# (a) parse_endpoints — FIVE_* URL extraction (dedup, order, punctuation).
# ---------------------------------------------------------------------------


def test_parse_endpoints_seed_dialect_is_clean() -> None:
    # The seed dialect line carries a trailing ``}"`` that must be stripped.
    line = f'export FIVE_BASE_URL="${{FIVE_BASE_URL:-{TARGET}}}"'
    assert parse_endpoints(line) == [TARGET]


def test_parse_endpoints_dedup_and_order_preserving() -> None:
    script = (
        f'export FIVE_BASE_URL="${{FIVE_BASE_URL:-{TARGET}}}"\n'
        'export FIVE_LARGE_URL="${FIVE_LARGE_URL:-http://192.168.1.162:9000/v1}"\n'
        f'export FIVE_BASE_URL="${{FIVE_BASE_URL:-{TARGET}}}"\n'
    )
    assert parse_endpoints(script) == [TARGET, "http://192.168.1.162:9000/v1"]


def test_parse_endpoints_tolerates_trailing_punctuation() -> None:
    script = f'export FIVE_BASE_URL="{TARGET}."  # base endpoint\n'
    assert parse_endpoints(script) == [TARGET]


def test_parse_endpoints_ignores_non_url_five_exports() -> None:
    # FIVE_MODEL / FIVE_LARGE_MODEL are not URLs and must not be picked up.
    script = (
        'export FIVE_MODEL="${FIVE_MODEL:-local-model}"\n'
        'export FIVE_LARGE_MODEL="${FIVE_LARGE_MODEL:-local-model}"\n'
    )
    assert parse_endpoints(script) == []


def test_parse_endpoints_from_committed_fixture() -> None:
    # The committed driver fixture (both FIVE_* URLs identical) dedups to one.
    assert parse_endpoints(_driver_script_text()) == [TARGET]


# ---------------------------------------------------------------------------
# endpoint_hostport — host:port with scheme-default ports.
# ---------------------------------------------------------------------------


def test_endpoint_hostport_explicit_port() -> None:
    assert endpoint_hostport(TARGET) == HOSTPORT


def test_endpoint_hostport_https_default_port() -> None:
    assert endpoint_hostport("https://example.com/v1") == "example.com:443"


def test_endpoint_hostport_http_default_port() -> None:
    assert endpoint_hostport("http://example.com/v1") == "example.com:80"


# ---------------------------------------------------------------------------
# parse_ss — real `ss -tnp` layout (Netid, State, Recv-Q, Send-Q, Local, ...).
# ---------------------------------------------------------------------------


def test_parse_ss_estab_with_pid() -> None:
    lines = parse_ss(_ss_foreign_text())
    assert lines[0] == ec.SocketLine(local_hostport=HOSTPORT, pid=4242, process="python3")


def test_parse_ss_estab_without_pid() -> None:
    lines = parse_ss(_ss_foreign_text())
    assert lines[1] == ec.SocketLine(local_hostport=HOSTPORT, pid=None, process=None)


def test_parse_ss_excludes_non_estab() -> None:
    # The LISTEN line must not be returned; only the two ESTAB lines are.
    assert len(parse_ss(_ss_foreign_text())) == 2


def test_parse_ss_empty_text() -> None:
    assert parse_ss("") == []


# ---------------------------------------------------------------------------
# (b) registry FRESH + foreign project + overlapping endpoint = NO-GO.
# ---------------------------------------------------------------------------


def test_fresh_foreign_registry_is_no_go(tmp_path: Path) -> None:
    reg = _write_registry(tmp_path / "launches", "other.json", "other-pipeline", 7200, NOW - 100)
    result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW)
    assert result.go is False
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"NO-GO: other-pipeline holds {TARGET} (fresh, age 100s < wall 7200s, pid 4242).",
    )


# ---------------------------------------------------------------------------
# (c) registry FRESH + same project = GO (not contention).
# ---------------------------------------------------------------------------


def test_fresh_same_project_registry_is_go(tmp_path: Path) -> None:
    reg = _write_registry(tmp_path / "launches", "myproj.json", "myproj", 7200, NOW - 100)
    result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW)
    assert result.go is True
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        "registry myproj is fresh but is this project; not contention.",
    )


# ---------------------------------------------------------------------------
# (d) registry STALE (age >= wall) = GO with a note.
# ---------------------------------------------------------------------------


def test_stale_registry_is_go_with_note(tmp_path: Path) -> None:
    reg = _write_registry(tmp_path / "launches", "other.json", "other-pipeline", 7200, NOW - 10_000)
    result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW)
    assert result.go is True
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"registry other-pipeline targets {TARGET} but is stale "
        "(age 10000s >= wall 7200s); not counted.",
    )


# ---------------------------------------------------------------------------
# (e) registry absent / empty / malformed = GO (never-guess, honest note).
# ---------------------------------------------------------------------------


def test_absent_registry_dir_is_go(tmp_path: Path) -> None:
    reg = tmp_path / "nope"  # does not exist
    with mock.patch.object(ec, "run_ss", return_value=None):
        result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW)
    assert result.go is True
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"no launch-registry directory at {reg}.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "no socket snapshot available (no live ss, no --ss-file).",
        "no occupancy data (no registry, no socket snapshot); GO with no occupancy data.",
    )


def test_empty_registry_dir_is_go(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    with mock.patch.object(ec, "run_ss", return_value=None):
        result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW)
    assert result.go is True
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"launch-registry directory {reg} is empty.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "no socket snapshot available (no live ss, no --ss-file).",
        "no occupancy data (no registry, no socket snapshot); GO with no occupancy data.",
    )


def test_malformed_registry_file_is_go(tmp_path: Path) -> None:
    reg = tmp_path / "launches"
    reg.mkdir(parents=True)
    (reg / "bad.json").write_text("{not json", encoding="utf-8")
    result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW)
    assert result.go is True
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        "registry file bad.json is malformed; skipped (not counted as occupancy).",
    )


# ---------------------------------------------------------------------------
# (f) socket fallback: foreign pid = NO-GO; lineage pid = GO; no pid = GO.
# ---------------------------------------------------------------------------


def test_socket_foreign_pid_is_no_go(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    ss = _ss_file(tmp_path, _ss_foreign_text())
    result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW, ss_file=ss, driver_lineage={1, 2})
    assert result.go is False
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"launch-registry directory {reg} is empty.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "socket snapshot read from --ss-file snap.txt.",
        f"NO-GO: established connection on {HOSTPORT} owned by pid 4242 (python3), "
        "outside the checked driver's lineage.",
        f"established connection on {HOSTPORT} with no attributable pid; "
        "cannot confirm foreign ownership; not counted.",
    )


def test_socket_lineage_pid_is_go(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    ss = _ss_file(tmp_path, _ss_foreign_text())
    result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW, ss_file=ss, driver_lineage={4242})
    assert result.go is True
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"launch-registry directory {reg} is empty.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "socket snapshot read from --ss-file snap.txt.",
        f"established connection on {HOSTPORT} owned by driver lineage (pid 4242); not contention.",
        f"established connection on {HOSTPORT} with no attributable pid; "
        "cannot confirm foreign ownership; not counted.",
    )


def test_socket_no_attributable_pid_is_go(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    ss_text = (
        "Netid State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process\n"
        f"tcp   ESTAB  0      0      {HOSTPORT}  10.0.0.6:51235\n"
    )
    ss = _ss_file(tmp_path, ss_text)
    result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW, ss_file=ss, driver_lineage={1, 2})
    assert result.go is True
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"launch-registry directory {reg} is empty.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "socket snapshot read from --ss-file snap.txt.",
        f"established connection on {HOSTPORT} with no attributable pid; "
        "cannot confirm foreign ownership; not counted.",
    )


# ---------------------------------------------------------------------------
# (g) no registry coverage AND no socket snapshot = GO with no-occupancy note.
# ---------------------------------------------------------------------------


def test_no_occupancy_data_is_go(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    with mock.patch.object(ec, "run_ss", return_value=None):
        result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW)
    assert result.go is True
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"launch-registry directory {reg} is empty.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "no socket snapshot available (no live ss, no --ss-file).",
        "no occupancy data (no registry, no socket snapshot); GO with no occupancy data.",
    )
