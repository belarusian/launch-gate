"""Check 3 — wall-sizing (B1).

The outer wall (the ``perl -e 'alarm shift; exec @ARGV' <wall>`` seconds) must
be large enough to contain the inner passes. When the ``ai/`` dir contains
observed inner-pass durations (a fourseer report's ``Duration (s)`` column, or
durations derivable from ``cycles.out`` timestamps), require
``outer_wall >= 3 * max_observed``. With no observations, GO with a note that
the conservative default row applies.
"""

from __future__ import annotations

import re
from pathlib import Path

from launch_gate.models import CheckResult

#: The ``perl -e 'alarm shift; exec @ARGV' <N> ...`` outer-wall invocation.
_OUTER_WALL_RE = re.compile(r"alarm\s+shift;\s*exec\s+@ARGV['\"]?\s+(\d+)")

#: The ``--inner-seconds <N>`` argument.
_INNER_SECONDS_RE = re.compile(r"--inner-seconds\s+(\d+)")

#: A fourseer report row: ``| 13 | exit:task_complete | 59 | 1358 | trajectory_0024.json |``.
#: The Duration (s) column is the 4th cell; ``-`` means no observation.
_FOURSEER_ROW_RE = re.compile(
    r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+|-)\s*\|\s*(\d+|-)\s*\|\s*([^|]+?)\s*\|"
)

#: A cycles.out cycle-marker line with a UTC timestamp:
#: ``========== CYCLE 3  15:19:44Z ==========``.
_CYCLES_TS_RE = re.compile(r"^={4,}\s*CYCLE\s+\d+\s+(\d{2}):(\d{2}):(\d{2})Z")


def parse_outer_wall(script_text: str) -> int | None:
    """Return the outer wall (perl alarm seconds) from a driver script.

    Args:
        script_text: The full text of the driver script.

    Returns:
        The outer wall in seconds, or ``None`` when not found.
    """
    m = _OUTER_WALL_RE.search(script_text)
    if m:
        return int(m.group(1))
    return None


def parse_inner_seconds(script_text: str) -> int | None:
    """Return the ``--inner-seconds`` value from a driver script.

    Args:
        script_text: The full text of the driver script.

    Returns:
        The inner seconds, or ``None`` when not found.
    """
    m = _INNER_SECONDS_RE.search(script_text)
    if m:
        return int(m.group(1))
    return None


def durations_from_fourseer(text: str) -> list[int]:
    """Extract observed inner-pass durations from a fourseer report.

    Args:
        text: The full text of a ``fourseer report`` (Per-Cycle Metrics table).

    Returns:
        A list of observed durations (seconds). Rows whose Duration cell is
        ``-`` (no observation) are skipped.
    """
    durations: list[int] = []
    for line in text.splitlines():
        m = _FOURSEER_ROW_RE.match(line.strip())
        if not m:
            continue
        duration_cell = m.group(4)
        if duration_cell.isdigit():
            durations.append(int(duration_cell))
    return durations


def durations_from_cycles_out(text: str) -> list[int]:
    """Derive per-cycle durations from ``cycles.out`` timestamps.

    Each ``========== CYCLE N <HH:MM:SS>Z ==========`` start marker is paired
    with the next start marker (or the matching ``done`` marker); the gap between
    consecutive start markers approximates that cycle's wall time.

    Args:
        text: The full text of a ``cycles.out``.

    Returns:
        A list of per-cycle durations (seconds) derived from consecutive start
        markers. Empty when fewer than two start markers are present.
    """
    stamps: list[int] = []
    for line in text.splitlines():
        m = _CYCLES_TS_RE.match(line.strip())
        if m:
            h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
            stamps.append(h * 3600 + mi * 60 + s)
    durations: list[int] = []
    for a, b in zip(stamps, stamps[1:], strict=False):
        durations.append(b - a)
    return durations


