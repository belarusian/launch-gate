# TICKET-039 — Golden test: console script + packages declaration

## Capability
Pin the release-metadata contract that `pyproject.toml` declares the
`launch-gate` console script pointing at `launch_gate.cli:main` and that the
`[tool.setuptools] packages` list covers `launch_gate` + `launch_gate.checks`.
A wrong entrypoint target or a missing subpackage would break the installed
CLI / the import surface.

## Probe result (verified against code)
- `[project.scripts] launch-gate = "launch_gate.cli:main"` — present, correct.
- `[tool.setuptools] packages = ["launch_gate", "launch_gate.checks"]` — present,
  covers both packages.
- `launch_gate/cli.py` defines `main()` — the target is importable.
- MATCH — no code fix needed; pin with a golden test.

## Acceptance
- A golden test asserts the `launch-gate` script maps to `launch_gate.cli:main`
  and the packages list contains both `launch_gate` and `launch_gate.checks`.
- Deterministic: no subprocess, no real clock.

## Notes
- Parse `pyproject.toml` without a hard `tomllib` dependency (Python 3.10).
