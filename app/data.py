"""Seeded synthetic card-transaction generator with fraud patterns, stealth fraud and concept drift.

SYNTHETIC DATA ONLY: no real customers or transactions. Fraud patterns (night activity, new device, foreign
country, high velocity, high amounts in some categories) overlap heavily with legitimate behaviour, 20% of fraud
is "stealth" (indistinguishable from legitimate rows), and after day `DRIFT_DAY` fraudsters change habits
(less night activity, fewer foreign transactions). Scores do not transfer to real fraud.

Author: Rayyan Anwar
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CATEGORIES = ["grocery", "fuel", "restaurant", "online_services", "electronics", "travel", "jewelry"]
CHANNELS = ["pos", "online", "atm"]
DRIFT_DAY = 65
CAT_AMOUNT = np.array([0.2, 0.3, 0.4, 0.0, 1.5, 1.8, 1.9])
P_CAT_LEGIT = np.array([0.30, 0.18, 0.22, 0.12, 0.08, 0.06, 0.04])
P_CAT_FRAUD = np.array([0.08, 0.05, 0.07, 0.20, 0.30, 0.15, 0.15])
P_CH_LEGIT = np.array([0.62, 0.30, 0.08])
P_CH_FRAUD = np.array([0.20, 0.65, 0.15])
_H = np.array([1, 1, 1, 1, 1, 2, 4, 6, 7, 7, 7, 8, 9, 8, 7, 7, 7, 8, 9, 9, 8, 6, 4, 2], float)
P_HOUR_LEGIT = _H / _H.sum()


def generate_transactions(n: int = 20000, days: int = 90, seed: int = 0, fraud_rate: float = 0.02,
                          start: str = "2025-01-01") -> pd.DataFrame:
    if n < 100 or days < 30:
        raise ValueError("need n >= 100 and days >= 30")
    if not 0.001 <= fraud_rate <= 0.3:
        raise ValueError("fraud_rate must be in [0.001, 0.3]")
    rng = np.random.default_rng(seed)
    fraud = rng.random(n) < fraud_rate
    stealth = fraud & (rng.random(n) < 0.20)
    f = fraud & ~stealth  # rows that actually follow the fraud pattern
    day = rng.integers(0, days, n)
    drifted = day >= DRIFT_DAY

    hour = rng.choice(24, n, p=P_HOUR_LEGIT)
    night_share = np.where(drifted, 0.20, 0.50)
    night = f & (rng.random(n) < night_share)
    hour = np.where(night, rng.integers(0, 6, n), hour)

    cat = np.where(f, rng.choice(7, n, p=P_CAT_FRAUD), rng.choice(7, n, p=P_CAT_LEGIT))
    chan = np.where(f, rng.choice(3, n, p=P_CH_FRAUD), rng.choice(3, n, p=P_CH_LEGIT))
    mu = np.where(f, np.log(90.0), np.log(35.0)) + CAT_AMOUNT[cat]
    amount = np.round(np.clip(np.exp(rng.normal(mu, np.where(f, 1.0, 0.9))), 1.0, None), 2)
    foreign = rng.random(n) < np.where(f, np.where(drifted, 0.10, 0.25), 0.03)
    new_device = rng.random(n) < np.where(f, 0.35, 0.04)
    velocity = 1 + rng.poisson(np.where(f, 1.5, 0.3))
    account_age = np.clip(rng.exponential(np.where(f, 250, 700), n), 1, 3650).astype(int)
    ts = pd.Timestamp(start) + pd.to_timedelta(day, unit="D") + pd.to_timedelta(hour, unit="h") \
        + pd.to_timedelta(rng.integers(0, 3600, n), unit="s")
    df = pd.DataFrame({
        "timestamp": ts, "customer_id": rng.integers(1, 1501, n), "amount": amount,
        "merchant_category": np.array(CATEGORIES)[cat], "channel": np.array(CHANNELS)[chan],
        "foreign": foreign.astype(int), "new_device": new_device.astype(int), "txn_count_1h": velocity,
        "account_age_days": account_age, "is_fraud": fraud.astype(int)})
    df = df.sort_values("timestamp").reset_index(drop=True)
    df.insert(0, "txn_id", [f"T{seed}-{i:06d}" for i in range(len(df))])
    return df


def feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Fixed-schema numeric features (one-hot columns are always present, so train/test align)."""
    ts = pd.to_datetime(df["timestamp"])
    x = pd.DataFrame({
        "amount": df["amount"].astype(float), "log_amount": np.log1p(df["amount"].astype(float)),
        "hour": ts.dt.hour, "is_night": (ts.dt.hour < 6).astype(int), "foreign": df["foreign"].astype(int),
        "new_device": df["new_device"].astype(int), "txn_count_1h": df["txn_count_1h"].astype(int),
        "account_age_days": df["account_age_days"].astype(int)})
    for c in CHANNELS:
        x[f"channel_{c}"] = (df["channel"] == c).astype(int)
    for c in CATEGORIES:
        x[f"cat_{c}"] = (df["merchant_category"] == c).astype(int)
    return x


def day_index(df: pd.DataFrame) -> np.ndarray:
    ts = pd.to_datetime(df["timestamp"])
    return (ts.dt.normalize() - pd.Timestamp("2025-01-01")).dt.days.to_numpy()
