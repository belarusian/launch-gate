"""Entry point for ``python3 -m launch_gate``.

The full CLI (argparse subcommands, the four checks, the deterministic report)
is built out across the build cycles. This stub keeps the entry point importable
and invocable from cycle 1 so the package surface is stable.
"""

from launch_gate.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
