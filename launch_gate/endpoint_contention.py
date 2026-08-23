"""Check 2 — endpoint-contention via the launch-registry (with socket fallback).

The occupancy design (documented in the README as the canonical bash block every
four driver must carry): each driver writes a heartbeat registry file at launch
and removes it on exit — ``~/.four/launches/<project>.json``. This check:

1. Parses the ``FIVE_*`` endpoint URL(s) out of the driver script.
2. Scans ``~/.four/launches/*.json``. A **fresh** entry (mtime within its own
   ``outer_wall_seconds``, default 7200) that lists a target endpoint and belongs
   to a *different* project is NO-GO (naming the occupying project). A **stale**
   entry is GO with a note.
3. When no registry file covers an endpoint, falls back to a socket snapshot:
   live ``ss -tnp`` when available on the host, else a ``--ss-file``. An
   established connection to a target endpoint owned by a pid outside the
   checked driver's lineage is NO-GO.
4. With no occupancy data at all, GO with an honest "no occupancy data" note.

The check **never guesses** occupancy: every verdict is backed by a concrete
source (a registry entry or a socket line) or an explicit "no data" note.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from launch_gate.models import CheckResult

#: Default outer wall (seconds) used to judge registry-entry freshness when an
#: entry omits ``outer_wall_seconds``.
DEFAULT_OUTER_WALL_SECONDS: int = 7200

#: A line that assigns a ``FIVE_*`` endpoint URL, e.g.
#: ``export FIVE_BASE_URL="${FIVE_BASE_URL:-http://192.168.1.161:8080/v1}"``.
_FIVE_ASSIGN_RE = re.compile(r"\bFIVE_(?:BASE|LARGE)_URL\b")

#: A URL anywhere in a line (used to pull the endpoint out of an assignment).
_URL_RE = re.compile(r"https?://\S+")


@dataclass(frozen=True)
class RegistryEntry:
    """One parsed launch-registry file.

    Attributes:
        project: The ``project`` field.
        pid: The ``pid`` field (string in the file; kept as-is).
        endpoints: The ``endpoints`` list.
        outer_wall_seconds: The ``outer_wall_seconds`` field (default applied).
        launched_at: The ``launched_at`` epoch.
        path: The registry file path it was read from.
        mtime: The file's mtime (epoch seconds).
    """

    project: str
    pid: str
    endpoints: tuple[str, ...]
    outer_wall_seconds: int
    launched_at: int
    path: str
    mtime: float


def parse_endpoints(script_text: str) -> list[str]:
    """Extract the ``FIVE_*`` endpoint URLs from a driver script.

    Args:
        script_text: The full text of the driver script.

    Returns:
        A de-duplicated, order-preserving list of endpoint URLs (the raw URL
        strings as written, e.g. ``http://192.168.1.161:8080/v1``).
    """
    seen: list[str] = []
    for line in script_text.splitlines():
        if not _FIVE_ASSIGN_RE.search(line):
            continue
        for match in _URL_RE.finditer(line):
            url = match.group(0).rstrip(".,;}\"'")
            if url not in seen:
                seen.append(url)
    return seen


def endpoint_hostport(url: str) -> str:
    """Return the ``host:port`` of an endpoint URL.

    Args:
        url: An endpoint URL such as ``http://192.168.1.161:8080/v1``.

    Returns:
        The ``host:port`` string (e.g. ``192.168.1.161:8080``). When the URL has
        no explicit port, the scheme default (``80`` for http, ``443`` for https)
        is used.
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return f"{host}:{port}"


def _parse_registry_file(path: Path) -> RegistryEntry | None:
    """Parse one registry JSON file into a :class:`RegistryEntry`.

    Returns:
        The parsed entry, or ``None`` when the file is unreadable or malformed.
    """
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    endpoints = data.get("endpoints", [])
    if not isinstance(endpoints, list):
        endpoints = []
    try:
        outer_wall = int(data.get("outer_wall_seconds", DEFAULT_OUTER_WALL_SECONDS))
    except (TypeError, ValueError):
        outer_wall = DEFAULT_OUTER_WALL_SECONDS
    try:
        launched_at = int(data.get("launched_at", 0))
    except (TypeError, ValueError):
        launched_at = 0
    return RegistryEntry(
        project=str(data.get("project", path.stem)),
        pid=str(data.get("pid", "")),
        endpoints=tuple(str(e) for e in endpoints),
        outer_wall_seconds=outer_wall,
        launched_at=launched_at,
        path=str(path),
        mtime=path.stat().st_mtime,
    )


def scan_registry(
    registry_dir: Path,
    target_endpoints: list[str],
    project_name: str,
    now: float,
) -> tuple[bool, list[str], bool]:
    """Scan the launch-registry directory for endpoint contention.

    Args:
        registry_dir: The ``~/.four/launches`` directory (may not exist).
        target_endpoints: The endpoint URLs the checked driver targets.
        project_name: The basename of the checked ``--project-dir``.
        now: The current epoch (seconds) used for freshness math.

    Returns:
        A ``(go, lines, covered)`` tuple. ``go`` is the verdict; ``lines`` the
        evidence; ``covered`` is ``True`` when at least one registry file was
        found (so the caller knows the registry was consulted, not just absent).
    """
    lines: list[str] = []
    if not registry_dir.is_dir():
        lines.append(f"no launch-registry directory at {registry_dir}.")
        return True, lines, False

    files = sorted(registry_dir.glob("*.json"))
    if not files:
        lines.append(f"launch-registry directory {registry_dir} is empty.")
        return True, lines, False

    target_set = set(target_endpoints)
    go = True
    for path in files:
        entry = _parse_registry_file(path)
        if entry is None:
            lines.append(
                f"registry file {path.name} is malformed; "
                f"skipped (not counted as occupancy)."
            )
            continue
        overlap = [e for e in entry.endpoints if e in target_set]
        if not overlap:
            lines.append(f"registry {entry.project} does not target a checked endpoint; ignored.")
            continue
        age = now - entry.mtime
        fresh = age < entry.outer_wall_seconds
        if fresh and entry.project != project_name:
            go = False
            lines.append(
                f"NO-GO: {entry.project} holds {overlap[0]} (fresh, age {int(age)}s < "
                f"wall {entry.outer_wall_seconds}s, pid {entry.pid})."
            )
        elif fresh:
            lines.append(
                f"registry {entry.project} is fresh but is this project; not contention."
            )
        else:
            lines.append(
                f"registry {entry.project} targets {overlap[0]} but is stale "
                f"(age {int(age)}s >= wall {entry.outer_wall_seconds}s); not counted."
            )
    return go, lines, True


def _ss_available() -> bool:
    """Return ``True`` when the ``ss`` binary is available on this host."""
    return shutil.which("ss") is not None


def run_ss() -> str | None:
    """Run ``ss -tnp`` and return its stdout, or ``None`` on failure."""
    if not _ss_available():
        return None
    try:
        proc = subprocess.run(
            ["ss", "-tnp"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


@dataclass(frozen=True)
class SocketLine:
    """One parsed established socket line from ``ss -tnp``.

    Attributes:
        local_hostport: The local ``host:port`` (e.g. ``192.168.1.161:8080``).
        pid: The owning pid, or ``None`` when not attributable.
        process: The owning process name, or ``None``.
    """

    local_hostport: str
    pid: int | None
    process: str | None


def parse_ss(text: str) -> list[SocketLine]:
    """Parse ``ss -tnp`` output into established socket lines.

    Only lines in the ``ESTAB`` state are returned. The columns are
    ``[Netid, State, Recv-Q, Send-Q, Local Address:Port, Peer Address:Port,
    Process]``; the state is the second column and the local address the
    fifth. The owning pid/process come from the trailing
    ``users:(("name",pid=N,...))`` field when present.

    Args:
        text: The full ``ss -tnp`` output.

    Returns:
        A list of :class:`SocketLine` for established connections.
    """
    lines: list[SocketLine] = []
    for raw in text.splitlines():
        cols = raw.split()
        if len(cols) < 5:
            continue
        state = cols[1]
        if state != "ESTAB":
            continue
        local = cols[4]
        hostport = local.rsplit(":", 1)
        if len(hostport) != 2:
            continue
        pid: int | None = None
        process: str | None = None
        m = re.search(r'users:\(\("([^"]*)",pid=(\d+)', raw)
        if m:
            process = m.group(1)
            pid = int(m.group(2))
        lines.append(
            SocketLine(
                local_hostport=f"{hostport[0]}:{hostport[1]}",
                pid=pid,
                process=process,
            )
        )
    return lines


def scan_socket(
    ss_text: str | None,
    target_endpoints: list[str],
    driver_lineage: set[int],
) -> tuple[bool, list[str], bool]:
    """Scan a socket snapshot for endpoint contention.

    Args:
        ss_text: The ``ss -tnp`` output, or ``None`` when no snapshot is
            available (neither live ``ss`` nor a ``--ss-file``).
        target_endpoints: The endpoint URLs the checked driver targets.
        driver_lineage: The set of pids belonging to the checked driver's own
            process lineage (its pid and descendants).

    Returns:
        A ``(go, lines, covered)`` tuple. ``covered`` is ``True`` when a socket
        snapshot was actually available to inspect.
    """
    lines: list[str] = []
    if ss_text is None:
        lines.append("no socket snapshot available (no live ss, no --ss-file).")
        return True, lines, False

    target_hostports = {endpoint_hostport(u) for u in target_endpoints}
    go = True
    for line in parse_ss(ss_text):
        if line.local_hostport not in target_hostports:
            continue
        if line.pid is None:
            lines.append(
                f"established connection on {line.local_hostport} with no attributable pid; "
                "cannot confirm foreign ownership; not counted."
            )
            continue
        if line.pid in driver_lineage:
            lines.append(
                f"established connection on {line.local_hostport} owned by driver lineage "
                f"(pid {line.pid}); not contention."
            )
            continue
        go = False
        owner = line.process or "unknown"
        lines.append(
            f"NO-GO: established connection on {line.local_hostport} owned by "
            f"pid {line.pid} ({owner}), outside the checked driver's lineage."
        )
    return go, lines, True


def check_endpoint_contention(
    script_text: str | None,
    registry_dir: Path,
    project_name: str,
    now: float,
    ss_file: Path | None = None,
    driver_lineage: set[int] | None = None,
) -> CheckResult:
    """Run the endpoint-contention check.

    Args:
        script_text: The driver script text (to parse ``FIVE_*`` endpoints), or
            ``None`` when ``--script`` was not supplied.
        registry_dir: The ``~/.four/launches`` directory to scan.
        project_name: The basename of the checked ``--project-dir``.
        now: The current epoch (seconds).
        ss_file: An optional pre-captured ``ss`` snapshot file.
        driver_lineage: The checked driver's own pid lineage (for socket
            attribution). Defaults to the empty set.

    Returns:
        A :class:`CheckResult` named ``endpoint-contention``.
    """
    lines: list[str] = []
    lineage = driver_lineage or set()

    if script_text is None:
        lines.append("no --script supplied; cannot parse target endpoints.")
        lines.append("no occupancy data to check; GO with no occupancy data.")
        return CheckResult("endpoint-contention", True, tuple(lines))

    endpoints = parse_endpoints(script_text)
    if not endpoints:
        lines.append("no FIVE_* endpoint URLs found in the driver script.")
        lines.append("no target endpoints to check; GO with no occupancy data.")
        return CheckResult("endpoint-contention", True, tuple(lines))

    lines.append(f"target endpoints: {', '.join(endpoints)}.")

    # 1. Registry scan.
    reg_go, reg_lines, reg_covered = scan_registry(registry_dir, endpoints, project_name, now)
    lines.extend(reg_lines)

    if reg_covered:
        # The registry was consulted; its verdict is authoritative.
        return CheckResult("endpoint-contention", reg_go, tuple(lines))

    # 2. No registry coverage for these endpoints -> socket fallback.
    lines.append("no registry coverage for the target endpoints; falling back to socket snapshot.")
    ss_text: str | None = None
    if ss_file is not None and ss_file.is_file():
        try:
            ss_text = ss_file.read_text(encoding="utf-8")
            lines.append(f"socket snapshot read from --ss-file {ss_file.name}.")
        except OSError:
            ss_text = None
    if ss_text is None:
        ss_text = run_ss()
        if ss_text is not None:
            lines.append("socket snapshot read from live `ss -tnp`.")

    sock_go, sock_lines, sock_covered = scan_socket(ss_text, endpoints, lineage)
    lines.extend(sock_lines)

    if not sock_covered:
        lines.append(
            "no occupancy data (no registry, no socket snapshot); "
            "GO with no occupancy data."
        )
    return CheckResult("endpoint-contention", sock_go, tuple(lines))
