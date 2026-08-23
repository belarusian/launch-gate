"""Check 1 — redirect-safety.

A *continuation* launch (the driver is being re-run for a later cycle, or a
``cycles.out`` already carries ``========== CYCLE N ==========`` markers) must
**append** (``>>``) to ``cycles.out``. A bare ``>`` against an existing marker
file would truncate the history and is NO-GO. A *first* launch (``>`` with no
prior history) is GO.

This module is pure: it inspects the launch line string and the (optional)
existing ``cycles.out`` text and returns a :class:`~launch_gate.models.CheckResult`.
"""

from __future__ import annotations

import re

from launch_gate.models import CheckResult

#: The cycle-marker dialect used by four drivers (see the seed cycles.out.sample).
#: A line like ``========== CYCLE 3  14:27:19Z ==========``.
_MARKER_RE = re.compile(r"^={4,}\s*CYCLE\s+\d+")


def has_cycle_markers(cycles_out_text: str) -> bool:
    """Return ``True`` when ``cycles_out_text`` carries a cycle-marker line.

    Args:
        cycles_out_text: The full text of an existing ``cycles.out`` (may be empty).

    Returns:
        ``True`` when at least one line matches the cycle-marker dialect.
    """
    for line in cycles_out_text.splitlines():
        if _MARKER_RE.match(line.strip()):
            return True
    return False


def _redirect_to_cycles(launch_line: str) -> str | None:
    """Classify how the launch line redirects into ``cycles.out``.

    Returns:
        ``"append"`` when the line uses ``>>`` to ``cycles.out``, ``"truncate"``
        when it uses a bare ``>`` to ``cycles.out``, or ``None`` when the line
        does not redirect into ``cycles.out`` at all.
    """
    # An append redirect into cycles.out.
    if re.search(r">>\s*cycles\.out", launch_line):
        return "append"
    # A bare (truncate) redirect into cycles.out. Match ``>`` not preceded by
    # another ``>`` (an append) and not preceded by ``2`` (a stderr-only
    # redirect like ``2> cycles.out`` is not a truncate of the stdout history).
    if re.search(r"(?<![2>])>\s*cycles\.out", launch_line):
        return "truncate"
    return None


def check_redirect_safety(launch_line: str, cycles_out_text: str | None) -> CheckResult:
    """Run the redirect-safety check.

    Args:
        launch_line: The driver invocation string (e.g.
            ``nohup ./run-cycles.sh 3 4 >> cycles.out 2>&1 &``).
        cycles_out_text: The text of an existing ``cycles.out`` when one is
            present on disk, or ``None`` when there is no history file.

    Returns:
        A :class:`CheckResult` named ``redirect-safety``.
    """
    lines: list[str] = []
    redirect = _redirect_to_cycles(launch_line)
    history_exists = cycles_out_text is not None
    has_markers = has_cycle_markers(cycles_out_text) if cycles_out_text is not None else False

    if redirect is None:
        lines.append("launch line does not redirect into cycles.out; nothing to gate.")
        return CheckResult("redirect-safety", True, tuple(lines))

    if redirect == "append":
        lines.append("launch line appends (>>) to cycles.out.")
        if has_markers:
            lines.append("existing cycles.out carries cycle markers; append preserves history.")
        return CheckResult("redirect-safety", True, tuple(lines))

    # redirect == "truncate"
    if not history_exists:
        lines.append("launch line uses bare (>) redirect but no cycles.out history exists.")
        lines.append("first launch: truncate is safe (no history to lose).")
        return CheckResult("redirect-safety", True, tuple(lines))

    if has_markers:
        lines.append("launch line uses bare (>) redirect against an existing cycles.out.")
        lines.append("existing cycles.out carries cycle markers; bare (>) would truncate history.")
        return CheckResult("redirect-safety", False, tuple(lines))

    # History file exists but has no markers yet.
    lines.append("launch line uses bare (>) redirect against an existing cycles.out.")
    lines.append("existing cycles.out has no cycle markers; treating as first-launch history.")
    return CheckResult("redirect-safety", True, tuple(lines))
