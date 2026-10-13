# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Analysis of the UCI "Steel Industry Energy Consumption" dataset (`Steel_industry_data.csv`, 15-min readings for 2018, DAEWOO Steel, Gwangyang; CC BY 4.0). Deliverables: an analysis notebook, a static HTML dashboard, and an HTML report. Narrative text is Korean; code and identifiers are English.

Docs: `README.md` (what and results, Korean), `WORKFLOW.md` (step-by-step reproduction, Korean), this file. `tests/test_docs.py` checks that file paths and config names cited in the docs exist, that the Markdown renders under CommonMark (no stray `**`, e.g. `**64%**가` fails) and in-page anchors resolve, and that README's '핵심 결과' section matches `outputs/analysis.json`; when an analysis change moves a number, update that section (and any changed command or name in WORKFLOW.md) in the same change. The README check matches exact phrases (e.g. "평일·주말 구분과 시각·계절만으로 0.88"), so if you reword it, update `expected` in `test_readme_results_match_pipeline` too.

## Commands

```bash
uv sync                                              # install (Python pinned to 3.12)
uv run pytest                                        # all tests (1–3 min: a session fixture runs the full pipeline once)
uv run pytest tests/test_io.py::test_midnight_rows_move_to_next_day   # single test
uv run ruff check .                                  # lint (also lints the notebook)
uv run python -m steelenergy.pipeline                # run every analysis step → outputs/analysis.json
uv run python web/build.py                           # render build/dashboard.html, build/report.html from that JSON
uv run python web/pages.py                           # wrap them as full documents + index → build/site/ (GitHub Pages)
uv run python tools/readme_figure.py                 # redraw docs/images/hour-weekday-{light,dark}.png for the README
uv run python notebooks/build_notebook.py             # regenerate the notebook (prose numbers from the JSON)
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb
uv run python notebooks/check_notebook.py             # error cells: 0 (exit 1 otherwise)
uv run python tools/check_platforms.py                # every supported OS/CPU installs from wheels
```

