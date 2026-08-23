"""Golden contract tests pinning the launch-gate release metadata.

These tests pin the release-metadata contract so a future drift between the
package's declared version, its packaging metadata, and its documented
entrypoints is caught by the gate. Three contracts are pinned (TICKET-038/039/
040, issues #48/#49/#50):

1. **Version parity** — ``launch_gate.__version__`` equals the ``version``
   field in ``pyproject.toml`` ``[project]``.

2. **Console script + packages** — ``pyproject.toml`` ``[project.scripts]``
   declares ``launch-gate = "launch_gate.cli:main"`` and ``[tool.setuptools]
   packages`` covers both ``launch_gate`` and ``launch_gate.checks``.

3. **Module entrypoint + README** — ``launch_gate/__main__.py`` exists and its
   source calls ``cli.main`` (the importable ``python3 -m launch_gate``
   entrypoint), and the README documents both the ``python3 -m launch_gate``
   entrypoint and the ``launch-gate`` console script.

These tests are deterministic: no subprocess, no real clock. They read files
and inspect source. ``pyproject.toml`` is parsed with a minimal, targeted
parser (no ``tomllib`` dependency — Python here is 3.10).
"""

from __future__ import annotations

import re
from pathlib import Path

import launch_gate

#: Repository root (this file lives in ``tests/``).
REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
README = REPO_ROOT / "README.md"
MAIN_MODULE = REPO_ROOT / "launch_gate" / "__main__.py"


# ---------------------------------------------------------------------------
# Minimal, targeted pyproject.toml parser (no tomllib dependency).
# ---------------------------------------------------------------------------


def _unquote(token: str) -> str:
    """Strip a single layer of matching quotes from a TOML scalar token."""
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
        return token[1:-1]
    return token


def _parse_value(value: str) -> object:
    """Parse a single-line TOML value: a string list ``[...]`` or a scalar.

    Only the subset used by ``pyproject.toml`` is handled: an inline array of
    strings, or a bare scalar (string/number). Trailing inline comments are
    stripped for scalars.
    """
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        items: list[str] = []
        for part in inner.split(","):
            part = part.strip()
            if part:
                items.append(_unquote(part))
        return items
    # Scalar: drop a trailing ``# comment`` (never inside a quoted string here).
    if value.startswith(('"', "'")):
        return _unquote(value)
    return value.split("#", 1)[0].strip()


def _parse_pyproject(text: str) -> dict[str, dict[str, object]]:
    """Parse ``pyproject.toml`` into ``{dotted_section: {key: value}}``.

    Handles ``[section]`` headers, ``key = "scalar"`` and single-line
    ``key = ["a", "b"]`` lines. Multi-line arrays (e.g. ``classifiers``) are
    skipped — they are not read by the golden tests. Blank lines and full-line
    comments are ignored. This is intentionally minimal: it covers exactly the
    fields the tests read.
    """
    sections: dict[str, dict[str, object]] = {}
    current = ""
    skipping_array = False
    for raw in text.splitlines():
        line = raw.strip()
        if skipping_array:
            # Consume the rest of a multi-line array until its closing bracket.
            if "]" in line:
                skipping_array = False
            continue
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            sections.setdefault(current, {})
            continue
        if "=" not in line or not current:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if value.startswith("[") and not value.endswith("]"):
            # Multi-line array: skip it (and its continuation lines).
            skipping_array = True
            continue
        sections[current][key.strip()] = _parse_value(value)
    return sections


def _pyproject() -> dict[str, dict[str, object]]:
    return _parse_pyproject(PYPROJECT.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Version parity: __init__.__version__ == pyproject [project] version.
# ---------------------------------------------------------------------------


def test_pyproject_project_version_is_present() -> None:
    version = _pyproject()["project"].get("version")
    assert version is not None, "pyproject.toml [project] must declare a version"
    assert isinstance(version, str) and version, "version must be a non-empty string"


def test_init_version_matches_pyproject_version() -> None:
    expected = _pyproject()["project"]["version"]
    assert launch_gate.__version__ == expected, (
        f"launch_gate.__version__ ({launch_gate.__version__!r}) must equal the "
        f"pyproject.toml [project] version ({expected!r})"
    )


# ---------------------------------------------------------------------------
# 2. Console script + packages declaration.
# ---------------------------------------------------------------------------


def test_console_script_declares_launch_gate_to_cli_main() -> None:
    scripts = _pyproject()["project.scripts"]
    assert scripts.get("launch-gate") == "launch_gate.cli:main", (
        f"[project.scripts] launch-gate must map to 'launch_gate.cli:main', "
        f"got {scripts.get('launch-gate')!r}"
    )


def test_setuptools_packages_covers_both_packages() -> None:
    packages = _pyproject()["tool.setuptools"]["packages"]
    assert isinstance(packages, list), "[tool.setuptools] packages must be a list"
    assert "launch_gate" in packages, "packages must include 'launch_gate'"
    assert "launch_gate.checks" in packages, "packages must include 'launch_gate.checks'"


def test_console_script_target_is_importable() -> None:
    # The declared target launch_gate.cli:main must actually resolve to a
    # callable (a wrong target would break the installed CLI).
    from launch_gate.cli import main

    assert callable(main)


# ---------------------------------------------------------------------------
# 3. Module entrypoint (python3 -m launch_gate) + README consistency.
# ---------------------------------------------------------------------------


def test_main_module_exists() -> None:
    assert MAIN_MODULE.is_file(), "launch_gate/__main__.py must exist"


def test_main_module_source_calls_cli_main() -> None:
    source = MAIN_MODULE.read_text(encoding="utf-8")
    # It must pull ``main`` from launch_gate.cli ...
    assert re.search(r"from\s+launch_gate\.cli\s+import\s+main\b", source), (
        "__main__.py must import main from launch_gate.cli"
    )
    # ... and invoke it (the entrypoint call).
    assert re.search(r"\bmain\s*\(", source), "__main__.py must call main()"


def test_readme_documents_module_entrypoint() -> None:
    readme = README.read_text(encoding="utf-8")
    assert "python3 -m launch_gate" in readme, (
        "README must document the 'python3 -m launch_gate' entrypoint"
    )


def test_readme_documents_console_script() -> None:
    readme = README.read_text(encoding="utf-8")
    assert "launch-gate" in readme, "README must document the 'launch-gate' console script"
