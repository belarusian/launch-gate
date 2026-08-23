# TICKET-040 — Golden test: `python3 -m launch_gate` entrypoint + README consistency

## Capability
Pin the release-metadata contract that the `python3 -m launch_gate` entrypoint
is importable (a `launch_gate/__main__.py` exists and calls `cli.main`) and that
the README's documented entrypoint (`python3 -m launch_gate` / the `launch-gate`
console script) and the README "Gate" section match the real contract.

## Probe result (verified against code)
- `launch_gate/__main__.py` exists and does `from launch_gate.cli import main`
  then `raise SystemExit(main())` — importable, correct.
- README line 7: "Entrypoint: `python3 -m launch_gate` (also installed as
  `launch-gate`)." — matches pyproject console script + `__main__.py`.
- README "Gate" section lists `pytest tests/ -x -q`, `ruff check launch_gate/`,
  `mypy launch_gate/ --ignore-missing-imports` — matches the runner-prompt gate.
- MATCH — no code fix needed; pin with a golden test.

## Acceptance
- A golden test asserts `launch_gate/__main__.py` exists and its source calls
  `cli.main` (importable entrypoint), and that the README documents both the
  `python3 -m launch_gate` entrypoint and the `launch-gate` console script.
- Deterministic: no subprocess, no real clock. Reads files + inspects source.

## Notes
- Do NOT invent behavior; only pin what the code + README already state.