Supported platforms: Windows x86_64 and ARM64, macOS Apple Silicon and Intel, Linux x86_64 and ARM64. 32-bit Windows is unsupported (pandas, scipy, scikit-learn and matplotlib ship no win32 wheels) and is reported as `n/a` by `tools/check_platforms.py`. Keep it that way:
- After any `uv add`/`uv remove`/`uv lock`, run `tools/check_platforms.py`. A dependency without wheels for one of the six targets is a regression. statsmodels was dropped for exactly this reason (no Windows ARM64 wheel); `stats.holm` replaces its `multipletests(method="holm")` and is tested against a hand computation.
- `[tool.uv] constraint-dependencies` in `pyproject.toml` pins `argon2-cffi-bindings<26` on Intel macOS only, because 26.x has no wheel there.
- Commands in the docs must work unchanged in bash/zsh and PowerShell/cmd: one command per line, no `&&` chains or line continuations, quoted paths (a clone's path may contain spaces or Korean), forward slashes are fine. Open every text file with an explicit `encoding="utf-8"` (Windows defaults to cp949, which breaks Korean text). `.gitattributes` fixes LF line endings except the raw CSV.
- Notebook figures pick the first installed font in `plots.KOREAN_FONTS` (AppleGothic, Malgun Gothic, NanumGothic, Noto Sans CJK KR, Noto Sans KR) and warn if none is found.

`web/build.py` and `notebooks/build_notebook.py` both read `outputs/analysis.json`, so run the pipeline first. If `import steelenergy` fails right after `uv sync`, run `uv sync --reinstall-package steelenergy` (the editable install was created before `src/` existed). `build/` and `outputs/analysis.json` are gitignored and can be regenerated at any time. `outputs/v1/` and `outputs/v2/` hold hand-saved PDFs that nothing regenerates: never delete or overwrite them. Never hand-edit `notebooks/analysis.ipynb`; edit `build_notebook.py` (its markdown goes through `fix_josa()`, which picks the Korean particle after a number). Don't hard-code volatile facts such as the test count in the docs. Spelling: `cspell.json` + `.cspell/project-words.txt` (grouped by source); `npx cspell lint --dot "**/*"` must report 0 issues. Fix real typos (US spelling) instead of adding them to the dictionary.

## Architecture

All computation lives in the analysis modules of `src/steelenergy/`. The allowed imports per module are written once in `tests/test_architecture.py` (`ALLOWED`) and enforced against the real imports; update that table deliberately when you add a module, never to silence a failure.
- Base: `config` (every tunable: paths, split dates, thresholds, holidays, tariffs, model hyperparameters, bootstrap/permutation counts, top-N list lengths), `units` (`power_factor`, `KW_PER_KWH_SLOT`), `labels` (Korean display names and `DATE_NOTES`).
- Analysis: `io → validate → features`, then `eda`, `stats`, `anomaly`, `scenarios`, and `models/split.py`, `models/regress.py`, `models/classify.py`. Each analysis module exposes `run()` returning one result dataclass (`eda.EdaResults`, `stats.StatsResults`, `anomaly.AnomalyResults`, `scenarios.ScenarioResults`; `regress.evaluate` → `RegressionReport`, `classify.run` → `ClassifierReport` with the reversed check attached). Analysis modules never import each other sideways, nor `export`, `pipeline`, `labels` or `plots`.
- Assembly: `pipeline.run()` wires the `run()`s together into `Results`; `export.payload()` only maps those results to JSON keys, joins labels and cleans types. If export needs a number that does not exist yet, add it to the owning module's result, not to export. Adding an analysis therefore goes: module function + its result dataclass/`run()` (+ `ALLOWED` if new module) → `pipeline.Results` → the matching `export` section function → template/tab file and notebook chapter function → a test (WORKFLOW.md §6). Tests build the payload in memory and write only to `tmp_path`, so a green `pytest` does not refresh `outputs/analysis.json` or `build/`; rerun the pipeline and builds to see changes.
- The notebook calls the same module functions step by step and adds the interpretation. Its prose is generated by `notebooks/build_notebook.py`: `_context()` reads the JSON, and one function per chapter (`CHAPTERS`) receives only the values it quotes.
- `plots.py` is notebook-only matplotlib and never computes results.

`web/` is presentation only:
- Jinja templates (`web/dashboard/index.html.j2`, `web/report/report.html.j2`) inline the shared `web/common/tokens.css`, `web/common/charts.js` (ECharts theme plumbing) and `web/common/views.js` (chart builders used by both pages), plus the JSON payload.
- The dashboard script is split: `web/dashboard/ui.js` (shared helpers, `window.DashUI`), one file per tab in `web/dashboard/tabs/` (each registers `window.DashTabs.<tab>(D)`), and `web/dashboard/dashboard.js` (tab switching). They are concatenated into one `<script>` in that include order, so a tab file may only use what earlier files define.
- `web/build.py` and `notebooks/build_notebook.py` import nothing from the package except `config`; everything else comes from `outputs/analysis.json`.
- `web/build.py` uses `StrictUndefined`, so a missing key fails the build. Every number on the pages comes from the JSON; don't hardcode figures in templates.
- `derived()` in `web/build.py` may only *select* or format values from the payload (e.g. `rdiff` for differences of displayed, rounded values), never compute new analysis.
- Output files start with `<title>` and have no doctype/head, because the Artifact publisher wraps them in its own skeleton. `web/pages.py` adds the doctype/charset/viewport and a landing page for GitHub Pages; `.github/workflows/pages.yml` runs `checks.yml` (ruff, `notebooks/check_notebook.py`, `tools/check_platforms.py`, cspell on Linux; pytest on macOS), then pipeline → build → pages on every push to `main`, and deploys `build/site/` (https://researcherhojin.github.io/steel-energy-analysis/). Pull requests run the same `checks.yml` via `ci.yml`. Keep `build.py`'s fragment output unchanged (`test_build` checks it).
- The README figure (`tools/readme_figure.py`) is committed under `docs/images/`; it aggregates `profile` as total sum / total count like `views.profileCells` and uses the `--seq-*` tokens. Rerun it and commit the PNGs when the analysis changes.
- Colors are tokens in `web/common/tokens.css` with light and dark values. Chart palettes were checked with the dataviz skill's palette validator (not part of this repo; keep the existing palette unless asked to change it); the daily-anomaly chart encodes day kinds by color *and* marker shape (circle/square/triangle/diamond), so keep both if you change either. Every chart names its axes with units (`yTitle`/`xTitle` in `web/common/charts.js`); bars always start at zero, and truncated axes use dots instead.
- `fmt` in `web/common/charts.js` rounds half-to-even to match Python's `format()`, so a value reads the same on both pages.

## Data and modeling rules that are easy to break

- **Midnight rows:** each day's last row is stamped `DD/MM/YYYY 00:00` with the *same* date (`NSM == 0`). It is really the 24:00 reading, and `io.fix_timestamps` moves it to the next day.
- **Operating day:** the index is the interval *end*, and `operating_day` = timestamp − 15 min. `Day_of_week`/`WeekStatus` labels match `operating_day`, not the calendar date. Calendar features (`slot`, `hour`, `dow`) are keyed to the interval start.
- **CO₂:** values are rounded to 0.01 t (60% are zero) and are ≈ kWh × a constant factor. Never use CO₂ as a model input. The headline factor is the annual ratio of sums (≈0.421 t/MWh; `stats.emission_factor()["ratio_of_sums"]`, exported as `kpi.co2_t_per_mwh`); the daily through-origin slope (≈0.433) appears only in the notebook.
- **`Load_Type`:** this is a seasonal time-of-use band schedule, not measured load. The schedule switches between Mar–Oct and Nov–Feb (`config.WINTER_MONTHS`).
  - Models use `is_winter` and must **not** use `month`. In the Jan–Oct training window `is_winter == 1` and `month <= 2` select exactly the same rows, so a tree picks one by column order, and Nov/Dec predictions then flip between 0.61 and 0.94 macro-F1 (`hgb_season_month_first` vs `hgb_season_month_last`).
  - The season-blind first attempt is kept in `classify.candidates()` on purpose, because the notebook and report discuss it.
- **Forecasting:** the forecast is one step ahead (15 min). Features are calendar + season + lags/rolling that end at t−1. Same-interval electrical readings (`features.SAME_INTERVAL`) are allowed only in the labelled classification ablation.
- **Split:** the split is chronological (train ≤ Sep, valid Oct, test Nov–Dec). Test is scored once, after refitting on train+valid. The example forecast week is `config.FORECAST_WEEK` (operating days); year-specific values live in `config.py` and `labels.DATE_NOTES`, and page titles take the year from the data (`meta.year`).
- **Statistical tests:** tests run on daily aggregates, with week-block bootstrap CIs. Even daily totals are autocorrelated (lag-1 ≈ 0.4), so conclusions rest on effect sizes and `ci_excludes_null`; p-values are reference only and are not shown in the report.
- **Holidays and shutdowns:** `config.KR_HOLIDAYS_2018` is excluded from the daily anomaly reference and never flagged; weekend holidays are not judged as shutdowns. Non-holiday weekday shutdowns (single or multi-day; z-scores miss multi-day runs) come from `eda.weekday_shutdowns`, a ratio rule against `eda.regular_weekday_median`; `eda.shutdown_runs` groups them into consecutive runs. The daily z-score's scale uses the whole year, so it is a retrospective review, not an alarm.
- **Tariffs:** all tariff values in `config.TARIFF_ASSUMPTIONS` are illustrative assumptions and must be labelled as such wherever money appears.
- **Load shift scenario:** moved kWh carries its own lagging kVarh (source-slot ratio); daily kWh and kVarh are conserved and cost lines must sum to the total (tests cover this).
- **Classification honesty:** the Nov–Dec test scores for Load_Type are exploratory (the season fix was chosen after seeing them); `classify.reverse_check` is the separate reversed split. Say so wherever those scores appear.
- **Cross-platform numbers:** with the same lockfile and seeds, the boosted trees and isolation forest still differ in the last digits across OS/CPU (Linux x86_64 gave test MAE 3.92 vs 3.94 on Apple Silicon, 207 vs 210 episodes). README's numbers come from Apple Silicon macOS, so `test_readme_results_match_pipeline` can fail elsewhere, and the Pages workflow builds on `macos-latest` with `pytest` gating the deploy. Regenerate README numbers on Apple Silicon.
- **Wording:** causes of shutdowns/anomalies are not knowable from meter data; phrase them as calendar matches or possibilities. Use "무효전력량" for kVarh quantities.
