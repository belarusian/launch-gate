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


# ---------------------------------------------------------------------------
# (h) --ss-file precedence: readable ss_file used, live ss NOT consulted;
#     ss_file None / not-a-file falls back to live ss (patched run_ss).
# ---------------------------------------------------------------------------


def _ss_two_pids_text() -> str:
    return (FIXTURES / "ss_estab_two_pids.txt").read_text(encoding="utf-8")


def test_ss_file_readable_is_used_and_live_ss_not_consulted(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    ss = _ss_file(tmp_path, _ss_foreign_text())
    with mock.patch.object(ec, "run_ss", return_value="SHOULD_NOT_APPEAR") as m:
        result = check_endpoint_contention(
            SCRIPT, reg, "myproj", NOW, ss_file=ss, driver_lineage={1, 2}
        )
    assert m.called is False
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


def test_ss_file_none_falls_back_to_live_ss(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    with mock.patch.object(ec, "run_ss", return_value=_ss_foreign_text()) as m:
        result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW, driver_lineage={1, 2})
    assert m.called is True
    assert result.go is False
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"launch-registry directory {reg} is empty.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "socket snapshot read from live `ss -tnp`.",
        f"NO-GO: established connection on {HOSTPORT} owned by pid 4242 (python3), "
        "outside the checked driver's lineage.",
        f"established connection on {HOSTPORT} with no attributable pid; "
        "cannot confirm foreign ownership; not counted.",
    )


def test_ss_file_not_a_file_falls_back_to_live_ss(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    missing = tmp_path / "does-not-exist.txt"
    with mock.patch.object(ec, "run_ss", return_value=_ss_foreign_text()) as m:
        result = check_endpoint_contention(
            SCRIPT, reg, "myproj", NOW, ss_file=missing, driver_lineage={1, 2}
        )
    assert m.called is True
    assert result.go is False
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"launch-registry directory {reg} is empty.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "socket snapshot read from live `ss -tnp`.",
        f"NO-GO: established connection on {HOSTPORT} owned by pid 4242 (python3), "
        "outside the checked driver's lineage.",
        f"established connection on {HOSTPORT} with no attributable pid; "
        "cannot confirm foreign ownership; not counted.",
    )


# ---------------------------------------------------------------------------
# (i) pid-lineage attribution edges: multi-ESTAB foreign wins; empty lineage
#     set = every attributable pid foreign; driver_lineage=None = empty set.
# ---------------------------------------------------------------------------


def test_multi_estab_lineage_and_foreign_is_no_go_foreign_wins(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    ss = _ss_file(tmp_path, _ss_two_pids_text())
    result = check_endpoint_contention(
        SCRIPT, reg, "myproj", NOW, ss_file=ss, driver_lineage={4242}
    )
    assert result.go is False
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"launch-registry directory {reg} is empty.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "socket snapshot read from --ss-file snap.txt.",
        f"established connection on {HOSTPORT} owned by driver lineage (pid 4242); not contention.",
        f"NO-GO: established connection on {HOSTPORT} owned by pid 9999 (node), "
        "outside the checked driver's lineage.",
    )


def test_empty_driver_lineage_set_marks_every_pid_foreign(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    ss = _ss_file(tmp_path, _ss_two_pids_text())
    result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW, ss_file=ss, driver_lineage=set())
    assert result.go is False
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"launch-registry directory {reg} is empty.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "socket snapshot read from --ss-file snap.txt.",
        f"NO-GO: established connection on {HOSTPORT} owned by pid 4242 (python3), "
        "outside the checked driver's lineage.",
        f"NO-GO: established connection on {HOSTPORT} owned by pid 9999 (node), "
        "outside the checked driver's lineage.",
    )


def test_driver_lineage_none_default_behaves_as_empty_set(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    ss = _ss_file(tmp_path, _ss_two_pids_text())
    result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW, ss_file=ss)
    assert result.go is False
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"launch-registry directory {reg} is empty.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "socket snapshot read from --ss-file snap.txt.",
        f"NO-GO: established connection on {HOSTPORT} owned by pid 4242 (python3), "
        "outside the checked driver's lineage.",
        f"NO-GO: established connection on {HOSTPORT} owned by pid 9999 (node), "
        "outside the checked driver's lineage.",
    )


# ---------------------------------------------------------------------------
# (j) registry `covered` semantics: non-empty registry dir is authoritative,
#     socket fallback SKIPPED entirely (no run_ss call, no fallback line).
# ---------------------------------------------------------------------------


def test_fresh_foreign_registry_covered_skips_socket_fallback(tmp_path: Path) -> None:
    reg = _write_registry(tmp_path / "launches", "other.json", "other-pipeline", 7200, NOW - 100)
    ss = _ss_file(tmp_path, _ss_foreign_text())
    with mock.patch.object(ec, "run_ss", return_value="SHOULD_NOT_APPEAR") as m:
        result = check_endpoint_contention(
            SCRIPT, reg, "myproj", NOW, ss_file=ss, driver_lineage={1, 2}
        )
    assert m.called is False
    assert result.go is False
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"NO-GO: other-pipeline holds {TARGET} (fresh, age 100s < wall 7200s, pid 4242).",
    )


