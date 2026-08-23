"""Unit tests for :mod:`launch_gate.wall_sizing` (check 3 — B1 wall-sizing).

Pins the exact verdict (``go``) **and** the exact evidence ``lines`` for every
classification in the wall-sizing matrix, plus the individual parsers
(:func:`parse_outer_wall`, :func:`parse_inner_seconds`,
:func:`durations_from_fourseer`, :func:`durations_from_cycles_out`) and the
artifact discovery helpers (:func:`_find_fourseer_report`,
:func:`_find_cycles_out`).

The classification matrix (cases a-f) is verified against the seed dialects:
the fourseer report's ``Duration (s)`` column, the ``cycles.out`` timestamp
markers, and the driver script's ``perl -e 'alarm shift; exec @ARGV' <wall>``
outer bound plus ``--inner-seconds``.
"""

from __future__ import annotations

from pathlib import Path

from launch_gate.wall_sizing import (
    _find_cycles_out,
    _find_fourseer_report,
    check_wall_sizing,
    durations_from_cycles_out,
    durations_from_fourseer,
    parse_inner_seconds,
    parse_outer_wall,
)

FIXTURES = Path(__file__).parent / "fixtures"

#: Driver script with a 10800s outer wall and a 3000s inner bound (seed dialect).
BIG_SCRIPT = (FIXTURES / "driver_wall.sh").read_text(encoding="utf-8")

#: A driver script whose outer wall (1000s) is too small to contain the
#: observed inner passes (3 * 1358 = 4074s and 3 * 1420 = 4260s).
SMALL_SCRIPT = (
    "perl -e 'alarm shift; exec @ARGV' 1000 python3 run-v2.py "
    "--inner-seconds 3000"
)


def _fourseer_text() -> str:
    return (FIXTURES / "fourseer-report.txt").read_text(encoding="utf-8")


def _cycles_text() -> str:
    return (FIXTURES / "cycles.out").read_text(encoding="utf-8")


def _ai_dir_with_fourseer(tmp_path: Path) -> Path:
    ai = tmp_path / "ai"
    ai.mkdir()
    (ai / "fourseer-report.txt").write_text(_fourseer_text(), encoding="utf-8")
    return ai


def _ai_dir_with_cycles(tmp_path: Path) -> Path:
    ai = tmp_path / "ai"
    ai.mkdir()
    (ai / "cycles.out").write_text(_cycles_text(), encoding="utf-8")
    return ai


def _empty_ai_dir(tmp_path: Path) -> Path:
    ai = tmp_path / "ai"
    ai.mkdir()
    return ai


# ---------------------------------------------------------------------------
# Classification matrix (cases a-f): assert go AND exact lines.
# ---------------------------------------------------------------------------


