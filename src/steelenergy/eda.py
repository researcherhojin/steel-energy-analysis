from dataclasses import dataclass

import pandas as pd

from steelenergy import config
from steelenergy.units import KW_PER_KWH_SLOT, power_factor


def daily_totals(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("operating_day")
    out = pd.DataFrame({
        "kwh": g["kwh"].sum(),
        "co2_t": g["co2_t"].sum(),
        "lag_kvarh": g["lag_kvarh"].sum(),
        "peak_kw": g["kwh"].max() * KW_PER_KWH_SLOT,
    })
    out["pf"] = power_factor(out["kwh"], out["lag_kvarh"])
    out["dow"] = out.index.dayofweek
    out["is_weekend"] = out["dow"] >= 5
    out["month"] = out.index.month
    by_type = df.pivot_table(index="operating_day", columns="load_type", values="kwh",
                             aggfunc="sum", observed=False)
    return out.join(by_type.add_prefix("kwh_"))


def hour_dow_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Mean kWh per 15-min slot, by hour of day (rows) and weekday (columns)."""
    return df.pivot_table(index="hour", columns="dow", values="kwh", aggfunc="mean")


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("month")
    out = pd.DataFrame({
        "kwh": g["kwh"].sum(),
        "co2_t": g["co2_t"].sum(),
        "lag_kvarh": g["lag_kvarh"].sum(),
        "peak_kw": g["kwh"].max() * KW_PER_KWH_SLOT,
        "days": g["operating_day"].nunique(),
    })
    out["kwh_per_day"] = out["kwh"] / out["days"]
    out["pf"] = power_factor(out["kwh"], out["lag_kvarh"])
    return out


def load_type_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("load_type", observed=False)
    out = pd.DataFrame({
        "slots": g.size(),
        "kwh": g["kwh"].sum(),
        "mean_kwh": g["kwh"].mean(),
        "median_kwh": g["kwh"].median(),
        "lag_kvarh": g["lag_kvarh"].sum(),
    })
    out["slot_share"] = out["slots"] / out["slots"].sum()
    out["kwh_share"] = out["kwh"] / out["kwh"].sum()
    out["pf"] = power_factor(out["kwh"], out["lag_kvarh"])
    return out


def concentration(df: pd.DataFrame, hours=(8, 18)) -> dict:
    """Share of annual kWh used on weekdays between the given hours (interval start)."""
    mask = (df["is_weekend"] == 0) & df["hour"].between(hours[0], hours[1] - 1)
    return {
        "hours": list(hours),
        "slot_share": float(mask.mean()),
        "kwh_share": float(df.loc[mask, "kwh"].sum() / df["kwh"].sum()),
    }


def idle_share(df: pd.DataFrame, threshold_kwh: float = 5.0) -> dict:
    """How often the plant sits near base load, and what that base load costs over a year."""
    idle = df["kwh"] < threshold_kwh
    return {
        "threshold_kwh": threshold_kwh,
        "slot_share": float(idle.mean()),
        "kwh": float(df.loc[idle, "kwh"].sum()),
        "base_kw": float(df.loc[idle, "kwh"].median() * KW_PER_KWH_SLOT),
    }


def pf_by_load_bin(df: pd.DataFrame, bins=(0, 5, 20, 40, 60, 80, 200)) -> pd.DataFrame:
    cut = pd.cut(df["kwh"], bins=list(bins), right=False)
    g = df.groupby(cut, observed=True)
    out = pd.DataFrame({"slots": g.size(), "kwh": g["kwh"].sum(), "lag_kvarh": g["lag_kvarh"].sum()})
    out["pf"] = power_factor(out["kwh"], out["lag_kvarh"])
    out.index = [f"{int(i.left)}–{int(i.right)}" for i in out.index]
    return out


def correlations(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["kwh", "lag_kvarh", "lead_kvarh", "co2_t", "lag_pf", "lead_pf", "hour", "is_weekend"]
    return df[cols].corr(method="spearman")


def tou_schedule(df: pd.DataFrame) -> pd.DataFrame:
    """Most common Load_Type per weekday hour, separately for the two seasons."""
    wd = df[df["is_weekend"] == 0]
    season = wd["is_winter"].map({0: "summer", 1: "winter"})
    return wd.groupby([season, wd["hour"]])["load_type"].agg(
        lambda s: s.mode().iloc[0]).unstack(0).astype(str)


def profile_cube(df: pd.DataFrame) -> pd.DataFrame:
    """kWh sum and slot count by month × weekday × hour × load type, for client-side filtering."""
    g = df.groupby(["month", "dow", "hour", "load_type"], observed=True)["kwh"]
    return g.agg(["sum", "count"]).reset_index()


def night_load(df: pd.DataFrame, start: int = 21, end: int = 8) -> pd.Series:
    """Mean 15-min kWh between `start` and `end` o'clock (interval start), by month."""
    night = df[(df["hour"] >= start) | (df["hour"] < end)]
    return night.groupby("month")["kwh"].mean().rename("night_mean_kwh")


def regular_weekday_median(daily: pd.DataFrame, holidays=config.KR_HOLIDAYS_2018) -> float:
    """Median daily kWh over weekdays that are not public holidays: the 'normal day' reference."""
    hol = pd.to_datetime(list(holidays))
    return float(daily.loc[~daily["is_weekend"] & ~daily.index.isin(hol), "kwh"].median())


def holiday_operation(daily: pd.DataFrame, holidays=config.KR_HOLIDAYS_2018) -> pd.DataFrame:
    """Each public holiday's consumption against the median non-holiday weekday."""
    names = pd.Series(holidays, name="holiday")
    names.index = pd.to_datetime(names.index)
    ref = regular_weekday_median(daily, holidays)
    out = daily.loc[names.index, ["kwh", "dow", "is_weekend"]].join(names)
    out["ratio_to_weekday"] = out["kwh"] / ref
    # A holiday on a weekend says nothing about whether the plant chose to stop.
    out["shutdown"] = ~out["is_weekend"] & (out["ratio_to_weekday"] < config.SHUTDOWN_RATIO)
    return out


def shutdown_runs(shutdowns: pd.DataFrame) -> pd.DataFrame:
    """Group shutdown days into runs of consecutive calendar days: start, end, days."""
    days = shutdowns.index.to_series()
    run = (days.diff() != pd.Timedelta(days=1)).cumsum()
    g = days.groupby(run.values)
    return pd.DataFrame({"start": g.min().values, "end": g.max().values, "days": g.size().values})


def weekday_shutdowns(daily: pd.DataFrame, holidays=config.KR_HOLIDAYS_2018) -> pd.DataFrame:
    """Non-holiday weekdays that ran at shutdown level (below SHUTDOWN_RATIO of a normal weekday)."""
    hol = pd.to_datetime(list(holidays))
    regular = daily[~daily["is_weekend"] & ~daily.index.isin(hol)]
    ratio = regular["kwh"] / regular_weekday_median(daily, holidays)
    out = regular.loc[ratio < config.SHUTDOWN_RATIO, ["kwh", "dow"]].copy()
    out["ratio_to_weekday"] = ratio[out.index]
    return out


def headline(df: pd.DataFrame, daily: pd.DataFrame) -> dict:
    """Year-level figures: totals, power factor, peak and typical daily use by day type."""
    return {
        "annual_kwh": df["kwh"].sum(),
        "annual_co2_t": df["co2_t"].sum(),
        "annual_pf": float(power_factor(df["kwh"].sum(), df["lag_kvarh"].sum())),
        "peak_kw": df["kwh"].max() * KW_PER_KWH_SLOT,
        "mean_daily_kwh": daily["kwh"].mean(),
        "weekday_mean_kwh": daily.loc[~daily["is_weekend"], "kwh"].mean(),
        "saturday_mean_kwh": daily.loc[daily["dow"] == 5, "kwh"].mean(),
        "sunday_mean_kwh": daily.loc[daily["dow"] == 6, "kwh"].mean(),
    }


def kwh_correlations(df: pd.DataFrame) -> pd.Series:
    """Spearman correlation of every column in `correlations` with kWh."""
    return correlations(df).loc["kwh"]


def holiday_counts(holidays: pd.DataFrame) -> dict:
    return {
        "holidays": len(holidays),
        "weekday_holidays": int((~holidays["is_weekend"]).sum()),
        "weekend_holidays": int(holidays["is_weekend"].sum()),
        "holiday_shutdowns": int(holidays["shutdown"].sum()),
    }


@dataclass
class EdaResults:
    daily: pd.DataFrame
    headline: dict
    concentration: dict
    idle: dict
    monthly: pd.DataFrame
    night_load: pd.Series
    profile: pd.DataFrame
    load_types: pd.DataFrame
    pf_by_load: pd.DataFrame
    tou_schedule: pd.DataFrame
    kwh_correlations: pd.Series
    regular_weekday_median: float
    holidays: pd.DataFrame
    holiday_counts: dict
    shutdowns: pd.DataFrame
    shutdown_runs: pd.DataFrame


def run(df: pd.DataFrame, daily: pd.DataFrame) -> EdaResults:
    holidays = holiday_operation(daily)
    shutdowns = weekday_shutdowns(daily)
    return EdaResults(
        daily=daily,
        headline=headline(df, daily),
        concentration=concentration(df),
        idle=idle_share(df),
        monthly=monthly_summary(df),
        night_load=night_load(df),
        profile=profile_cube(df),
        load_types=load_type_summary(df),
        pf_by_load=pf_by_load_bin(df),
        tou_schedule=tou_schedule(df),
        kwh_correlations=kwh_correlations(df),
        regular_weekday_median=regular_weekday_median(daily),
        holidays=holidays,
        holiday_counts=holiday_counts(holidays),
        shutdowns=shutdowns,
        shutdown_runs=shutdown_runs(shutdowns),
    )