def test_stale_only_registry_covered_is_go_with_no_socket_line(tmp_path: Path) -> None:
    reg = _write_registry(tmp_path / "launches", "other.json", "other-pipeline", 7200, NOW - 10_000)
    ss = _ss_file(tmp_path, _ss_foreign_text())
    with mock.patch.object(ec, "run_ss", return_value="SHOULD_NOT_APPEAR") as m:
        result = check_endpoint_contention(
            SCRIPT, reg, "myproj", NOW, ss_file=ss, driver_lineage={1, 2}
        )
    assert m.called is False
    assert result.go is True
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"registry other-pipeline targets {TARGET} but is stale "
        "(age 10000s >= wall 7200s); not counted.",
    )


# ---------------------------------------------------------------------------
# (k) no --script / no FIVE_* endpoints = GO with honest no-occupancy note
#     (no registry/socket scan at all).
# ---------------------------------------------------------------------------


def test_no_script_is_go_with_no_occupancy_note(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    result = check_endpoint_contention(None, reg, "myproj", NOW)
    assert result.go is True
    assert result.lines == (
        "no --script supplied; cannot parse target endpoints.",
        "no occupancy data to check; GO with no occupancy data.",
    )


def test_no_five_endpoints_is_go_with_no_occupancy_note(tmp_path: Path) -> None:
    reg = _empty_registry(tmp_path)
    script = 'export FIVE_MODEL="${FIVE_MODEL:-local-model}"\n'
    result = check_endpoint_contention(script, reg, "myproj", NOW)
    assert result.go is True
    assert result.lines == (
        "no FIVE_* endpoint URLs found in the driver script.",
        "no target endpoints to check; GO with no occupancy data.",
    )


# ---------------------------------------------------------------------------
# (l) multi-endpoint overlap: two distinct FIVE_* endpoints; a fresh-foreign
#     registry covering only ONE drives the verdict, the uncovered one is not
#     dropped (still listed in the target-endpoints line).
# ---------------------------------------------------------------------------

TARGET2 = "http://192.168.1.162:9000/v1"
SCRIPT_TWO = (
    f'export FIVE_BASE_URL="${{FIVE_BASE_URL:-{TARGET}}}"\n'
    f'export FIVE_LARGE_URL="${{FIVE_LARGE_URL:-{TARGET2}}}"\n'
)


def test_multi_endpoint_overlap_one_covered_drives_verdict(tmp_path: Path) -> None:
    # A fresh-foreign registry covering only TARGET (one of two) is NO-GO; the
    # uncovered TARGET2 is not dropped from the target-endpoints line.
    reg = _write_registry(
        tmp_path / "launches", "other.json", "other-pipeline", 7200, NOW - 100,
        endpoints=[TARGET],
    )
    result = check_endpoint_contention(SCRIPT_TWO, reg, "myproj", NOW)
    assert result.go is False
    assert result.lines == (
        f"target endpoints: {TARGET}, {TARGET2}.",
        f"NO-GO: other-pipeline holds {TARGET} (fresh, age 100s < wall 7200s, pid 4242).",
    )


# ---------------------------------------------------------------------------
# (m) bracketed / bare IPv6 canonical host:port (endpoint_hostport must match
#     parse_ss so the socket-overlap test matches; endpoint_hostport is total).
# ---------------------------------------------------------------------------

def _ss_ipv6_text() -> str:
    return (FIXTURES / "ss_estab_ipv6.txt").read_text(encoding="utf-8")


def test_endpoint_hostport_bracketed_ipv6_keeps_brackets() -> None:
    # urlparse would strip the brackets (-> ::1:8080); the canonical form keeps
    # them so it matches parse_ss.
    assert endpoint_hostport("http://[::1]:8080/v1") == "[::1]:8080"


def test_endpoint_hostport_bare_ipv6_is_bracketed_and_total() -> None:
    # urlparse raises ValueError on a bare-IPv6 netloc; endpoint_hostport is
    # total and canonicalizes to the bracketed form.
    assert endpoint_hostport("http://::1:8080/v1") == "[::1]:8080"


def test_endpoint_hostport_bracketed_ipv6_default_port() -> None:
    assert endpoint_hostport("http://[::1]/v1") == "[::1]:80"


def test_parse_ss_bracketed_ipv6_estab() -> None:
    lines = parse_ss(_ss_ipv6_text())
    assert lines[0] == ec.SocketLine(local_hostport="[::1]:8080", pid=4242, process="python3")


def test_endpoint_hostport_matches_parse_ss_for_bracketed_ipv6() -> None:
    # The canonical host:port of the endpoint equals the local host:port parse_ss
    # yields for a matching ESTAB line, so the overlap test matches.
    assert endpoint_hostport("http://[::1]:8080/v1") == parse_ss(_ss_ipv6_text())[0].local_hostport


def test_bracketed_ipv6_foreign_socket_line_is_no_go(tmp_path: Path) -> None:
    # A bracketed-IPv6 foreign socket line is NO-GO (not a false GO from a
    # bracket-stripping mismatch).
    script = 'export FIVE_BASE_URL="${FIVE_BASE_URL:-http://[::1]:8080/v1}"\n'
    reg = _empty_registry(tmp_path)
    ss = _ss_file(tmp_path, _ss_ipv6_text())
    result = check_endpoint_contention(
        script, reg, "myproj", NOW, ss_file=ss, driver_lineage={1, 2}
    )
    assert result.go is False
    assert result.lines == (
        "target endpoints: http://[::1]:8080/v1.",
        f"launch-registry directory {reg} is empty.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "socket snapshot read from --ss-file snap.txt.",
        "NO-GO: established connection on [::1]:8080 owned by pid 4242 (python3), "
        "outside the checked driver's lineage.",
    )


def test_bare_ipv6_endpoint_returns_verdict_without_exception(tmp_path: Path) -> None:
    # A bare-IPv6 endpoint canonicalizes to [::1]:8080 and matches the socket
    # line; the check returns a verdict (no ValueError from urlparse).
    script = 'export FIVE_BASE_URL="${FIVE_BASE_URL:-http://::1:8080/v1}"\n'
    reg = _empty_registry(tmp_path)
    ss = _ss_file(tmp_path, _ss_ipv6_text())
    result = check_endpoint_contention(
        script, reg, "myproj", NOW, ss_file=ss, driver_lineage={1, 2}
    )
    assert result.go is False
    assert result.lines == (
        "target endpoints: http://::1:8080/v1.",
        f"launch-registry directory {reg} is empty.",
        "no registry coverage for the target endpoints; falling back to socket snapshot.",
        "socket snapshot read from --ss-file snap.txt.",
        "NO-GO: established connection on [::1]:8080 owned by pid 4242 (python3), "
        "outside the checked driver's lineage.",
    )


# ---------------------------------------------------------------------------
# (n) non-list `endpoints` field (string / number / null) -> ignored, no crash.
# ---------------------------------------------------------------------------


def test_non_list_endpoints_field_is_ignored_without_crash(tmp_path: Path) -> None:
    for i, value in enumerate(("http://192.168.1.161:8080/v1", 8080, None)):
        reg = tmp_path / f"launches_{i}"
        reg.mkdir(parents=True)
        f = reg / "other.json"
        f.write_text(
            json.dumps(
                {
                    "project": "other-pipeline",
                    "pid": "4242",
                    "endpoints": value,
                    "outer_wall_seconds": 7200,
                    "launched_at": 1_699_000_000,
                }
            ),
            encoding="utf-8",
        )
        os.utime(f, (NOW - 100, NOW - 100))
        result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW)
        assert result.go is True
        assert result.lines == (
            f"target endpoints: {TARGET}.",
            "registry other-pipeline does not target a checked endpoint; ignored.",
        )