def test_a_fourseer_observed_outer_wall_sufficient_is_go(tmp_path: Path) -> None:
    # Case a: a fourseer observation (1358s) with a 10800s outer wall.
    # 10800 >= 3 * 1358 = 4074 -> GO.
    ai = _ai_dir_with_fourseer(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(BIG_SCRIPT, ai, proj)
    assert result.go is True
    assert result.lines == (
        "outer wall (perl alarm): 10800s.",
        "--inner-seconds: 3000s.",
        "observed inner-pass durations: [1358].",
        "source: fourseer report fourseer-report.txt: 1 duration(s).",
        "outer wall 10800s >= 3 * max_observed 1358s (4074s). GO.",
    )


def test_b_fourseer_observed_outer_wall_insufficient_is_no_go(tmp_path: Path) -> None:
    # Case b: a fourseer observation (1358s) with a 1000s outer wall.
    # 1000 < 3 * 1358 = 4074 -> NO-GO.
    ai = _ai_dir_with_fourseer(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(SMALL_SCRIPT, ai, proj)
    assert result.go is False
    assert result.lines == (
        "outer wall (perl alarm): 1000s.",
        "--inner-seconds: 3000s.",
        "observed inner-pass durations: [1358].",
        "source: fourseer report fourseer-report.txt: 1 duration(s).",
        "outer wall 1000s < 3 * max_observed 1358s (4074s). NO-GO.",
    )


def test_c_no_observations_is_conservative_default_go(tmp_path: Path) -> None:
    # Case c: no fourseer Duration and no cycles.out timestamps.
    # The conservative default row applies -> GO with no observations.
    ai = _empty_ai_dir(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(BIG_SCRIPT, ai, proj)
    assert result.go is True
    assert result.lines == (
        "outer wall (perl alarm): 10800s.",
        "--inner-seconds: 3000s.",
        "no observed inner-pass durations found "
        "(no fourseer Duration, no cycles.out timestamps).",
        "conservative default row applies; GO with no observations.",
    )


def test_d_observations_but_no_script_is_no_outer_wall_no_go(tmp_path: Path) -> None:
    # Case d: a fourseer observation exists but no --script was supplied, so
    # there is no outer wall to compare against -> NO-GO.
    ai = _ai_dir_with_fourseer(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(None, ai, proj)
    assert result.go is False
    assert result.lines == (
        "no --script supplied; cannot parse the outer wall.",
        "observed inner-pass durations: [1358].",
        "source: fourseer report fourseer-report.txt: 1 duration(s).",
        "no outer wall to compare against; cannot verify sizing.",
    )


def test_e_cycles_out_observed_outer_wall_sufficient_is_go(tmp_path: Path) -> None:
    # Case e: a cycles.out-derived observation (1420s) with a 10800s outer wall.
    # 10800 >= 3 * 1420 = 4260 -> GO.
    ai = _ai_dir_with_cycles(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(BIG_SCRIPT, ai, proj)
    assert result.go is True
    assert result.lines == (
        "outer wall (perl alarm): 10800s.",
        "--inner-seconds: 3000s.",
        "observed inner-pass durations: [1420].",
        "source: cycles.out cycles.out: 1 derived duration(s).",
        "outer wall 10800s >= 3 * max_observed 1420s (4260s). GO.",
    )


def test_f_cycles_out_observed_outer_wall_insufficient_is_no_go(tmp_path: Path) -> None:
    # Case f: a cycles.out-derived observation (1420s) with a 1000s outer wall.
    # 1000 < 3 * 1420 = 4260 -> NO-GO.
    ai = _ai_dir_with_cycles(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(SMALL_SCRIPT, ai, proj)
    assert result.go is False
    assert result.lines == (
        "outer wall (perl alarm): 1000s.",
        "--inner-seconds: 3000s.",
        "observed inner-pass durations: [1420].",
        "source: cycles.out cycles.out: 1 derived duration(s).",
        "outer wall 1000s < 3 * max_observed 1420s (4260s). NO-GO.",
    )


# ---------------------------------------------------------------------------
# Parsers.
# ---------------------------------------------------------------------------


def test_parse_outer_wall_from_seed_dialect() -> None:
    assert parse_outer_wall(BIG_SCRIPT) == 10800


def test_parse_outer_wall_absent_is_none() -> None:
    assert parse_outer_wall("echo no alarm here") is None


def test_parse_inner_seconds_from_seed_dialect() -> None:
    assert parse_inner_seconds(BIG_SCRIPT) == 3000


def test_parse_inner_seconds_absent_is_none() -> None:
    assert parse_inner_seconds("echo no inner bound here") is None


def test_durations_from_fourseer_observed_plus_dash_row() -> None:
    # The observed row (1358) is kept; the dash row (no observation) is skipped.
    assert durations_from_fourseer(_fourseer_text()) == [1358]


def test_durations_from_fourseer_empty_is_empty() -> None:
    assert durations_from_fourseer("") == []


def test_durations_from_fourseer_header_and_separator_are_ignored() -> None:
    text = (
        "| Cycle | Outcome | Steps | Duration (s) | Trajectory |\n"
        "| --- | --- | --- | --- | --- |\n"
    )
    assert durations_from_fourseer(text) == []


def test_durations_from_cycles_out_consecutive_start_markers() -> None:
    # 14:27:19Z -> 14:50:59Z is a 1420s gap.
    assert durations_from_cycles_out(_cycles_text()) == [1420]


def test_durations_from_cycles_out_single_marker_is_empty() -> None:
    assert durations_from_cycles_out("========== CYCLE 1  14:27:19Z ==========\n") == []


def test_durations_from_cycles_out_no_markers_is_empty() -> None:
    assert durations_from_cycles_out("plain output, no markers\n") == []


# ---------------------------------------------------------------------------
# Artifact discovery.
# ---------------------------------------------------------------------------


def test_find_fourseer_report_found(tmp_path: Path) -> None:
    ai = _ai_dir_with_fourseer(tmp_path)
    found = _find_fourseer_report(ai)
    assert found is not None
    assert found.name == "fourseer-report.txt"


def test_find_fourseer_report_absent_is_none(tmp_path: Path) -> None:
    ai = _empty_ai_dir(tmp_path)
    assert _find_fourseer_report(ai) is None


def test_find_fourseer_report_non_dir_is_none(tmp_path: Path) -> None:
    assert _find_fourseer_report(tmp_path / "does-not-exist") is None


def test_find_cycles_out_in_ai_dir(tmp_path: Path) -> None:
    ai = _ai_dir_with_cycles(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    found = _find_cycles_out(ai, proj)
    assert found is not None
    assert found.name == "cycles.out"


def test_find_cycles_out_in_project_dir(tmp_path: Path) -> None:
    ai = _empty_ai_dir(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "cycles.out").write_text(_cycles_text(), encoding="utf-8")
    found = _find_cycles_out(ai, proj)
    assert found is not None
    assert found.name == "cycles.out"


def test_find_cycles_out_absent_is_none(tmp_path: Path) -> None:
    ai = _empty_ai_dir(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    assert _find_cycles_out(ai, proj) is None


# ---------------------------------------------------------------------------
# Additional edge cases: combined sources, missing outer wall, boundary, and
# parser robustness. Each asserts the verdict (go) AND the exact evidence lines.
# ---------------------------------------------------------------------------

#: A realistic full-run cycles.out with a long middle pass (9000s) so that
#: 3 * max_observed (27000s) exceeds the 10800s outer wall -> NO-GO.
LONG_CYCLES = (FIXTURES / "cycles_out_long.out").read_text(encoding="utf-8")


def _ai_dir_with_long_cycles(tmp_path: Path) -> Path:
    ai = tmp_path / "ai"
    ai.mkdir()
    (ai / "cycles.out").write_text(LONG_CYCLES, encoding="utf-8")
    return ai


def _ai_dir_with_both(tmp_path: Path) -> Path:
    ai = tmp_path / "ai"
    ai.mkdir()
    (ai / "fourseer-report.txt").write_text(_fourseer_text(), encoding="utf-8")
    (ai / "cycles.out").write_text(_cycles_text(), encoding="utf-8")
    return ai


def test_g_both_sources_combined_is_go(tmp_path: Path) -> None:
    # Both a fourseer observation (1358) and a cycles.out-derived observation
    # (1420) are present. Observations are combined, both source notes are
    # emitted, and the max (1420) drives the verdict: 10800 >= 3 * 1420 = 4260.
    ai = _ai_dir_with_both(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(BIG_SCRIPT, ai, proj)
    assert result.go is True
    assert result.lines == (
        "outer wall (perl alarm): 10800s.",
        "--inner-seconds: 3000s.",
        "observed inner-pass durations: [1358, 1420].",
        "source: fourseer report fourseer-report.txt: 1 duration(s).",
        "source: cycles.out cycles.out: 1 derived duration(s).",
        "outer wall 10800s >= 3 * max_observed 1420s (4260s). GO.",
    )


def test_h_script_without_outer_wall_with_observations_is_no_go(tmp_path: Path) -> None:
    # A driver script is supplied but has no perl-alarm outer wall, yet a
    # fourseer observation exists. There is no outer wall to compare against,
    # so the check is NO-GO (distinct from the no-script case).
    ai = _ai_dir_with_fourseer(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(
        "echo hi; python3 run-v2.py --inner-seconds 3000", ai, proj
    )
    assert result.go is False
    assert result.lines == (
        "no outer wall (perl alarm) found in the driver script.",
        "--inner-seconds: 3000s.",
        "observed inner-pass durations: [1358].",
        "source: fourseer report fourseer-report.txt: 1 duration(s).",
        "no outer wall to compare against; cannot verify sizing.",
    )


def test_i_script_without_outer_wall_no_observations_is_go(tmp_path: Path) -> None:
    # A driver script is supplied but has no perl-alarm outer wall and there
    # are no observations. The conservative default row still applies -> GO.
    ai = _empty_ai_dir(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(
        "echo hi; python3 run-v2.py --inner-seconds 3000", ai, proj
    )
    assert result.go is True
    assert result.lines == (
        "no outer wall (perl alarm) found in the driver script.",
        "--inner-seconds: 3000s.",
        "no observed inner-pass durations found "
        "(no fourseer Duration, no cycles.out timestamps).",
        "conservative default row applies; GO with no observations.",
    )


def test_j_fourseer_all_dash_rows_is_conservative_go(tmp_path: Path) -> None:
    # A fourseer report exists but every Duration cell is a dash (no
    # observation). A source note records the absence and the conservative
    # default row applies -> GO.
    ai = tmp_path / "ai"
    ai.mkdir()
    (ai / "fourseer-report.txt").write_text(
        "| Cycle | Outcome | Steps | Duration (s) | Trajectory |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 7 | exit:task_complete | 41 | - | trajectory_0013.json |\n",
        encoding="utf-8",
    )
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(BIG_SCRIPT, ai, proj)
    assert result.go is True
    assert result.lines == (
        "outer wall (perl alarm): 10800s.",
        "--inner-seconds: 3000s.",
        "no observed inner-pass durations found "
        "(no fourseer Duration, no cycles.out timestamps).",
        "source: fourseer report fourseer-report.txt: no Duration (s) observations.",
        "conservative default row applies; GO with no observations.",
    )


def test_k_cycles_out_single_marker_is_conservative_go(tmp_path: Path) -> None:
    # A cycles.out with only one start marker yields no derived durations, so
    # no cycles source note is emitted and the conservative default row applies.
    ai = tmp_path / "ai"
    ai.mkdir()
    (ai / "cycles.out").write_text(
        "========== CYCLE 1  14:27:19Z ==========\n"
        "OUTER outcome: exit:task_complete\n"
        "========== CYCLE 1 done ==========\n",
        encoding="utf-8",
    )
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(BIG_SCRIPT, ai, proj)
    assert result.go is True
    assert result.lines == (
        "outer wall (perl alarm): 10800s.",
        "--inner-seconds: 3000s.",
        "no observed inner-pass durations found "
        "(no fourseer Duration, no cycles.out timestamps).",
        "conservative default row applies; GO with no observations.",
    )


def test_l_boundary_equality_is_go(tmp_path: Path) -> None:
    # Boundary: outer wall (10800) equals 3 * max_observed (3 * 3600 = 10800).
    # The comparison is >=, so equality is GO.
    ai = tmp_path / "ai"
    ai.mkdir()
    (ai / "fourseer-report.txt").write_text(
        "| 7 | exit:task_complete | 41 | 3600 | trajectory_0013.json |\n",
        encoding="utf-8",
    )
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(BIG_SCRIPT, ai, proj)
    assert result.go is True
    assert result.lines == (
        "outer wall (perl alarm): 10800s.",
        "--inner-seconds: 3000s.",
        "observed inner-pass durations: [3600].",
        "source: fourseer report fourseer-report.txt: 1 duration(s).",
        "outer wall 10800s >= 3 * max_observed 3600s (10800s). GO.",
    )


def test_m_full_run_cycles_out_is_no_go(tmp_path: Path) -> None:
    # A realistic full-run cycles.out with a long middle pass (9000s). The max
    # observation is 9000, so 3 * 9000 = 27000 > 10800 -> NO-GO.
    ai = _ai_dir_with_long_cycles(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(BIG_SCRIPT, ai, proj)
    assert result.go is False
    assert result.lines == (
        "outer wall (perl alarm): 10800s.",
        "--inner-seconds: 3000s.",
        "observed inner-pass durations: [1800, 1800, 9000].",
        "source: cycles.out cycles.out: 3 derived duration(s).",
        "outer wall 10800s < 3 * max_observed 9000s (27000s). NO-GO.",
    )


# ---------------------------------------------------------------------------
# Parser robustness (original inputs, not copied from the seed).
# ---------------------------------------------------------------------------


def test_parse_outer_wall_double_quoted() -> None:
    # The perl invocation may use double quotes around the -e program.
    assert parse_outer_wall('perl -e "alarm shift; exec @ARGV" 5000 python3 x.py') == 5000


def test_parse_outer_wall_extra_whitespace() -> None:
    # Extra whitespace between the wall value and the command is tolerated.
    assert parse_outer_wall("perl -e 'alarm shift; exec @ARGV'   7777   python3 x.py") == 7777


def test_parse_inner_seconds_equals_form_is_none() -> None:
    # The parser only recognises the space-separated ``--inner-seconds N`` form;
    # the ``--inner-seconds=N`` form is not matched (returns None).
    assert parse_inner_seconds("python3 x.py --inner-seconds=42") is None


def test_durations_from_cycles_out_ignores_done_markers() -> None:
    # ``done`` markers carry no timestamp and are ignored; only consecutive
    # start markers produce durations (3 starts -> 2 durations).
    text = (
        "========== CYCLE 1  14:27:19Z ==========\n"
        "OUTER outcome: exit:task_complete\n"
        "========== CYCLE 1 done ==========\n"
        "========== CYCLE 2  14:50:59Z ==========\n"
        "========== CYCLE 2 done ==========\n"
        "========== CYCLE 3  15:19:44Z ==========\n"
        "========== CYCLE 3 done ==========\n"
    )
    assert durations_from_cycles_out(text) == [1420, 1725]


def test_durations_from_fourseer_multiple_observed_rows() -> None:
    # Multiple observed rows are preserved in order; the dash row is skipped.
    text = (
        "| 7 | exit:task_complete | 41 | 1358 | trajectory_0013.json |\n"
        "| 8 | exit:task_complete | 55 | 2000 | trajectory_0014.json |\n"
        "| 9 | exit:task_complete | 60 | - | trajectory_0015.json |\n"
    )
    assert durations_from_fourseer(text) == [1358, 2000]


# ---------------------------------------------------------------------------
# Edge pins (n)-(q): artifact discovery subpaths, fourseer lexicographic
# selection, fourseer row robustness, and the no-script + no-observations
# conservative-default GO. Each asserts the returned path / value / exact lines.
# ---------------------------------------------------------------------------


def test_find_cycles_out_nested_ai_subpath(tmp_path: Path) -> None:
    # (n) A ``cycles.out`` nested under ``ai_dir/ai/`` is discovered.
    ai = tmp_path / "ai"
    (ai / "ai").mkdir(parents=True)
    (ai / "ai" / "cycles.out").write_text(_cycles_text(), encoding="utf-8")
    proj = tmp_path / "proj"
    proj.mkdir()
    found = _find_cycles_out(ai, proj)
    assert found == ai / "ai" / "cycles.out"


def test_find_cycles_out_nested_project_subpath(tmp_path: Path) -> None:
    # (n) A ``cycles.out`` nested under ``project_dir/ai/`` is discovered when
    # the ``ai_dir`` has none.
    ai = _empty_ai_dir(tmp_path)
    proj = tmp_path / "proj"
    (proj / "ai").mkdir(parents=True)
    (proj / "ai" / "cycles.out").write_text(_cycles_text(), encoding="utf-8")
    found = _find_cycles_out(ai, proj)
    assert found == proj / "ai" / "cycles.out"


def test_find_cycles_out_top_level_wins_over_nested_in_same_base(tmp_path: Path) -> None:
    # (n) Within the same base, a top-level ``cycles.out`` wins over the
    # nested ``ai/cycles.out`` (the top-level name is checked first).
    ai = tmp_path / "ai"
    (ai / "ai").mkdir(parents=True)
    (ai / "cycles.out").write_text(_cycles_text(), encoding="utf-8")
    (ai / "ai" / "cycles.out").write_text(_cycles_text(), encoding="utf-8")
    proj = tmp_path / "proj"
    proj.mkdir()
    found = _find_cycles_out(ai, proj)
    assert found == ai / "cycles.out"


def test_find_fourseer_report_lexicographic_first_with_subdir(tmp_path: Path) -> None:
    # (o) When several ``*fourseer*report*`` files exist (one in a nested
    # subdir), the lexicographically-first full path wins. The nested
    # ``aaa/fourseer-report.txt`` sorts before the top-level files.
    ai = tmp_path / "ai"
    (ai / "aaa").mkdir(parents=True)
    (ai / "aaa" / "fourseer-report.txt").write_text(_fourseer_text(), encoding="utf-8")
    (ai / "fourseer-report.txt").write_text(_fourseer_text(), encoding="utf-8")
    (ai / "fourseer-report-2.txt").write_text(_fourseer_text(), encoding="utf-8")
    found = _find_fourseer_report(ai)
    assert found == ai / "aaa" / "fourseer-report.txt"


def test_durations_from_fourseer_dash_steps_numeric_duration_is_kept() -> None:
    # (p) A row whose Steps cell is a dash is kept when its Duration cell is
    # numeric: the dash is in the Steps column, not the Duration column.
    text = "| 7 | x | - | 1358 | t.json |\n"
    assert durations_from_fourseer(text) == [1358]


def test_durations_from_fourseer_trailing_extra_cell_is_tolerated() -> None:
    # (p) A trailing extra cell after the Trajectory cell is tolerated; the
    # Duration cell (4th) is still read.
    text = "| 7 | x | 41 | 1358 | t.json | extra |\n"
    assert durations_from_fourseer(text) == [1358]


def test_q_no_script_no_observations_is_conservative_default_go(tmp_path: Path) -> None:
    # (q) No ``--script`` and no observations (empty ``ai_dir``/``project_dir``)
    # -> GO with the conservative-default note. This is the no-``--script``
    # counterpart of case (c).
    ai = _empty_ai_dir(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(None, ai, proj)
    assert result.go is True
    assert result.lines == (
        "no --script supplied; cannot parse the outer wall.",
        "no observed inner-pass durations found "
        "(no fourseer Duration, no cycles.out timestamps).",
        "conservative default row applies; GO with no observations.",
    )


# ---------------------------------------------------------------------------
# Cycle 10 — fourseer report with MULTIPLE observed Duration rows.
# ---------------------------------------------------------------------------


def _fourseer_multi_text() -> str:
    return (FIXTURES / "fourseer-report-multi.txt").read_text(encoding="utf-8")


def _ai_dir_with_fourseer_multi(tmp_path: Path) -> Path:
    ai = tmp_path / "ai"
    ai.mkdir()
    (ai / "fourseer-report-multi.txt").write_text(_fourseer_multi_text(), encoding="utf-8")
    return ai


def test_durations_from_fourseer_multi_returns_both_observed() -> None:
    # Two observed rows (1358, 1420) are returned in order; the dash row is
    # skipped.
    assert durations_from_fourseer(_fourseer_multi_text()) == [1358, 1420]


def test_wall_sizing_multi_observations_uses_max_go(tmp_path: Path) -> None:
    # With observations [1358, 1420], the required wall is 3 * max = 3 * 1420
    # = 4260s. The 10800s outer wall is sufficient -> GO. The evidence line
    # names the MAX observed (1420), not the first (1358).
    ai = _ai_dir_with_fourseer_multi(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(BIG_SCRIPT, ai, proj)
    assert result.go is True
    assert result.lines == (
        "outer wall (perl alarm): 10800s.",
        "--inner-seconds: 3000s.",
        "observed inner-pass durations: [1358, 1420].",
        "source: fourseer report fourseer-report-multi.txt: 2 duration(s).",
        "outer wall 10800s >= 3 * max_observed 1420s (4260s). GO.",
    )


def test_wall_sizing_multi_observations_uses_max_no_go(tmp_path: Path) -> None:
    # Same observations, but the 1000s outer wall is below 3 * max (4260s)
    # -> NO-GO, again keyed off the MAX observed (1420).
    ai = _ai_dir_with_fourseer_multi(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir()
    result = check_wall_sizing(SMALL_SCRIPT, ai, proj)
    assert result.go is False
    assert result.lines == (
        "outer wall (perl alarm): 1000s.",
        "--inner-seconds: 3000s.",
        "observed inner-pass durations: [1358, 1420].",
        "source: fourseer report fourseer-report-multi.txt: 2 duration(s).",
        "outer wall 1000s < 3 * max_observed 1420s (4260s). NO-GO.",
    )


# ---------------------------------------------------------------------------
# Cycle 10 — cycles.out with only ``done`` markers (no start timestamps).
# ---------------------------------------------------------------------------


def _cycles_done_only_text() -> str:
    return (FIXTURES / "cycles_out_done_only.out").read_text(encoding="utf-8")


def test_durations_from_cycles_out_done_only_returns_empty() -> None:
    # ``done`` markers carry no timestamp; with no start markers there are no
    # consecutive stamps to pair, so no durations are derived.
    assert durations_from_cycles_out(_cycles_done_only_text()) == []
