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


# ---------------------------------------------------------------------------
# Cycle 4 edge-case sweep: forms the Cycle-3 dedicated tests did not pin.
# ---------------------------------------------------------------------------


def test_explicit_stdout_truncate_1_gt_against_markers_is_no_go() -> None:
    # ``1>`` is the explicit-stdout form of a bare truncate; it must be gated
    # exactly like ``>`` against an existing marker file.
    result = check_redirect_safety("./run.sh 1> cycles.out", _markers_text())
    assert result.go is False
    assert result.lines == (
        "launch line uses bare (>) redirect against an existing cycles.out.",
        "existing cycles.out carries cycle markers; bare (>) would truncate history.",
    )


def test_explicit_stdout_truncate_1_gt_no_history_is_go() -> None:
    result = check_redirect_safety("./run.sh 1> cycles.out", None)
    assert result.go is True
    assert result.lines == (
        "launch line uses bare (>) redirect but no cycles.out history exists.",
        "first launch: truncate is safe (no history to lose).",
    )


def test_append_with_no_history_is_go() -> None:
    # ``>>`` with no existing cycles.out is a first launch: GO, and the
    # single-line evidence (no marker line, since there is no history).
    result = check_redirect_safety("./run.sh >> cycles.out", None)
    assert result.go is True
    assert result.lines == (
        "launch line appends (>>) to cycles.out.",
    )


def test_redirect_to_a_different_file_is_not_gated() -> None:
    # A truncate into a *different* file does not touch the cycles.out
    # history, so it is not gated even against a marker file.
    result = check_redirect_safety("./run.sh > other.log", _markers_text())
    assert result.go is True
    assert result.lines == (
        "launch line does not redirect into cycles.out; nothing to gate.",
    )


def test_append_to_a_different_file_is_not_gated() -> None:
    result = check_redirect_safety("./run.sh >> other.log", _markers_text())
    assert result.go is True
    assert result.lines == (
        "launch line does not redirect into cycles.out; nothing to gate.",
    )


def test_whitespace_variants_of_truncate_are_still_gated() -> None:
    # Extra spaces and a tab between ``>`` and ``cycles.out`` must not evade
    # the truncate classification.
    for line in ("./run.sh >  cycles.out", "./run.sh >\tcycles.out"):
        result = check_redirect_safety(line, _markers_text())
        assert result.go is False, line
        assert result.lines == (
            "launch line uses bare (>) redirect against an existing cycles.out.",
            "existing cycles.out carries cycle markers; bare (>) would truncate history.",
        )


def test_no_space_append_is_still_classified() -> None:
    result = check_redirect_safety("./run.sh >>cycles.out", _markers_text())
    assert result.go is True
    assert result.lines == (
        "launch line appends (>>) to cycles.out.",
        "existing cycles.out carries cycle markers; append preserves history.",
    )


def test_done_marker_line_is_recognized() -> None:
    # The ``========== CYCLE N done ==========`` closing line also carries the
    # marker prefix, so a file with only a done line still counts as history.
    assert has_cycle_markers("========== CYCLE 1 done ==========\n") is True
    result = check_redirect_safety("./run.sh > cycles.out", "========== CYCLE 1 done ==========\n")
    assert result.go is False


def test_non_seed_marker_dialect_is_not_a_marker() -> None:
    # A marker line that is NOT the seed dialect (e.g. ``### CYCLE 1``) must
    # NOT be treated as a cycle marker: only the ``========== CYCLE N ==========``
    # dialect counts. So a bare ``>`` against such a file is GO (no markers).
    assert has_cycle_markers("### CYCLE 1\n") is False
    result = check_redirect_safety("./run.sh > cycles.out", "### CYCLE 1\n")
    assert result.go is True
    assert result.lines == (
        "launch line uses bare (>) redirect against an existing cycles.out.",
        "existing cycles.out has no cycle markers; treating as first-launch history.",
    )
