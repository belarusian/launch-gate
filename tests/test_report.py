"""Unit tests for :func:`launch_gate.report.render_report`.

These pin the exact layout of the rendered report: the header block, the
per-check verdict table (name / GO-NO-GO / indented evidence), and the final
``ALL-GO`` / ``NO-GO`` line.
"""

from __future__ import annotations

from launch_gate.models import CheckResult, Report
from launch_gate.report import render_report


def _all_go_report() -> Report:
    return Report(
        header=(
            "launch line: nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
            "project dir: /home/u/proj (project 'proj')",
        ),
        checks=(
            CheckResult("redirect-safety", True, ("launch line appends (>>) to cycles.out.",)),
            CheckResult("endpoint-contention", True, ("no occupancy data; GO.",)),
            CheckResult("wall-sizing", True, ("outer wall (perl alarm): 21600s.",)),
            CheckResult("prerequisites", True, ("on branch main.",)),
        ),
    )


def _no_go_report() -> Report:
    return Report(
        header=("launch line: ./run.sh > cycles.out",),
        checks=(
            CheckResult("redirect-safety", False, ("bare (>) would truncate history.",)),
            CheckResult("endpoint-contention", True, ("no occupancy data; GO.",)),
        ),
    )


def test_header_block_is_rendered() -> None:
    out = render_report(_all_go_report())
    lines = out.split("\n")
    # Title + rule, then each header line verbatim, then a blank line.
    assert lines[0] == "launch-gate report"
    assert lines[1] == "=" * 40
    assert lines[2] == "launch line: nohup ./run.sh 3 4 >> cycles.out 2>&1 &"
    assert lines[3] == "project dir: /home/u/proj (project 'proj')"
    assert lines[4] == ""


def test_per_check_verdict_table_layout() -> None:
    out = render_report(_all_go_report())
    lines = out.split("\n")
    # Section header + rule.
    assert lines[5] == "per-check verdicts"
    assert lines[6] == "-" * 40
    # Each check: name left-justified to 20 cols, then the verdict token.
    assert lines[7] == "redirect-safety      GO"
    assert lines[8] == "    launch line appends (>>) to cycles.out."
    assert lines[9] == "endpoint-contention  GO"
    assert lines[10] == "    no occupancy data; GO."
    assert lines[11] == "wall-sizing          GO"
    assert lines[12] == "    outer wall (perl alarm): 21600s."
    assert lines[13] == "prerequisites        GO"
    assert lines[14] == "    on branch main."
    # Closing rule.
    assert lines[15] == "-" * 40


def test_final_line_all_go() -> None:
    out = render_report(_all_go_report())
    assert out.split("\n")[-1] == "ALL-GO"


def test_final_line_no_go() -> None:
    out = render_report(_no_go_report())
    assert out.split("\n")[-1] == "NO-GO"


def test_no_go_verdict_token_in_table() -> None:
    out = render_report(_no_go_report())
    lines = out.split("\n")
    # _no_go_report has a single header line, so the table starts at index 6.
    assert lines[6] == "redirect-safety      NO-GO"
    assert lines[7] == "    bare (>) would truncate history."
    assert lines[8] == "endpoint-contention  GO"


def test_no_trailing_newline() -> None:
    out = render_report(_all_go_report())
    assert not out.endswith("\n")


def test_empty_checks_is_no_go() -> None:
    # A report with no checks is not all-GO (all_go requires at least one).
    report = Report(header=("h",), checks=())
    out = render_report(report)
    assert out.split("\n")[-1] == "NO-GO"


# ---------------------------------------------------------------------------
# Cycle 13 — layout contract: named constants + render_header helper.
# ---------------------------------------------------------------------------


def test_render_header_matches_header_block() -> None:
    from launch_gate.report import render_header

    header = (
        "launch line: nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
        "project dir: /home/u/proj (project 'proj')",
    )
    lines = render_header(header)
    assert lines == [
        "launch-gate report",
        "=" * 40,
        "launch line: nohup ./run.sh 3 4 >> cycles.out 2>&1 &",
        "project dir: /home/u/proj (project 'proj')",
        "",
    ]


def test_render_header_is_pure_and_deterministic() -> None:
    from launch_gate.report import render_header

    header = ("h1", "h2")
    assert render_header(header) == render_header(header)


def test_layout_constants_pin_the_golden_widths() -> None:
    # The named constants are the single source of truth for the layout the
    # golden test pins byte-for-byte.
    from launch_gate import report as report_mod

    assert report_mod._TITLE == "launch-gate report"
    assert report_mod._RULE_WIDTH == 40
    assert report_mod._NAME_WIDTH == 20
    assert report_mod._SECTION_TITLE == "per-check verdicts"
    assert report_mod._EVIDENCE_INDENT == "    "
    assert report_mod._VERDICT_WIDTH == 6


def test_render_report_uses_render_header() -> None:
    # The header block of render_report is exactly render_header's output.
    from launch_gate.report import render_header

    report = _all_go_report()
    out = render_report(report)
    header_lines = render_header(report.header)
    assert out.split("\n")[: len(header_lines)] == header_lines
