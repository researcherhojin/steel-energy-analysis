"""Matplotlib helpers for the notebook. Takes tables, never computes analysis results."""
import warnings

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

INK = "#1d2430"
MUTED = "#8a93a1"
GRID = "#e6e8ec"
ACCENT = "#1f6f8b"
WARN = "#c2552d"
LOAD_COLORS = {"Light_Load": "#b9d3de", "Medium_Load": "#5b9bb4", "Maximum_Load": "#1f4e66"}
DOW_KO = ["월", "화", "수", "목", "금", "토", "일"]
BAND_KO = {"Light_Load": "경부하", "Medium_Load": "중간부하", "Maximum_Load": "최대부하"}


# Korean-capable fonts in order of preference: macOS, Windows, then the usual Linux packages
# (fonts-nanum, fonts-noto-cjk).
KOREAN_FONTS = ["AppleGothic", "Malgun Gothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans KR"]


def korean_font() -> str | None:
    """First installed font from KOREAN_FONTS, or None."""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    return next((name for name in KOREAN_FONTS if name in installed), None)


def setup() -> None:
    font = korean_font()
    if font is None:
        warnings.warn("No Korean font found; Hangul in figures will show as boxes. "
                      f"Install one of: {', '.join(KOREAN_FONTS)}.", stacklevel=2)
    mpl.rcParams.update({
        "font.family": font or "DejaVu Sans",
        "axes.unicode_minus": False,
        "figure.dpi": 110,
        "figure.figsize": (9, 3.6),
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        
        "axes.titleweight": "normal",
        "axes.titlesize": 12,
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "legend.frameon": False,
    })


def caption(ax, text: str) -> None:
    ax.annotate(text, xy=(0, -0.2), xycoords="axes fraction", fontsize=8, color=MUTED, va="top")


def heatmap_hour_dow(profile: pd.DataFrame, ax=None):
    ax = ax or plt.subplots(figsize=(6, 5))[1]
    im = ax.imshow(profile.values, aspect="auto", cmap="Blues", origin="upper")
    ax.set_xticks(range(7), DOW_KO)
    ax.set_yticks(range(0, 24, 2), [f"{h:02d}시" for h in range(0, 24, 2)])
    ax.grid(False)
    plt.colorbar(im, ax=ax, label="15분당 평균 kWh", shrink=0.8)
    return ax


def monthly(monthly: pd.DataFrame):
    """Daily-mean kWh and power factor as two stacked panels sharing the month axis."""
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(9, 4.6), sharex=True,
                                      gridspec_kw={"height_ratios": [2, 1]})
    top.bar(monthly.index, monthly["kwh_per_day"], color=ACCENT, width=0.65)
    top.set_ylabel("일평균 kWh")
    bottom.plot(monthly.index, monthly["pf"], color=ACCENT, marker="o", ms=3, lw=1.2)
    bottom.axhline(0.9, color=MUTED, lw=0.8)
    bottom.set_ylabel("역률")
    bottom.set_xticks(monthly.index, [f"{m}월" for m in monthly.index])
    fig.subplots_adjust(bottom=0.16, hspace=0.12)
    return top, bottom


def load_type_distribution(df: pd.DataFrame, ax=None):
    ax = ax or plt.subplots()[1]
    order = list(LOAD_COLORS)
    data = [df.loc[df["load_type"] == t, "kwh"] for t in order]
    bp = ax.boxplot(data, vert=False, widths=0.5, patch_artist=True, showfliers=True,
                    flierprops={"marker": ".", "markersize": 2, "markeredgecolor": MUTED, "alpha": 0.4},
                    medianprops={"color": INK})
    for patch, t in zip(bp["boxes"], order, strict=True):
        patch.set_facecolor(LOAD_COLORS[t])
        patch.set_edgecolor(MUTED)
    ax.set_yticks(range(1, 4), [BAND_KO[t] for t in order])
    ax.set_xlabel("15분 사용량 (kWh) · 점은 상자 범위 밖의 기록")
    return ax


