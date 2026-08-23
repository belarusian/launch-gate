"""launch_gate — a deterministic, stdlib-only launch gate for four pipelines.

Gates a four pipeline launch at the launch moment: the gap between pre-launch
readiness (loop-doctor) and the run. Inspects driver artifacts (the launch line,
the driver script, cycles.out, the launch-registry, fourseer/gate-log data) and
emits a deterministic GO/NO-GO report.

Exit-code contract:
    0 = all checks GO
    1 = any check NO-GO
    2 = usage error
"""

from launch_gate.endpoint_contention import (
    RegistryEntry,
    SocketLine,
    check_endpoint_contention,
    endpoint_hostport,
    parse_endpoints,
    parse_ss,
    scan_registry,
    scan_socket,
)
from launch_gate.models import CheckResult, Report
from launch_gate.prerequisites import GitState, check_prerequisites, collect_git_state
from launch_gate.redirect_safety import check_redirect_safety, has_cycle_markers
from launch_gate.report import render_report
from launch_gate.wall_sizing import (
    check_wall_sizing,
    durations_from_cycles_out,
    durations_from_fourseer,
    parse_inner_seconds,
    parse_outer_wall,
)

__version__ = "0.1.0"

__all__ = [
    "CheckResult",
    "Report",
    "RegistryEntry",
    "SocketLine",
    "GitState",
    "check_redirect_safety",
    "has_cycle_markers",
    "check_endpoint_contention",
    "parse_endpoints",
    "endpoint_hostport",
    "parse_ss",
    "scan_registry",
    "scan_socket",
    "check_wall_sizing",
    "parse_outer_wall",
    "parse_inner_seconds",
    "durations_from_fourseer",
    "durations_from_cycles_out",
    "check_prerequisites",
    "collect_git_state",
    "render_report",
    "__version__",
]
