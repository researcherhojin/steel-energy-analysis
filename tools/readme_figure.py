"""Draw the README's hour × weekday heatmap from outputs/analysis.json → docs/images/.

    uv run python tools/readme_figure.py

Same cells as the dashboard heatmap (views.profileCells): mean kWh per 15-min slot = total sum / total
count over every month and tariff band. Light and dark versions use the web sequential tokens, so the
README matches GitHub's theme.
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from steelenergy import config, plots  # noqa: E402

OUT_DIR = config.ROOT / "docs" / "images"
DOW_KO = ["월", "화", "수", "목", "금", "토", "일"]
# --surface, --ink-2, --ink-3, --seq-lo/mid/hi from web/common/tokens.css.
THEMES = {
    "light": {"surface": "#ffffff", "ink": "#485261", "muted": "#626c7b",
              "seq": ["#f3f7fc", "#6da7ec", "#0d366b"]},
    "dark": {"surface": "#151a21", "ink": "#a9b2be", "muted": "#7c8694",
             "seq": ["#18212c", "#2a78d6", "#b7d3f6"]},
}


def hour_dow_mean(profile: dict) -> np.ndarray:
    """7 × 24 grid of mean kWh per slot (rows Mon–Sun, columns hour of interval start)."""
    total, count = np.zeros((7, 24)), np.zeros((7, 24))
    for dow, hour, s, n in zip(profile["dow"], profile["hour"], profile["sum"], profile["count"],
                               strict=True):
        total[dow, hour] += s
        count[dow, hour] += n
    return total / count


def draw(grid: np.ndarray, theme: dict, path) -> None:
    font = plots.korean_font()
    plt.rcParams.update({"font.family": font or "DejaVu Sans", "axes.unicode_minus": False})
    fig, ax = plt.subplots(figsize=(10, 3.4), dpi=150, facecolor=theme["surface"])
    ax.set_facecolor(theme["surface"])
    cmap = LinearSegmentedColormap.from_list("seq", theme["seq"])
    mesh = ax.pcolormesh(grid, cmap=cmap, vmin=0, edgecolors=theme["surface"], linewidth=1.5)
    ax.invert_yaxis()
    ax.set_xticks(np.arange(0, 24, 3) + 0.5, [f"{h:02d}" for h in range(0, 24, 3)])
    ax.set_yticks(np.arange(7) + 0.5, DOW_KO)
    ax.set_xlabel("시각 (15분 구간 시작, 시)", color=theme["ink"])
    ax.set_ylabel("요일", color=theme["ink"], rotation=0, labelpad=14, va="center")
    ax.tick_params(colors=theme["muted"], length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    bar = fig.colorbar(mesh, ax=ax, pad=0.015, fraction=0.03)
    bar.set_label("평균 사용량 (kWh / 15분)", color=theme["ink"])
    bar.ax.tick_params(colors=theme["muted"], length=0)
    bar.outline.set_visible(False)
    fig.tight_layout()
    fig.savefig(path, facecolor=theme["surface"])
    plt.close(fig)


def main() -> None:
    data = json.loads((config.OUTPUT_DIR / "analysis.json").read_text(encoding="utf-8"))
    grid = hour_dow_mean(data["profile"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, theme in THEMES.items():
        path = OUT_DIR / f"hour-weekday-{name}.png"
        draw(grid, theme, path)
        print(f"wrote {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
