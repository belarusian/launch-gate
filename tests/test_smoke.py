"""Smoke test: the package imports and exposes its entry point."""

import launch_gate


def test_import() -> None:
    assert launch_gate.__name__ == "launch_gate"
    assert hasattr(launch_gate, "__version__")


def test_entrypoint_importable() -> None:
    import launch_gate.__main__  # noqa: F401
    from launch_gate.cli import build_parser, main

    assert callable(main)
    parser = build_parser()
    assert parser.prog == "launch-gate"
