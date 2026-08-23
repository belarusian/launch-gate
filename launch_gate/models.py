"""Shared value objects for launch_gate.

These frozen dataclasses are the single source of truth consumed by the four
check modules and the report renderer. A check produces a :class:`CheckResult`
(a named GO/NO-GO verdict plus ordered evidence lines); the report renders the
list of results deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CheckResult:
    """The outcome of one named launch-gate check.

    Attributes:
        name: Stable check name (``redirect-safety``, ``endpoint-contention``,
            ``wall-sizing``, ``prerequisites``).
        go: ``True`` for a GO verdict, ``False`` for NO-GO.
        lines: Ordered evidence lines. Each is a short, self-contained sentence
            describing what was observed. Rendered indented under the verdict.
    """

    name: str
    go: bool
    lines: tuple[str, ...] = field(default_factory=tuple)

    @property
    def label(self) -> str:
        """Return the two-letter verdict token: ``GO`` or ``NO-GO``."""
        return "GO" if self.go else "NO-GO"


@dataclass(frozen=True)
class Report:
    """A fully assembled, deterministic launch-gate report.

    Attributes:
        header: The header block (what was checked, sources read).
        checks: The ordered list of per-check results.
    """

    header: tuple[str, ...]
    checks: tuple[CheckResult, ...]

    @property
    def all_go(self) -> bool:
        """Return ``True`` when every check is GO (and at least one ran)."""
        return bool(self.checks) and all(c.go for c in self.checks)
