"""Unit tests for :mod:`launch_gate.redirect_safety`.

Pins the exact verdict (``go``) **and** the exact evidence ``lines`` for every
redirect classification, including the stderr-only ``2> cycles.out`` edge that
must NOT be treated as a truncate of the stdout history.
"""

from __future__ import annotations

from pathlib import Path

from launch_gate.redirect_safety import check_redirect_safety, has_cycle_markers

FIXTURES = Path(__file__).parent / "fixtures"


def _markers_text() -> str:
    return (FIXTURES / "cycles_out_markers.txt").read_text(encoding="utf-8")


def _nomarkers_text() -> str:
    return (FIXTURES / "cycles_out_nomarkers.txt").read_text(encoding="utf-8")


def test_append_is_go() -> None:
    result = check_redirect_safety(
        "nohup ./run.sh 3 4 >> cycles.out 2>&1 &", _markers_text()
    )
    assert result.go is True
    assert result.lines == (
        "launch line appends (>>) to cycles.out.",
        "existing cycles.out carries cycle markers; append preserves history.",
    )


def test_bare_truncate_no_history_is_go() -> None:
    result = check_redirect_safety("./run.sh > cycles.out", None)
    assert result.go is True
    assert result.lines == (
        "launch line uses bare (>) redirect but no cycles.out history exists.",
        "first launch: truncate is safe (no history to lose).",
    )


def test_bare_truncate_against_markers_is_no_go() -> None:
    result = check_redirect_safety("./run.sh > cycles.out", _markers_text())
    assert result.go is False
    assert result.lines == (
        "launch line uses bare (>) redirect against an existing cycles.out.",
        "existing cycles.out carries cycle markers; bare (>) would truncate history.",
    )


def test_bare_truncate_against_nomarkers_is_go() -> None:
    result = check_redirect_safety("./run.sh > cycles.out", _nomarkers_text())
    assert result.go is True
    assert result.lines == (
        "launch line uses bare (>) redirect against an existing cycles.out.",
        "existing cycles.out has no cycle markers; treating as first-launch history.",
    )


def test_no_redirect_into_cycles_out_is_go() -> None:
    result = check_redirect_safety("./run.sh", _markers_text())
    assert result.go is True
    assert result.lines == (
        "launch line does not redirect into cycles.out; nothing to gate.",
    )


def test_stderr_only_redirect_is_not_a_truncate() -> None:
    # ``2> cycles.out`` redirects stderr only; it must NOT be classified as a
    # truncate of the stdout history, so it is GO even against a marker file.
    result = check_redirect_safety("./run.sh 2> cycles.out", _markers_text())
    assert result.go is True
    assert result.lines == (
        "launch line does not redirect into cycles.out; nothing to gate.",
    )


def test_dup_stdout_to_stderr_is_not_a_redirect() -> None:
    # ``2>&1`` duplicates stderr onto stdout; it is not a redirect into
    # cycles.out at all.
    result = check_redirect_safety("./run.sh 2>&1", _markers_text())
    assert result.go is True
    assert result.lines == (
        "launch line does not redirect into cycles.out; nothing to gate.",
    )


def test_has_cycle_markers_true() -> None:
    assert has_cycle_markers(_markers_text()) is True


def test_has_cycle_markers_false() -> None:
    assert has_cycle_markers(_nomarkers_text()) is False


def test_has_cycle_markers_empty() -> None:
    assert has_cycle_markers("") is False
