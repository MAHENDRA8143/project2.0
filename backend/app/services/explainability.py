from __future__ import annotations

from typing import Dict

import pandas as pd


def trend_explanation(history_df: pd.DataFrame, prediction_df: pd.DataFrame) -> str:
    recent = history_df.tail(12)
    pred = prediction_df.head(12)

    cod_trend = pred["COD"].mean() - recent["COD"].mean()
    do_trend = pred["DO"].mean() - recent["DO"].mean()
    bod_trend = pred["BOD"].mean() - recent["BOD"].mean()

    cues = []
    if cod_trend > 1.0:
        cues.append("rising COD")
    if do_trend < -0.4:
        cues.append("falling DO")
    if bod_trend > 1.0:
        cues.append("increasing BOD")

    if not cues:
        return "Prediction is influenced by stable recent pollutant and oxygen trends."

    joined = " and ".join(cues)
    return f"Prediction influenced by {joined} trends."


def feature_delta_summary(history_df: pd.DataFrame, prediction_df: pd.DataFrame) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for col in ["BOD", "COD", "pH", "DO", "NH3_N", "TP"]:
        result[col] = round(float(prediction_df[col].mean() - history_df.tail(24)[col].mean()), 3)
    return result