def _find_fourseer_report(ai_dir: Path) -> Path | None:
    """Return the first ``*fourseer*report*`` file under ``ai_dir``, if any."""
    if not ai_dir.is_dir():
        return None
    candidates = sorted(
        p for p in ai_dir.rglob("*") if p.is_file() and "fourseer" in p.name and "report" in p.name
    )
    return candidates[0] if candidates else None


def _find_cycles_out(ai_dir: Path, project_dir: Path) -> Path | None:
    """Return a ``cycles.out`` under ``ai_dir`` or ``project_dir``, if any."""
    for base in (ai_dir, project_dir):
        if not base.is_dir():
            continue
        for name in ("cycles.out", "ai/cycles.out"):
            candidate = base / name
            if candidate.is_file():
                return candidate
    return None


def check_wall_sizing(
    script_text: str | None,
    ai_dir: Path,
    project_dir: Path,
) -> CheckResult:
    """Run the wall-sizing (B1) check.

    Args:
        script_text: The driver script text (to parse the outer wall and
            ``--inner-seconds``), or ``None`` when ``--script`` was not supplied.
        ai_dir: The AI artifacts directory (may hold a fourseer report and/or
            ``cycles.out``).
        project_dir: The project checkout directory (may hold ``cycles.out``).

    Returns:
        A :class:`CheckResult` named ``wall-sizing``.
    """
    lines: list[str] = []

    outer_wall: int | None = None
    inner_seconds: int | None = None
    if script_text is not None:
        outer_wall = parse_outer_wall(script_text)
        inner_seconds = parse_inner_seconds(script_text)
        if outer_wall is not None:
            lines.append(f"outer wall (perl alarm): {outer_wall}s.")
        else:
            lines.append("no outer wall (perl alarm) found in the driver script.")
        if inner_seconds is not None:
            lines.append(f"--inner-seconds: {inner_seconds}s.")
    else:
        lines.append("no --script supplied; cannot parse the outer wall.")

    # Gather observed inner-pass durations.
    observations: list[int] = []
    source_notes: list[str] = []

    fourseer_path = _find_fourseer_report(ai_dir)
    if fourseer_path is not None:
        try:
            fourseer_text = fourseer_path.read_text(encoding="utf-8")
        except OSError:
            fourseer_text = ""
        durs = durations_from_fourseer(fourseer_text)
        if durs:
            observations.extend(durs)
            source_notes.append(f"fourseer report {fourseer_path.name}: {len(durs)} duration(s).")
        else:
            source_notes.append(
                f"fourseer report {fourseer_path.name}: "
                f"no Duration (s) observations."
            )

    cycles_path = _find_cycles_out(ai_dir, project_dir)
    if cycles_path is not None:
        try:
            cycles_text = cycles_path.read_text(encoding="utf-8")
        except OSError:
            cycles_text = ""
        durs = durations_from_cycles_out(cycles_text)
        if durs:
            observations.extend(durs)
            source_notes.append(f"cycles.out {cycles_path.name}: {len(durs)} derived duration(s).")

    if observations:
        max_observed = max(observations)
        lines.append(f"observed inner-pass durations: {sorted(observations)}.")
        for note in source_notes:
            lines.append(f"source: {note}")
        required = 3 * max_observed
        if outer_wall is None:
            lines.append("no outer wall to compare against; cannot verify sizing.")
            return CheckResult("wall-sizing", False, tuple(lines))
        if outer_wall >= required:
            lines.append(
                f"outer wall {outer_wall}s >= 3 * max_observed {max_observed}s ({required}s). GO."
            )
            return CheckResult("wall-sizing", True, tuple(lines))
        lines.append(
            f"outer wall {outer_wall}s < 3 * max_observed {max_observed}s ({required}s). NO-GO."
        )
        return CheckResult("wall-sizing", False, tuple(lines))

    # No observations.
    lines.append(
        "no observed inner-pass durations found "
        "(no fourseer Duration, no cycles.out timestamps)."
    )
    for note in source_notes:
        lines.append(f"source: {note}")
    lines.append("conservative default row applies; GO with no observations.")
    return CheckResult("wall-sizing", True, tuple(lines))
