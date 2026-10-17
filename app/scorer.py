"""Risk scorer trained on synthetic data (logistic regression) with fixed risk bands.

Scores are relative and uncalibrated. Author: Rayyan Anwar
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .data import day_index, feature_frame, generate_transactions


class Scorer:
    def __init__(self, seed: int = 0, n: int = 30000):
        df = generate_transactions(n, 90, seed)
        d = day_index(df)
        tr, va = df[d < 50], df[(d >= 50) & (d < 70)]
        self.model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed))
        self.model.fit(feature_frame(tr), tr["is_fraud"])
        sv = self.model.predict_proba(feature_frame(va))[:, 1]
        self.high, self.medium = float(np.quantile(sv, 0.99)), float(np.quantile(sv, 0.95))

    def score(self, df: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(feature_frame(df))[:, 1]

    def band(self, s: float) -> str:
        return "high" if s >= self.high else "medium" if s >= self.medium else "low"


@lru_cache(maxsize=1)
def get_scorer() -> Scorer:
    return Scorer()
