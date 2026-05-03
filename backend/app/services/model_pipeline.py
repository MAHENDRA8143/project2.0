from __future__ import annotations

from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from app.core.config import FEATURES, MODEL_PATH


@dataclass
class ForecastResult:
    prediction_df: pd.DataFrame


@dataclass
class ForecastBundle:
    model: Ridge
    scaler_x: StandardScaler
    scaler_y: StandardScaler
    sequence_length: int
    feature_names: list[str]


class STPForecaster:
    def __init__(self, sequence_length: int = 72, horizon: int = 24) -> None:
        self.sequence_length = sequence_length
        self.horizon = horizon

    def _create_windows(self, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x_data = []
        y_data = []
        end = len(values) - self.sequence_length
        for i in range(max(0, end)):
            x_data.append(values[i : i + self.sequence_length])
            y_data.append(values[i + self.sequence_length])

        if not x_data:
            raise ValueError("Not enough data to create training windows.")

        return np.array(x_data), np.array(y_data)

    def _save_bundle(self, bundle: ForecastBundle) -> None:
        joblib.dump(bundle, MODEL_PATH)

    def _load_bundle(self) -> ForecastBundle:
        if not MODEL_PATH.exists():
            raise FileNotFoundError("Forecast bundle is missing.")
        bundle = joblib.load(MODEL_PATH)
        if isinstance(bundle, dict):
            return ForecastBundle(**bundle)
        return bundle

    def _forecast_hours(self, df: pd.DataFrame, hours: int) -> pd.DataFrame:
        bundle = self._load_bundle()

        current_window = df[FEATURES].tail(bundle.sequence_length).values.astype(np.float32)
        if current_window.shape[0] < bundle.sequence_length:
            raise ValueError("Insufficient historical data for prediction.")

        predictions: list[np.ndarray] = []
        for _ in range(hours):
            x_scaled = bundle.scaler_x.transform(current_window.reshape(1, -1))
            pred_scaled = bundle.model.predict(x_scaled)[0]
            pred = bundle.scaler_y.inverse_transform(pred_scaled.reshape(1, -1))[0]
            pred = np.clip(pred, 0.0, None)
            pred[2] = float(np.clip(pred[2], 5.5, 9.0))
            predictions.append(pred)
            current_window = np.vstack([current_window[1:], pred])

        pred_df = pd.DataFrame(predictions, columns=FEATURES)
        return pred_df

    def train(self, df: pd.DataFrame, epochs: int = 8) -> None:
        values = df[FEATURES].values.astype(np.float32)
        x_raw, y_raw = self._create_windows(values)

        scaler_x = StandardScaler()
        x_flat = x_raw.reshape(len(x_raw), -1)
        x_scaled = scaler_x.fit_transform(x_flat).reshape(x_raw.shape)

        scaler_y = StandardScaler()
        y_flat = y_raw.reshape(-1, len(FEATURES))
        y_scaled = scaler_y.fit_transform(y_flat).reshape(y_raw.shape)

        model = Ridge(alpha=1.0)
        model.fit(x_scaled.reshape(len(x_scaled), -1), y_scaled)

        bundle = ForecastBundle(
            model=model,
            scaler_x=scaler_x,
            scaler_y=scaler_y,
            sequence_length=self.sequence_length,
            feature_names=list(FEATURES),
        )
        self._save_bundle(bundle)

    def predict_next_day(self, df: pd.DataFrame) -> ForecastResult:
        if not MODEL_PATH.exists():
            self.train(df)

        pred_df = self._forecast_hours(df, self.horizon)
        return ForecastResult(prediction_df=pred_df)

    def predict_next_7_days(self, df: pd.DataFrame) -> ForecastResult:
        """Predict the next 7 days (168 hours) by chaining day-by-day predictions."""
        if not MODEL_PATH.exists():
            self.train(df)

        pred_df = self._forecast_hours(df, 24 * 7)
        return ForecastResult(prediction_df=pred_df)
