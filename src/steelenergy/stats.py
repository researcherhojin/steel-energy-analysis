from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from steelenergy import config


@dataclass(frozen=True)
class TestResult:
    question: str
    unit: str
    n: int
    test: str
    statistic: float
    p_value: float
    effect_name: str
    effect: float
    ci_low: float
    ci_high: float
    p_holm: float = np.nan


def cliffs_delta(x, y) -> float:
    x, y = np.asarray(x), np.asarray(y)
    gt = (x[:, None] > y[None, :]).sum()
    lt = (x[:, None] < y[None, :]).sum()
    return (gt - lt) / (x.size * y.size)


def week_bootstrap(daily: pd.DataFrame, stat, n_boot=config.BOOTSTRAP_DRAWS,
                   seed=config.SEED) -> tuple[float, float]:
    """95% CI by resampling whole ISO weeks, which keeps the within-week dependence intact."""
    rng = np.random.default_rng(seed)
    week = daily.index.to_period("W-SUN")
    groups = [daily[week == w] for w in week.unique()]
    draws = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        draws[b] = stat(pd.concat([groups[i] for i in pick]))
    return tuple(np.quantile(draws, [0.025, 0.975]))


def weekday_vs_weekend(daily: pd.DataFrame) -> TestResult:
    wd, we = daily.loc[~daily["is_weekend"], "kwh"], daily.loc[daily["is_weekend"], "kwh"]
    u = stats.mannwhitneyu(wd, we, alternative="two-sided")
    ci = week_bootstrap(daily, lambda d: cliffs_delta(d.loc[~d["is_weekend"], "kwh"],
                                                      d.loc[d["is_weekend"], "kwh"]))
    return TestResult("평일과 주말의 일 소비량 차이", "operating day", len(daily),
                      "Mann–Whitney U", float(u.statistic), float(u.pvalue),
                      "Cliff's δ", float(cliffs_delta(wd, we)), *map(float, ci))


def saturday_vs_sunday(daily: pd.DataFrame) -> TestResult:
    sat, sun = daily.loc[daily["dow"] == 5, "kwh"], daily.loc[daily["dow"] == 6, "kwh"]
    w = stats.wilcoxon(sat.values, sun.values[: len(sat)])
    weekend = daily[daily["is_weekend"]]
    ci = week_bootstrap(weekend, lambda d: cliffs_delta(d.loc[d["dow"] == 5, "kwh"],
                                                        d.loc[d["dow"] == 6, "kwh"]))
    return TestResult("토요일과 일요일의 일 소비량 차이(같은 주끼리 대응)", "weekend pair",
                      len(sat), "Wilcoxon signed-rank", float(w.statistic), float(w.pvalue),
                      "Cliff's δ", float(cliffs_delta(sat, sun)), *map(float, ci))


def load_type_levels(df: pd.DataFrame) -> TestResult:
    """Friedman on each day's mean kWh per load type (the days are the blocks)."""
    per_day = df.pivot_table(index="operating_day", columns="load_type", values="kwh",
                             aggfunc="mean", observed=False).dropna()
    f = stats.friedmanchisquare(*[per_day[c] for c in per_day.columns])
    n, k = per_day.shape
    w = f.statistic / (n * (k - 1))

    def kendall_w(d):
        r = d.rank(axis=1)
        s = ((r.sum() - r.sum().mean()) ** 2).sum()
        return 12 * s / (len(d) ** 2 * (k**3 - k))

    ci = week_bootstrap(per_day, kendall_w)
    return TestResult("부하 유형(Light/Medium/Maximum)별 평균 소비 수준", "operating day", n,
                      "Friedman χ²", float(f.statistic), float(f.pvalue),
                      "Kendall's W", float(w), *map(float, ci))


def month_effect(daily: pd.DataFrame) -> TestResult:
    """Kruskal–Wallis across months, weekdays only so the weekend mix does not drive it."""
    wd = daily[~daily["is_weekend"]]
    groups = [g["kwh"].values for _, g in wd.groupby("month")]
    h = stats.kruskal(*groups)
    n, k = len(wd), len(groups)
    eps2 = (h.statistic - k + 1) / (n - k)

    def eps(d):
        gs = [g["kwh"].values for _, g in d.groupby("month")]
        hh = stats.kruskal(*gs).statistic
        return (hh - len(gs) + 1) / (len(d) - len(gs))

    ci = week_bootstrap(wd, eps)
    return TestResult("월별 평일 일 소비량 차이(계절성)", "weekday", n, "Kruskal–Wallis H",
                      float(h.statistic), float(h.pvalue), "ε²", float(eps2), *map(float, ci))


def holm(p_values) -> np.ndarray:
    """Holm–Bonferroni adjusted p-values (step-down, monotone, capped at 1).

    Equivalent to statsmodels' multipletests(method="holm")[1]; implemented here so the
    project does not need statsmodels, which ships no wheels for Windows on ARM64.
    """
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p, kind="mergesort")
    m = len(p)
    stepped = np.maximum.accumulate((m - np.arange(m)) * p[order])
    adjusted = np.empty(m)
    adjusted[order] = np.minimum(stepped, 1.0)
    return adjusted


def run_tests(df: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Effect sizes with week-block bootstrap CIs, plus rank-test p-values.

    Daily totals are still autocorrelated (lag-1 r ≈ 0.4), so the p-values assume more
    independence than the data has. Conclusions rest on the effect sizes and whether their
    block-bootstrap CI excludes 'no effect'; the p-values are kept for reference only.
    """
    results = [weekday_vs_weekend(daily), saturday_vs_sunday(daily),
               load_type_levels(df), month_effect(daily)]
    table = pd.DataFrame([r.__dict__ for r in results])
    table["p_holm"] = holm(table["p_value"])
    table["ci_excludes_null"] = table["ci_low"] > 0
    return table


def emission_factor(daily: pd.DataFrame) -> dict:
    """tCO2 per MWh from daily sums. Interval values are rounded to 0.01 t, so per-slot ratios are useless."""
    x, y = daily["kwh"].values / 1000, daily["co2_t"].values
    slope = float((x @ y) / (x @ x))
    resid = y - slope * x
    r2 = 1 - resid @ resid / ((y - y.mean()) @ (y - y.mean()))
    return {"t_per_mwh": slope, "ratio_of_sums": float(y.sum() / x.sum()), "r2_daily": float(r2)}


def co2_zero_share(df: pd.DataFrame) -> float:
    """Share of 15-min records whose CO₂ rounds to 0.00 t."""
    return float((df["co2_t"] == 0).mean())


@dataclass
class StatsResults:
    tests: pd.DataFrame
    emission: dict
    co2_zero_share: float


def run(df: pd.DataFrame, daily: pd.DataFrame) -> StatsResults:
    return StatsResults(tests=run_tests(df, daily), emission=emission_factor(daily),
                        co2_zero_share=co2_zero_share(df))
