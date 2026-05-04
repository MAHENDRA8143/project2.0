from __future__ import annotations

from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

from app.core.config import FEATURES, MODEL_PATH


@dataclass
class ForecastResult:
    prediction_df: pd.DataFrame


@dataclass
class ForecastBundle:
    models: dict  # One model per feature
    scaler_x: StandardScaler
    scaler_y: StandardScaler
    sequence_length: int
    feature_names: list[str]
    feature_scalers: dict  # Per-feature scalers


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

    def _add_temporal_features(self, x_data: np.ndarray) -> np.ndarray:
        """Add temporal and statistical features from the window"""
        n_samples, seq_len, n_features = x_data.shape
        features = []
        
        for i in range(n_samples):
            window = x_data[i]
            feat_row = []
            
            # Raw flattened sequence
            feat_row.extend(window.flatten())
            
            # Statistical features per feature
            for feat_idx in range(n_features):
                feat_vals = window[:, feat_idx]
                feat_row.extend([
                    np.mean(feat_vals),           # Mean
                    np.std(feat_vals),            # Std dev
                    np.min(feat_vals),            # Min
                    np.max(feat_vals),            # Max
                    np.ptp(feat_vals),            # Range
                    feat_vals[-1],                # Last value
                    feat_vals[0],                 # First value
                    np.median(feat_vals),         # Median
                ])
            
            features.append(feat_row)
        
        return np.array(features, dtype=np.float32)

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
            # Add temporal features
            window_expanded = current_window.reshape(1, bundle.sequence_length, len(FEATURES))
            x_features = self._add_temporal_features(window_expanded)
            
            # Predict each feature
            pred = np.zeros(len(FEATURES), dtype=np.float32)
            for feat_idx, feature_name in enumerate(FEATURES):
                pred[feat_idx] = bundle.models[feature_name].predict(x_features)[0]
            
            # Apply constraints
            pred = np.clip(pred, 0.0, None)
            pred[2] = float(np.clip(pred[2], 5.5, 9.0))  # pH constraint
            
            predictions.append(pred)
            current_window = np.vstack([current_window[1:], pred])

        pred_df = pd.DataFrame(predictions, columns=FEATURES)
        return pred_df

    def train(self, df: pd.DataFrame, epochs: int = 8) -> None:
        values = df[FEATURES].values.astype(np.float32)
        x_raw, y_raw = self._create_windows(values)

        # Add temporal and statistical features
        print("Extracting temporal features...")
        x_features = self._add_temporal_features(x_raw)

        # Scale features
        scaler_x = StandardScaler()
        x_scaled = scaler_x.fit_transform(x_features)

        # Train a separate model for each feature
        models = {}
        feature_scalers = {}
        
        for feat_idx, feature_name in enumerate(FEATURES):
            print(f"\n[TRAINING] {feature_name}...")
            y = y_raw[:, feat_idx].astype(np.float32)
            
            # Scale target
            scaler_y = StandardScaler()
            y_scaled = scaler_y.fit_transform(y.reshape(-1, 1)).ravel()
            feature_scalers[feature_name] = scaler_y
            
            # Optimized hyperparameters for better performance
            print(f"  -> Training with HistGradientBoosting...")
            model = HistGradientBoostingRegressor(
                loss='squared_error',
                learning_rate=0.10,
                max_iter=120,               # Good balance
                max_depth=6,
                max_bins=255,
                min_samples_leaf=6,
                random_state=42,
                verbose=0
            )
            
            try:
                model.fit(x_scaled, y_scaled)
                train_r2 = model.score(x_scaled, y_scaled)
                print(f"  -> Training R2: {train_r2:.6f}")
                models[feature_name] = model
            except KeyboardInterrupt:
                print(f"  [TIMEOUT] Using lightweight fallback...")
                model = HistGradientBoostingRegressor(
                    loss='squared_error',
                    learning_rate=0.15,
                    max_iter=30,
                    max_depth=3,
                    min_samples_leaf=20,
                    random_state=42,
                    verbose=0
                )
                model.fit(x_scaled, y_scaled)
                train_r2 = model.score(x_scaled, y_scaled)
                print(f"  -> Fallback Training R2: {train_r2:.6f}")
                models[feature_name] = model

        bundle = ForecastBundle(
            models=models,
            scaler_x=scaler_x,
            scaler_y=None,
            sequence_length=self.sequence_length,
            feature_names=list(FEATURES),
            feature_scalers=feature_scalers,
        )
        self._save_bundle(bundle)
        print("\n[COMPLETE] Model training finished successfully!")

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