# ---------------------------------------------------------------------------
# (o) outer_wall_seconds / launched_at coercion defaults (missing / non-numeric
#     -> 7200 and 0); freshness uses mtime + coerced wall, NOT launched_at.
# ---------------------------------------------------------------------------


def test_missing_wall_and_launched_at_coerce_and_freshness_uses_mtime(tmp_path: Path) -> None:
    # outer_wall_seconds and launched_at are both absent -> coerced to 7200 and
    # 0. Freshness is judged from mtime (age 100s < wall 7200s), NOT from
    # launched_at (which is 0 and would otherwise read as stale).
    reg = tmp_path / "launches"
    reg.mkdir(parents=True)
    f = reg / "other.json"
    f.write_text(
        json.dumps({"project": "other-pipeline", "pid": "4242", "endpoints": [TARGET]}),
        encoding="utf-8",
    )
    os.utime(f, (NOW - 100, NOW - 100))
    result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW)
    assert result.go is False
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"NO-GO: other-pipeline holds {TARGET} (fresh, age 100s < wall 7200s, pid 4242).",
    )


def test_non_numeric_wall_and_launched_at_coerce_to_defaults(tmp_path: Path) -> None:
    # Non-numeric outer_wall_seconds / launched_at -> coerced to 7200 / 0; the
    # entry is still judged fresh from mtime.
    reg = tmp_path / "launches"
    reg.mkdir(parents=True)
    f = reg / "other.json"
    f.write_text(
        json.dumps(
            {
                "project": "other-pipeline",
                "pid": "4242",
                "endpoints": [TARGET],
                "outer_wall_seconds": "abc",
                "launched_at": "xyz",
            }
        ),
        encoding="utf-8",
    )
    os.utime(f, (NOW - 100, NOW - 100))
    result = check_endpoint_contention(SCRIPT, reg, "myproj", NOW)
    assert result.go is False
    assert result.lines == (
        f"target endpoints: {TARGET}.",
        f"NO-GO: other-pipeline holds {TARGET} (fresh, age 100s < wall 7200s, pid 4242).",
    )
