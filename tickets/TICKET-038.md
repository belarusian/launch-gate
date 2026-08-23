# TICKET-038 — Golden test: `__init__.__version__` == pyproject `version`

## Capability
Pin the release-metadata contract that the package version declared in
`launch_gate/__init__.py` (`__version__`) matches the `version` field in
`pyproject.toml` `[project]`. A future bump of one without the other is a
release inconsistency the gate must catch.

## Probe result (verified against code)
- `pyproject.toml` `[project] version = "0.1.0"`.
- `launch_gate/__init__.py` `__version__ = "0.1.0"`.
- MATCH — no code fix needed; pin with a golden test.

## Acceptance
- A new test in `tests/test_readme_contract.py` (or a new
  `tests/test_release_metadata.py`) asserts `launch_gate.__version__` equals the
  `version` parsed from `pyproject.toml`.
- Deterministic: no subprocess, no real clock. Reads the file + imports the
  package.
- Reuse existing helpers where possible.

## Notes
- Python here is 3.10 (no `tomllib`); the test must parse `pyproject.toml`
  without a hard `tomllib` dependency (a minimal fallback or a targeted regex
  for the `version` scalar is acceptable).
