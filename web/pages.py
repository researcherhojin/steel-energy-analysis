"""Wrap build/*.html as standalone pages for GitHub Pages → build/site/.

    uv run python web/pages.py

web/build.py writes fragments that start with <title> (the Artifact publisher adds its own
skeleton). A plain web host needs the doctype, charset and viewport, so this adds them and a
small landing page that links both pages. It reads analysis.json only for the year.
"""
import json
from html import escape
from pathlib import Path

from steelenergy import config

WEB = Path(__file__).resolve().parent
SITE = config.BUILD_DIR / "site"
PAGES = ["report.html", "dashboard.html"]
REPO_URL = "https://github.com/researcherhojin/steel-energy-analysis"

HEAD = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
"""


def standalone(fragment: str) -> str:
    """A <title>-first fragment → a full document (the parser moves body content out of <head>)."""
    return HEAD + fragment + ("" if fragment.endswith("\n") else "\n") + "</html>\n"


def landing(year: int) -> str:
    tokens = (WEB / "common" / "tokens.css").read_text(encoding="utf-8")
    title = escape(f"제철소 전력 사용 분석 ({year})")
    return f"""<title>{title}</title>
<style>
{tokens}
main {{ max-width: 640px; margin: 0 auto; padding: 48px 16px; }}
h1 {{ font-size: var(--step-2); font-weight: 600; margin: 0 0 8px; }}
p {{ color: var(--ink-2); margin: 0 0 24px; }}
a.card {{ display: block; padding: 16px 20px; margin-bottom: 12px; background: var(--surface);
  border: 1px solid var(--rule); border-radius: var(--radius); color: var(--ink); text-decoration: none; }}
a.card:hover {{ border-color: var(--accent); }}
a.card b {{ display: block; font-size: var(--step-1); font-weight: 600; margin-bottom: 4px; }}
a.card span {{ color: var(--ink-3); font-size: var(--step--1); }}
footer {{ margin-top: 32px; font-size: var(--step--1); color: var(--ink-3); }}
footer a {{ color: var(--accent); }}
</style>
<main>
<h1>{title}</h1>
<p>UCI Steel Industry Energy Consumption 데이터셋(대우제철 광양 공장) 분석 결과입니다.</p>
<a class="card" href="report.html"><b>보고서</b><span>결론과 근거를 순서대로 정리한 문서</span></a>
<a class="card" href="dashboard.html"><b>대시보드</b>
<span>월·시간대·요금 구간을 골라 가며 수치를 탐색하는 화면</span></a>
<footer>코드와 분석 노트북: <a href="{REPO_URL}">GitHub 저장소</a> · 데이터 CC BY 4.0</footer>
</main>
"""


def write(build_dir: Path = config.BUILD_DIR, data_path: Path = config.OUTPUT_DIR / "analysis.json",
          site_dir: Path = SITE) -> list[Path]:
    year = json.loads(data_path.read_text(encoding="utf-8"))["meta"]["year"]
    site_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name in PAGES:
        path = site_dir / name
        path.write_text(standalone((build_dir / name).read_text(encoding="utf-8")), encoding="utf-8")
        written.append(path)
    index = site_dir / "index.html"
    index.write_text(standalone(landing(year)), encoding="utf-8")
    return [index, *written]


if __name__ == "__main__":
    for p in write():
        print(f"wrote {p.relative_to(config.ROOT)} ({p.stat().st_size / 1024:.0f} KB)")
