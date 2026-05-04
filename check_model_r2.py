#!/usr/bin/env python3
"""
Script to evaluate the STP Forecaster model's R² score
"""
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
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error, mean_absolute_percentage_error
from app.core.config import FEATURES, MODEL_PATH
from app.services.data_store import ensure_dataset
from app.services.model_pipeline import STPForecaster

def calculate_model_r2():
    """Load model and calculate R² score on the full dataset"""
    
    # Load data
    print("Loading dataset...")
    df = ensure_dataset(days=90)
    print(f"[OK] Dataset loaded: {len(df)} rows")
    
    # Check if model exists
    if not MODEL_PATH.exists():
        print(f"[ERROR] Model not found at {MODEL_PATH}")
        print("  Please train the model first using: python scripts/train_model.py")
        return None
    
    # Load the trained model
    print(f"\nLoading model from {MODEL_PATH}...")
    forecaster = STPForecaster(sequence_length=72, horizon=24)
    bundle = forecaster._load_bundle()
    print("[OK] Model loaded successfully")
    
    # Prepare data for prediction
    print("\nPreparing validation data...")
    values = df[FEATURES].values.astype(np.float32)
    
    # Create windows (same as training)
    x_data = []
    y_data = []
    sequence_length = bundle.sequence_length
    
    for i in range(len(values) - sequence_length):
        x_data.append(values[i : i + sequence_length])
        y_data.append(values[i + sequence_length])
    
    if not x_data:
        print("[ERROR] Not enough data to create validation windows")
        return None
    
    x_data = np.array(x_data)
    y_data = np.array(y_data)
    print(f"[OK] Created {len(x_data)} validation windows")
    
    # Add temporal features (same as training)
    print("\nExtracting temporal features...")
    x_features = forecaster._add_temporal_features(x_data)
    
    # Scale the input data
    print("Scaling data...")
    x_scaled = bundle.scaler_x.transform(x_features)
    print("[OK] Input data scaled")
    
    # Make predictions
    print("\nMaking predictions...")
    y_pred = np.zeros_like(y_data)
    
    for feat_idx, feature_name in enumerate(FEATURES):
        model = bundle.models[feature_name]
        scaler = bundle.feature_scalers[feature_name]
        
        # Predict scaled values
        y_pred_scaled = model.predict(x_scaled)
        
        # Inverse scale predictions
        y_pred[:, feat_idx] = scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()
    
    print(f"[OK] Generated {len(y_pred)} predictions")
    
    # Calculate R² score
    print("\n" + "="*60)
    print("MODEL R2 SCORE EVALUATION (IMPROVED)")
    print("="*60)
    
    # Overall R² score
    r2_overall = r2_score(y_data, y_pred)
    print(f"\n[SCORE] Overall R2 Score: {r2_overall:.6f}")
    
    if r2_overall < 0.5:
        print("   [WARNING] Model is not performing well (R2 < 0.5)")
    elif r2_overall < 0.7:
        print("   [OK] Model performance is fair")
    elif r2_overall < 0.9:
        print("   [OK] Model performance is good")
    else:
        print("   [EXCELLENT] Model performance is excellent!")
    
    # Per-feature R² scores
    print("\n[FEATURES] R2 Score per Feature:")
    print("-" * 40)
    feature_r2_scores = {}
    for i, feature in enumerate(FEATURES):
        r2_feat = r2_score(y_data[:, i], y_pred[:, i])
        feature_r2_scores[feature] = r2_feat
        status = "[EXCELLENT]" if r2_feat > 0.9 else "[OK]" if r2_feat > 0.7 else "[FAIR]"
        print(f"  {feature:25s}: {r2_feat:10.6f} {status}")
    
    # Additional metrics
    print("\n[METRICS] Additional Performance Metrics:")
    print("-" * 40)
    
    mse = mean_squared_error(y_data, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_data, y_pred)
    
    print(f"  Mean Squared Error (MSE):     {mse:.6f}")
    print(f"  Root Mean Squared Error (RMSE): {rmse:.6f}")
    print(f"  Mean Absolute Error (MAE):    {mae:.6f}")
    
    # MAPE per feature (avoiding division by zero)
    print(f"\n  MAPE (Mean Absolute Percentage Error) per Feature:")
    for i, feature in enumerate(FEATURES):
        # Filter out zero values to avoid inf/nan
        mask = y_data[:, i] != 0
        if mask.sum() > 0:
            mape = mean_absolute_percentage_error(y_data[mask, i], y_pred[mask, i])
            print(f"    {feature:23s}: {mape:.4%}")
    
    print("\n" + "="*60)
    print("[OK] Evaluation Complete!")
    print("="*60 + "\n")
    
    return {
        'overall_r2': r2_overall,
        'feature_r2_scores': feature_r2_scores,
        'rmse': rmse,
        'mae': mae,
        'mse': mse
    }

if __name__ == "__main__":
    results = calculate_model_r2()
    if results:
        print("\n[SUMMARY] Model Performance Summary:")
        print(f"  Overall R2: {results['overall_r2']:.6f}")
        print(f"  RMSE: {results['rmse']:.6f}")
        print(f"  MAE: {results['mae']:.6f}")
