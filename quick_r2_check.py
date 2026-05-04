#!/usr/bin/env python3
"""Quick R² check script"""
from pathlib import Path
import sys
import os

ROOT = Path(__file__).resolve().parents[0]
backend_path = str(ROOT / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

os.chdir(ROOT)

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score
from app.core.config import FEATURES, MODEL_PATH
from app.services.data_store import ensure_dataset
from app.services.model_pipeline import STPForecaster

# Load data
print("="*60)
df = ensure_dataset(days=90)
values = df[FEATURES].values.astype(np.float32)

# Load model
forecaster = STPForecaster(sequence_length=72, horizon=24)
bundle = forecaster._load_bundle()

# Create windows
x_data = []
y_data = []
sequence_length = bundle.sequence_length

for i in range(len(values) - sequence_length):
    x_data.append(values[i : i + sequence_length])
    y_data.append(values[i + sequence_length])

x_data = np.array(x_data)
y_data = np.array(y_data)

# Extract features and scale
x_features = forecaster._add_temporal_features(x_data)
x_scaled = bundle.scaler_x.transform(x_features)

# Predictions
y_pred = np.zeros_like(y_data)
for feat_idx, feature_name in enumerate(FEATURES):
    model = bundle.models[feature_name]
    scaler = bundle.feature_scalers[feature_name]
    y_pred_scaled = model.predict(x_scaled)
    y_pred[:, feat_idx] = scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()

# Calculate R²
r2_overall = r2_score(y_data, y_pred)

print("MODEL R2 SCORES")
print("="*60)
print(f"Overall R2: {r2_overall:.6f}")
print()
print("Per-Feature R2:")
for i, feature in enumerate(FEATURES):
    r2_feat = r2_score(y_data[:, i], y_pred[:, i])
    print(f"  {feature:10s}: {r2_feat:.6f}")

print("="*60)
