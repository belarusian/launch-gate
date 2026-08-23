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

__version__ = "0.1.0"
