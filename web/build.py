"""Render the dashboard and report from outputs/analysis.json.

    uv run python web/build.py
"""
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from steelenergy import config

WEB = Path(__file__).resolve().parent
PAGES = {"dashboard/index.html.j2": "dashboard.html", "report/report.html.j2": "report.html"}


def num(x, digits=0):
    return f"{x:,.{digits}f}"


def pct(x, digits=0):
    return f"{x * 100:.{digits}f}%"


def won(x):
    """KRW in 만 원 (10^4) units, the way Korean budget tables usually read."""
    return f"{x / 1e4:,.0f}만 원"


def md(date):
    """'2018-02-14…' → '2/14'."""
    return f"{int(date[5:7])}/{int(date[8:10])}"


def rdiff(after, before, scale=1.0, digits=0):
    """Signed difference of the *displayed* (rounded) values, so a table's columns add up."""
    a, b = round(after / scale, digits), round(before / scale, digits)
    diff = a - b
    sign = "+" if diff > 0 else "−" if diff < 0 else "±"
    return sign + num(abs(diff), digits)


def run_label(run):
    """A shutdown run from the payload → '5/1' or '8/1–8/3'."""
    return md(run["start"]) if run["days"] == 1 else f"{md(run['start'])}–{md(run['end'])}"


def by(rows, key, value):
    """The one record in `rows` whose `key` equals `value`; fails loudly otherwise."""
    hits = [r for r in rows if r[key] == value]
    if len(hits) != 1:
        raise KeyError(f"{key}={value!r}: {len(hits)} matches")
    return hits[0]


def derived(d: dict) -> dict:
    """Selections the templates need. Picks values out of the payload; computes nothing new."""
    reg = {r["model"]: r for r in d["regression"]["scores"]}
    clf = {r["model"]: r for r in d["classification"]["scores"]}
    shift10 = by(d["scenarios"]["shift"], "fraction", d["meta"]["shift_example"])
    holidays = d["anomaly"]["holidays"]
    groups = [(run_label(r), d["date_notes"].get(r["start"][:10], ""))
              for r in d["anomaly"]["shutdown_runs"]]
    return {
        "pf_low": d["pf_by_load"][0]["pf"],
        "reg": reg,
        "reg_gain": reg["hgb"]["test_mae_vs_best_naive"],
        "clf": clf,
        "shift10": shift10,
        "pf95": d["scenarios"]["pf_default"],
        "tests": {t["test"]: t for t in d["stats"]["tests"]},
        "holidays_weekday": [h for h in holidays if not h["is_weekend"]],
        "holidays_weekend": [h for h in holidays if h["is_weekend"]],
        "holidays_running": [h for h in holidays if not h["is_weekend"] and not h["shutdown"]],
        "holidays_closed": [h for h in holidays if h["shutdown"]],
        "sens": d["anomaly"]["sensitivity"],
        "shutdown_groups": groups,  # one row per consecutive shutdown run (eda.shutdown_runs)
        "shutdown_notes": list(dict.fromkeys(note for _, note in groups)),
        "reverse": {r["model"]: r for r in d["classification"]["reverse"]},
        "errors_by_daytype": {r["daytype"]: r for r in d["classification"]["errors_by_daytype"]},
        "lt": {r["load_type"]: r for r in d["load_types"]},
        "month": {m["month"]: m for m in d["monthly"]},
    }


def render(data_path: Path = config.OUTPUT_DIR / "analysis.json",
           out_dir: Path = config.BUILD_DIR) -> list[Path]:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    env = Environment(loader=FileSystemLoader(WEB), undefined=StrictUndefined, autoescape=False,
                      keep_trailing_newline=True)
    env.filters.update(num=num, pct=pct, won=won, md=md)
    env.globals.update(rdiff=rdiff)
    env.globals.update(by=by)
    # Escape "</" so the payload cannot close its own <script> tag.
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    context = {**data, **derived(data), "data_json": data_json}
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for template, name in PAGES.items():
        path = out_dir / name
        path.write_text(env.get_template(template).render(context), encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    for p in render():
        print(f"wrote {p.relative_to(config.ROOT)} ({p.stat().st_size / 1024:.0f} KB)")
