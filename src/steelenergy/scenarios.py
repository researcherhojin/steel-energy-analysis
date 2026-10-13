from dataclasses import dataclass

import numpy as np
import pandas as pd

from steelenergy import config
from steelenergy.units import KW_PER_KWH_SLOT, power_factor


def _monthly_bill(df: pd.DataFrame, kwh: pd.Series, kvarh: pd.Series, tariff: dict) -> pd.DataFrame:
    """Energy + demand + PF surcharge per month under the assumed tariff."""
    rate = df["load_type"].astype(str).map(tariff["energy_rate_per_kwh"])
    month = df["month"]
    energy = (kwh * rate).groupby(month).sum()
    demand = (kwh.groupby(month).max() * KW_PER_KWH_SLOT) * tariff["demand_rate_per_kw_month"]
    pf = pd.Series(power_factor(kwh.groupby(month).sum(), kvarh.groupby(month).sum()),
                   index=energy.index)
    shortfall_pct = ((tariff["pf_threshold"] - pf).clip(lower=0) * 100)
    surcharge = energy * shortfall_pct * tariff["pf_penalty_rate_per_pct"]
    return pd.DataFrame({"energy": energy, "demand": demand, "pf": pf, "pf_surcharge": surcharge,
                         "total": energy + demand + surcharge})


def baseline_bill(df: pd.DataFrame, tariff=config.TARIFF_ASSUMPTIONS) -> pd.DataFrame:
    return _monthly_bill(df, df["kwh"], df["lag_kvarh"], tariff)


def correct_power_factor(df: pd.DataFrame, target=config.PF_TARGET) -> pd.Series:
    """Lagging kVarh after compensation: each slot below target is brought up to it. kWh unchanged."""
    allowed = df["kwh"] * np.tan(np.arccos(target))
    return np.minimum(df["lag_kvarh"], allowed)


def pf_scenario(df: pd.DataFrame, target=config.PF_TARGET, tariff=config.TARIFF_ASSUMPTIONS) -> dict:
    kvarh = correct_power_factor(df, target)
    before, after = baseline_bill(df, tariff), _monthly_bill(df, df["kwh"], kvarh, tariff)
    kva_before = np.sqrt(df["kwh"] ** 2 + df["lag_kvarh"] ** 2)
    kva_after = np.sqrt(df["kwh"] ** 2 + kvarh**2)
    return {
        "target_pf": target,
        "kvarh_before": float(df["lag_kvarh"].sum()),
        "kvarh_after": float(kvarh.sum()),
        "peak_kva_before": float(kva_before.max() * KW_PER_KWH_SLOT),
        "peak_kva_after": float(kva_after.max() * KW_PER_KWH_SLOT),
        "annual_pf_before": float(power_factor(df["kwh"].sum(), df["lag_kvarh"].sum())),
        "annual_pf_after": float(power_factor(df["kwh"].sum(), kvarh.sum())),
        "surcharge_before": float(before["pf_surcharge"].sum()),
        "surcharge_after": float(after["pf_surcharge"].sum()),
        "kwh_change": 0.0,
    }


def shift_peak_load(df: pd.DataFrame, fraction: float) -> tuple[pd.Series, pd.Series]:
    """Move `fraction` of each day's Maximum_Load energy evenly onto that day's Light_Load slots.

    Lagging kVarh moves with the energy it belongs to (the source slot's kVarh/kWh ratio),
    so the receiving slots do not inherit their own, much worse, idle-time ratio.
    Returns the shifted (kWh, lagging kVarh). Days without Light_Load slots are left as is.
    """
    day = df["operating_day"]
    is_max = df["load_type"] == "Maximum_Load"
    is_light = df["load_type"] == "Light_Load"
    light_slots = is_light.groupby(day).transform("sum")
    movable = is_max & (light_slots > 0)
    receiving = is_light & (light_slots > 0)

    def move(series: pd.Series) -> pd.Series:
        out_ = series.where(movable, 0) * fraction
        per_day = out_.groupby(day).transform("sum")
        return series - out_ + (per_day / light_slots.replace(0, np.nan)).where(receiving, 0)

    return move(df["kwh"]), move(df["lag_kvarh"])


def shift_scenario(df: pd.DataFrame, fraction: float,
                   tariff=config.TARIFF_ASSUMPTIONS) -> dict:
    kwh, kvarh = shift_peak_load(df, fraction)
    before, after = baseline_bill(df, tariff), _monthly_bill(df, kwh, kvarh, tariff)
    return {
        "fraction": fraction,
        "kwh_before": float(df["kwh"].sum()),
        "kwh_after": float(kwh.sum()),
        "peak_kw_before": float(df["kwh"].max() * KW_PER_KWH_SLOT),
        "peak_kw_after": float(kwh.max() * KW_PER_KWH_SLOT),
        "mean_monthly_peak_kw_before": float(df["kwh"].groupby(df["month"]).max().mean() * KW_PER_KWH_SLOT),
        "mean_monthly_peak_kw_after": float(kwh.groupby(df["month"]).max().mean() * KW_PER_KWH_SLOT),
        "energy_cost_before": float(before["energy"].sum()),
        "energy_cost_after": float(after["energy"].sum()),
        "demand_cost_before": float(before["demand"].sum()),
        "demand_cost_after": float(after["demand"].sum()),
        "surcharge_before": float(before["pf_surcharge"].sum()),
        "surcharge_after": float(after["pf_surcharge"].sum()),
        "total_cost_before": float(before["total"].sum()),
        "total_cost_after": float(after["total"].sum()),
    }


def surcharge_profile(bill: pd.DataFrame, months=(8, 9, 10)) -> dict:
    """How many months carry a power-factor surcharge, and the share falling in `months`."""
    total = bill["pf_surcharge"].sum()
    return {
        "months_with_surcharge": int((bill["pf_surcharge"] > 0).sum()),
        "focus_months": list(months),
        "focus_share": float(bill.loc[list(months), "pf_surcharge"].sum() / total) if total else 0.0,
    }


def pf_grid(df, targets=(0.90, 0.92, 0.94, 0.95, 0.96, 0.98)) -> pd.DataFrame:
    return pd.DataFrame([pf_scenario(df, t) for t in targets])


def shift_grid(df, fractions=(0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30)) -> pd.DataFrame:
    return pd.DataFrame([shift_scenario(df, f) for f in fractions])


def first_demand_increase(shift: pd.DataFrame) -> float | None:
    """Smallest shift fraction at which the demand charge rises instead of falling."""
    rising = shift.loc[shift["demand_cost_after"] > shift["demand_cost_before"], "fraction"]
    return float(rising.iloc[0]) if len(rising) else None


@dataclass
class ScenarioResults:
    pf_grid: pd.DataFrame
    pf_default: dict
    shift_grid: pd.DataFrame
    first_demand_increase: float | None
    bill: pd.DataFrame
    surcharge: dict


def run(df: pd.DataFrame) -> ScenarioResults:
    pf = pf_grid(df)
    shift = shift_grid(df)
    bill = baseline_bill(df)
    return ScenarioResults(
        pf_grid=pf,
        pf_default=pf.set_index("target_pf").loc[config.PF_TARGET].to_dict(),
        shift_grid=shift,
        first_demand_increase=first_demand_increase(shift),
        bill=bill,
        surcharge=surcharge_profile(bill),
    )
