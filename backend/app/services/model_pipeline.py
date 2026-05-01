from __future__ import annotations

from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import load_model

from app.core.config import FEATURES, MODEL_PATH, SCALER_X_PATH, SCALER_Y_PATH
from app.models.cnn_lstm_attention import build_cnn_lstm_attention_model


@dataclass
class ForecastResult:
    prediction_df: pd.DataFrame


class STPForecaster:
    def __init__(self, sequence_length: int = 72, horizon: int = 24) -> None:
        self.sequence_length = sequence_length
        self.horizon = horizon

    def _create_windows(self, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x_data = []
        y_data = []
        end = len(values) - self.sequence_length - self.horizon + 1
        for i in range(max(0, end)):
            x_data.append(values[i : i + self.sequence_length])
            y_data.append(values[i + self.sequence_length : i + self.sequence_length + self.horizon])

        if not x_data:
            raise ValueError("Not enough data to create training windows.")

        return np.array(x_data), np.array(y_data)

    def train(self, df: pd.DataFrame, epochs: int = 8) -> None:
        values = df[FEATURES].values.astype(np.float32)
        x_raw, y_raw = self._create_windows(values)

        scaler_x = StandardScaler()
        x_flat = x_raw.reshape(-1, len(FEATURES))
        x_scaled = scaler_x.fit_transform(x_flat).reshape(x_raw.shape)

        scaler_y = StandardScaler()
        y_flat = y_raw.reshape(-1, len(FEATURES))
        y_scaled = scaler_y.fit_transform(y_flat).reshape(y_raw.shape)

        model = build_cnn_lstm_attention_model(self.sequence_length, len(FEATURES), self.horizon)
        model.fit(
            x_scaled,
            y_scaled,
            validation_split=0.15,
            epochs=epochs,
            batch_size=16,
            verbose=0,
        )

        model.save(MODEL_PATH)
        joblib.dump(scaler_x, SCALER_X_PATH)
        joblib.dump(scaler_y, SCALER_Y_PATH)

    def predict_next_day(self, df: pd.DataFrame) -> ForecastResult:
        if not MODEL_PATH.exists() or not SCALER_X_PATH.exists() or not SCALER_Y_PATH.exists():
            self.train(df)

        model = load_model(MODEL_PATH)
        scaler_x: StandardScaler = joblib.load(SCALER_X_PATH)
        scaler_y: StandardScaler = joblib.load(SCALER_Y_PATH)

        input_seq = df[FEATURES].tail(self.sequence_length).values.astype(np.float32)
        if input_seq.shape[0] < self.sequence_length:
            raise ValueError("Insufficient historical data for prediction.")

        x_scaled = scaler_x.transform(input_seq).reshape(1, self.sequence_length, len(FEATURES))
        pred_scaled = model.predict(x_scaled, verbose=0)[0]

        pred = scaler_y.inverse_transform(pred_scaled)
        pred_df = pd.DataFrame(pred, columns=FEATURES)
        pred_df = pred_df.clip(lower=0.0)

        # Bound pH range to realistic treatment process values.
        pred_df["pH"] = pred_df["pH"].clip(lower=5.5, upper=9.0)
        return ForecastResult(prediction_df=pred_df)

    def predict_next_7_days(self, df: pd.DataFrame) -> ForecastResult:
        """Predict the next 7 days (168 hours) by chaining day-by-day predictions."""
        if not MODEL_PATH.exists() or not SCALER_X_PATH.exists() or not SCALER_Y_PATH.exists():
            self.train(df)

        model = load_model(MODEL_PATH)
        scaler_x: StandardScaler = joblib.load(SCALER_X_PATH)
        scaler_y: StandardScaler = joblib.load(SCALER_Y_PATH)

        all_predictions = []
        current_input_df = df[FEATURES].tail(self.sequence_length).copy()

        for day in range(7):
            input_seq = current_input_df.tail(self.sequence_length).values.astype(np.float32)
            if input_seq.shape[0] < self.sequence_length:
                raise ValueError("Insufficient historical data for prediction.")

            x_scaled = scaler_x.transform(input_seq).reshape(1, self.sequence_length, len(FEATURES))
            pred_scaled = model.predict(x_scaled, verbose=0)[0]

            pred = scaler_y.inverse_transform(pred_scaled)
            pred_df = pd.DataFrame(pred, columns=FEATURES)
            pred_df = pred_df.clip(lower=0.0)
            pred_df["pH"] = pred_df["pH"].clip(lower=5.5, upper=9.0)

            all_predictions.append(pred_df)

            current_input_df = pd.concat([current_input_df.iloc[24:], pred_df], ignore_index=True)

        result_df = pd.concat(all_predictions, ignore_index=True)
        return ForecastResult(prediction_df=result_df)

    def predict_next_7_days(self, df: pd.DataFrame) -> ForecastResult:
        """Predict the next 7 days (168 hours) by chaining day-by-day predictions."""
        if not MODEL_PATH.exists() or not SCALER_X_PATH.exists() or not SCALER_Y_PATH.exists():
            self.train(df)

        model = load_model(MODEL_PATH)
        scaler_x: StandardScaler = joblib.load(SCALER_X_PATH)
        scaler_y: StandardScaler = joblib.load(SCALER_Y_PATH)

        all_predictions = []
        current_input_df = df[FEATURES].tail(self.sequence_length).copy()

        for day in range(7):
            input_seq = current_input_df.tail(self.sequence_length).values.astype(np.float32)
            if input_seq.shape[0] < self.sequence_length:
                raise ValueError("Insufficient historical data for prediction.")

            x_scaled = scaler_x.transform(input_seq).reshape(1, self.sequence_length, len(FEATURES))
            pred_scaled = model.predict(x_scaled, verbose=0)[0]

            pred = scaler_y.inverse_transform(pred_scaled)
            pred_df = pd.DataFrame(pred, columns=FEATURES)
            pred_df = pred_df.clip(lower=0.0)
            pred_df["pH"] = pred_df["pH"].clip(lower=5.5, upper=9.0)

            all_predictions.append(pred_df)

            # Use last 24 predictions as part of next input sequence
            current_input_df = pd.concat([current_input_df.iloc[24:], pred_df], ignore_index=True)

        result_df = pd.concat(all_predictions, ignore_index=True)
        return ForecastResult(prediction_df=result_df)
