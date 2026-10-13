"""Module boundaries, written once and checked against the actual imports.

Layers: config/units → io → validate → features → analysis (eda, stats, anomaly, scenarios,
models.*) → export → pipeline. Presentation code (labels, plots, web/build.py, the notebook
builder) never reaches into analysis modules.
"""
import ast

import pytest

from steelenergy import config

PKG = config.ROOT / "src" / "steelenergy"

# module → the steelenergy modules it may import. Anything not listed here is a failure.
ALLOWED = {
    "config": set(),
    "units": {"config"},
    "labels": set(),
    "io": {"config"},
    "validate": {"config"},
    "features": {"config"},
    "eda": {"config", "units"},
    "stats": {"config"},
    "anomaly": {"config"},
    "scenarios": {"config", "units"},
    "models.split": {"config"},
    "models.regress": {"config", "features", "models.split"},
    "models.classify": {"config", "features", "models.split"},
    "plots": set(),
    "export": {"config", "labels"},
    "pipeline": {"config", "io", "validate", "features", "eda", "stats", "anomaly", "scenarios",
                 "models.split", "models.regress", "models.classify", "export"},
}
SCRIPTS = {
    "web/build.py": {"config"},
    "web/pages.py": {"config"},
    "notebooks/build_notebook.py": {"config"},
    "notebooks/check_notebook.py": set(),
    "tools/check_platforms.py": set(),
    "tools/readme_figure.py": {"config", "plots"},
}


def _imports(path):
    """steelenergy modules imported by a file, as dotted names relative to the package."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("steelenergy"):
            base = node.module.removeprefix("steelenergy").lstrip(".")
            for alias in node.names:
                name = f"{base}.{alias.name}".lstrip(".") if base in ("", "models") else base
                found.add(name)
        elif isinstance(node, ast.Import):
            found |= {a.name.removeprefix("steelenergy.") for a in node.names
                      if a.name.startswith("steelenergy.")}
    return {m for m in found if m != "models"}


def _module_name(path):
    rel = path.relative_to(PKG).with_suffix("")
    return ".".join(p for p in rel.parts if p != "__init__")


def test_every_module_has_a_rule():
    modules = {_module_name(p) for p in PKG.rglob("*.py")} - {"", "models"}
    assert modules == set(ALLOWED), f"add these to ALLOWED: {modules - set(ALLOWED)}"


@pytest.mark.parametrize("path", sorted(PKG.rglob("*.py")), ids=lambda p: _module_name(p) or "__init__")
def test_package_imports_follow_layers(path):
    name = _module_name(path)
    if name in ("", "models"):
        return
    extra = _imports(path) - ALLOWED[name]
    assert not extra, f"{name} imports {sorted(extra)}, which its layer does not allow"


@pytest.mark.parametrize("script", sorted(SCRIPTS))
def test_presentation_scripts_only_read_config(script):
    extra = _imports(config.ROOT / script) - SCRIPTS[script]
    assert not extra, f"{script} imports {sorted(extra)}; it must work from analysis.json alone"