def tou_schedule(schedule: pd.DataFrame, ax=None):
    ax = ax or plt.subplots(figsize=(9, 1.8))[1]
    code = {t: i for i, t in enumerate(LOAD_COLORS)}
    grid = schedule[["summer", "winter"]].replace(code).T.values.astype(float)
    cmap = mpl.colors.ListedColormap(list(LOAD_COLORS.values()))
    ax.imshow(grid, aspect="auto", cmap=cmap, vmin=-0.5, vmax=2.5)
    ax.set_yticks([0, 1], ["3–10월", "11–2월"])
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}" for h in range(0, 24, 2)])
    ax.set_xlabel("시각 (시, 구간 시작)")
    ax.set_xticks([x - 0.5 for x in range(25)], minor=True)
    ax.set_yticks([-0.5, 0.5, 1.5], minor=True)
    ax.grid(which="minor", color="white", lw=1.5)
    ax.tick_params(which="minor", length=0)
    handles = [mpatches.Patch(color=c, label=BAND_KO[k]) for k, c in LOAD_COLORS.items()]
    ax.legend(handles=handles, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.45))
    return ax


def daily_timeline(daily: pd.DataFrame, flagged: pd.DataFrame | None = None, ax=None):
    ax = ax or plt.subplots(figsize=(10, 3.4))[1]
    ax.plot(daily.index, daily["kwh"], color=MUTED, lw=0.8, label="일별")
    ax.plot(daily.index, daily["kwh"].rolling(7, center=True).mean(), color=ACCENT, lw=1.6,
            label="7일 이동평균")
    if flagged is not None and len(flagged):
        ax.scatter(flagged.index, flagged["kwh"], color=WARN, s=22, zorder=3, label="이상 일자")
    ax.set_ylabel("일 사용량 (kWh)")
    ax.legend(loc="upper right")
    return ax


def scores_bar(scores: pd.Series, highlight: str, ax=None, xlabel=""):
    ax = ax or plt.subplots(figsize=(7, 0.45 * len(scores) + 0.8))[1]
    colors = [ACCENT if i == highlight else GRID for i in scores.index]
    ax.barh(scores.index, scores.values, color=colors, edgecolor=MUTED, linewidth=0.4)
    for y, v in enumerate(scores.values):
        ax.text(v, y, f" {v:.3f}", va="center", fontsize=8, color=INK)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel)
    ax.grid(axis="y", visible=False)
    return ax


def confusion(cm: pd.DataFrame, ax=None):
    ax = ax or plt.subplots(figsize=(4.2, 3.6))[1]
    share = cm.div(cm.sum(axis=1), axis=0)
    ax.imshow(share.values, cmap="Blues", vmin=0, vmax=1)
    for (i, j), v in np.ndenumerate(cm.values):
        ax.text(j, i, f"{v:,}", ha="center", va="center", fontsize=8,
                color="white" if share.values[i, j] > 0.5 else INK)
    labels = [BAND_KO[c] for c in cm.columns]
    ax.set_xticks(range(3), labels)
    ax.set_yticks(range(3), labels)
    ax.set_xlabel("예측")
    ax.set_ylabel("실제")
    ax.grid(False)
    return ax


def forecast_week(pred: pd.DataFrame, ax=None, show_naive: bool = False):
    """The naive line is the actual shifted by one slot and hides the other two; off by default."""
    ax = ax or plt.subplots(figsize=(10, 3.2))[1]
    ax.plot(pred.index, pred["kwh"], color=INK, lw=1.0, label="실측")
    ax.plot(pred.index, pred["pred"], color=ACCENT, lw=1.0, label="HGB 예측")
    if show_naive:
        ax.plot(pred.index, pred["naive"], color=MUTED, lw=0.8, label="직전값")
    ax.set_ylabel("15분 kWh")
    ax.legend(ncol=3, loc="upper right")
    return ax


def error_by_hour(err: pd.DataFrame, ax=None):
    ax = ax or plt.subplots()[1]
    ax.plot(err.index, err["naive_mae"], color=MUTED, label="직전값 그대로")
    ax.plot(err.index, err["mae"], color=ACCENT, label="HGB")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("시작 시각")
    ax.set_ylabel("MAE (kWh)")
    ax.legend()
    return ax


def pf_by_load(table: pd.DataFrame, threshold: float = 0.9, ax=None):
    """Dots, not bars: the axis does not start at zero, so bar length would mislead."""
    ax = ax or plt.subplots()[1]
    x = range(len(table))
    colors = [WARN if v < threshold else ACCENT for v in table["pf"]]
    ax.vlines(x, threshold, table["pf"], color=GRID, lw=2)
    ax.scatter(x, table["pf"], color=colors, s=60, zorder=3)
    ax.axhline(threshold, color=MUTED, lw=0.8)
    ax.set_xticks(list(x), table.index)
    ax.set_ylim(0.65, 1.0)
    ax.set_xlabel("15분 사용량 구간 (kWh)")
    ax.set_ylabel("역률")
    return ax
