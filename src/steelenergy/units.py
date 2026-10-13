"""Electrical unit helpers shared by the analysis modules."""
import numpy as np

from steelenergy import config

KW_PER_KWH_SLOT = 60 / config.INTERVAL_MIN  # 15-min kWh → average kW over the slot


def power_factor(kwh, kvarh):
    """Energy-weighted displacement power factor (0–1)."""
    s = np.sqrt(np.square(kwh) + np.square(kvarh))
    return np.where(s > 0, kwh / s, np.nan)
