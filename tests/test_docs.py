"""The Markdown docs must point at things that exist and quote numbers the pipeline produces."""
import ast
import importlib
import re

import pytest

from steelenergy import config

DOCS = ["README.md", "WORKFLOW.md", "CLAUDE.md"]
# Relative paths in the docs are written from the repo root or from these folders.
BASES = ["", "web/", "src/steelenergy/", "notebooks/"]
GENERATED = ("build/", "outputs/")
REPO_ROOT_NAME = "steel-energy-analysis/"
MODULES = {name: f"steelenergy.{name}" for name in
           ("config", "io", "validate", "features", "eda", "stats", "anomaly", "scenarios",
            "export", "pipeline", "labels", "plots")}
MODULES.update({"classify": "steelenergy.models.classify", "regress": "steelenergy.models.regress",
                "split": "steelenergy.models.split"})
# Constants the docs may cite that live outside the package (rule tables, chapter lists).
SCRIPTS_WITH_CONSTANTS = ["tests/test_architecture.py", "notebooks/build_notebook.py", "web/build.py"]


def _script_constants():
    names = set()
    for rel in SCRIPTS_WITH_CONSTANTS:
        for node in ast.parse((config.ROOT / rel).read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign):
                names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    return names


def _code_spans(doc):
    return re.findall(r"`([^`\n]+)`", (config.ROOT / doc).read_text(encoding="utf-8"))


def _looks_like_path(token):
    # Paths on the reader's machine (~/…, %USERPROFILE%\…) and "n/a" are not repo paths.
    if token.startswith(("~", "%")) or re.fullmatch(r"[a-z]/[a-z]", token):
        return False
    return ("/" in token or re.search(r"\.(py|md|j2|css|js|toml|ipynb|csv|zip|json|html)$", token)) \
        and " " not in token and "*" not in token and "…" not in token and not token.startswith("http")


@pytest.mark.parametrize("doc", DOCS)
def test_cited_paths_exist(doc):
    missing = []
    for token in filter(_looks_like_path, _code_spans(doc)):
        path = token.split("::")[0]
        if path.startswith(GENERATED) or path.startswith("/") or token == REPO_ROOT_NAME:
            continue
        if not any((config.ROOT / base / path).exists() for base in BASES):
            missing.append(token)
    assert not missing, f"{doc} cites paths that do not exist: {missing}"


@pytest.mark.parametrize("doc", DOCS)
def test_cited_names_exist(doc):
    missing = []
    for token in _code_spans(doc):
        if _looks_like_path(token):
            continue
        for mod, attr in re.findall(r"\b([a-z_]+)\.([A-Za-z_][A-Za-z0-9_]*)", token):
            if mod in MODULES and not hasattr(importlib.import_module(MODULES[mod]), attr):
                missing.append(token)
        is_constant = re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", token)
        in_package = any(hasattr(importlib.import_module(m), token) for m in MODULES.values())
        if is_constant and not in_package and token not in _script_constants():
            missing.append(token)
    assert not missing, f"{doc} cites names that do not exist: {missing}"


def test_readme_results_match_pipeline(payload):
    readme = (config.ROOT / "README.md").read_text(encoding="utf-8")
    k, reg = payload["kpi"], {r["model"]: r for r in payload["regression"]["scores"]}
    rev = {r["model"]: r for r in payload["classification"]["reverse"]}
    pf = payload["scenarios"]["pf_default"]
    shift = next(s for s in payload["scenarios"]["shift"] if abs(s["fraction"] - 0.1) < 1e-9)
    expected = [
        f"1년 시간의 {k['weekday_daytime']['slot_share'] * 100:.0f}%",
        f"**{k['weekday_daytime']['kwh_share'] * 100:.0f}%**",
        f"**{reg['hgb']['test_mae']:.2f} kWh**",
        f"오차율 {reg['hgb']['test_wape'] * 100:.0f}%",
        f"오차가 {reg['hgb']['test_mae_vs_best_naive'] * 100:.0f}% 작습니다",
        f"평일·주말 구분과 시각·계절만으로 {rev['schedule_lookup_season']['macro_f1']:.2f}",
        f"과거 사용량까지 쓰면 {rev['hgb']['macro_f1']:.2f}",
        f"평일 공휴일 {k['weekday_holidays']}일 중 **{k['holiday_shutdowns']}일**",
        f"평일 **{k['weekday_shutdowns']}일**",
        f"이상 판정은 **{k['anomalous_days']}일**",
        f"역률을 {payload['meta']['pf_target']:.2f}까지",
        f"**{(1 - pf['kvarh_after'] / pf['kvarh_before']) * 100:.0f}%**",
        f"**{(shift['total_cost_before'] - shift['total_cost_after']) / 1e4:,.0f}만 원**",
        f"`Steel_industry_data.csv`({payload['meta']['rows']:,}행)",
    ]
    stale = [e for e in expected if e not in readme]
    assert not stale, f"README results differ from the pipeline; expected to find: {stale}"


def _slug(heading):
    """GitHub's heading anchor: lower-case, punctuation dropped, spaces to hyphens."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


@pytest.mark.parametrize("doc", DOCS)
def test_markdown_renders_and_anchors_resolve(doc):
    from markdown_it import MarkdownIt

    src = (config.ROOT / doc).read_text(encoding="utf-8")
    html = MarkdownIt("commonmark").enable("table").render(src)
    prose = re.sub(r"<[^>]+>", "", re.sub(r"<code>.*?</code>|<pre>.*?</pre>", "", html, flags=re.S))
    # A literal ** in the rendered text means bold failed (e.g. **64%**가 under CommonMark rules).
    assert "**" not in prose, f"{doc}: unrendered bold near: {re.findall(r'.{0,20}[*][*].{0,20}', prose)}"

    targets = {"": src, "WORKFLOW.md": (config.ROOT / "WORKFLOW.md").read_text(encoding="utf-8")}
    for file, anchor in re.findall(r"\]\(((?:WORKFLOW\.md)?)#([^)]+)\)", src):
        headings = {_slug(h) for h in re.findall(r"^#{1,6} (.+)$", targets[file], flags=re.M)}
        assert anchor in headings, f"{doc}: link #{anchor} has no matching heading"
