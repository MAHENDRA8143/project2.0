"""
Generates a suite of professional, high-resolution (300 DPI) graphs for a 
wastewater treatment AI project report using matplotlib.

This script creates synthetic time-series data and then produces 10 distinct
visualizations suitable for an academic or engineering report.

Usage:
1. Ensure matplotlib and pandas are installed:
   pip install matplotlib pandas
2. Run the script from the project root directory:
   python scripts/generate_report_graphs.py

This will save 10 PNG files to the `docs/figures/` directory.
"""

import os
import numpy as np
import pandas as pd
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- Configuration ---
OUTPUT_DIR = Path(r"E:\prooooooooojjectt\docs\imagess")
DPI = 300
NUM_POINTS = 365 * 24 # 1 year of hourly data

# --- Synthetic Data Generation ---
def generate_synthetic_data(num_points=NUM_POINTS, seed=42):
    """
    Generates a DataFrame with synthetic wastewater data, including trends, noise, and spikes.
    """
    np.random.seed(seed)
    
    # Time index
    time_index = pd.to_datetime(np.arange(num_points), unit='h', origin=pd.Timestamp('2023-01-01'))
    
    # Base signals with trend and seasonality
    t = np.arange(num_points)
    ph_base = 7.2 + 0.3 * np.sin(2 * np.pi * t / (24 * 7)) + 0.1 * np.sin(2 * np.pi * t / 24)
    do_base = 4.0 - 1.5 * np.sin(2 * np.pi * t / 24 + np.pi/2)
    bod_base = 20 + 10 * np.sin(2 * np.pi * t / 24) + 5 * np.sin(2 * np.pi * t / (24 * 30)) + t/500
    
    # Create correlated signals and add noise
    data = {
        'pH': ph_base + np.random.normal(0, 0.05, num_points),
        'DO': do_base + np.random.normal(0, 0.2, num_points),
        'BOD': bod_base + np.random.normal(0, 2, num_points),
    }
    data['COD'] = data['BOD'] * (1.8 + np.random.normal(0, 0.2, num_points)) + 5
    data['NH3'] = data['BOD'] / 5 + np.random.normal(0, 0.5, num_points) + 2
    data['TP'] = data['BOD'] / 20 + np.random.normal(0, 0.1, num_points) + 0.5
    
    df = pd.DataFrame(data, index=time_index)
    
    # Add random spikes
    df['is_spike'] = False
    num_spikes = int(num_points / 100)
    spike_indices = np.random.choice(df.index, num_spikes, replace=False)
    for idx in spike_indices:
        df.loc[idx, 'BOD'] *= np.random.uniform(1.5, 2.5)
        df.loc[idx, 'COD'] *= np.random.uniform(1.5, 2.0)
        df.loc[idx, 'NH3'] *= np.random.uniform(2.0, 3.0)
        df.loc[idx, 'DO'] /= np.random.uniform(1.5, 2.0)
        df.loc[idx, 'is_spike'] = True
        
    # Clip to realistic values
    df['pH'] = df['pH'].clip(6.0, 9.0)
    df['DO'] = df['DO'].clip(0, 10)
    df['BOD'] = df['BOD'].clip(5, 100)
    df['COD'] = df['COD'].clip(10, 250)
    df['NH3'] = df['NH3'].clip(1, 20)
    df['TP'] = df['TP'].clip(0.1, 5)
    
    return df

def simulate_predictions(df):
    """Simulates model predictions by adding noise to actuals."""
    predictions = df['BOD'].copy() + np.random.normal(0, df['BOD'].std() * 0.1, len(df))
    return predictions.clip(0)

# --- Graph Generation Functions ---

def save_figure(fig, filename):
    """Saves a figure to the output directory."""
    path = OUTPUT_DIR / filename
    fig.savefig(str(path), dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    if path.exists():
        print(f"Saved: {path}")
    else:
        print(f"ERROR: Could not find the file at {path}. Check folder permissions!")

def plot_predicted_vs_actual_line(df, predictions):
    """1. Predicted vs Actual Line Graph"""
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df.index, df['BOD'], label='Actual Values', alpha=0.7)
    ax.plot(df.index, predictions, label='Predicted Values', linestyle='--')
    ax.set_title('Predicted vs. Actual BOD Values Over Time', fontsize=16)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('BOD (mg/L)', fontsize=12)
    ax.legend()
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    fig.tight_layout()
    save_figure(fig, '01_predicted_vs_actual_line.png')

def plot_actual_vs_predicted_scatter(df, predictions):
    """2. Actual vs Predicted Scatter Plot"""
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(df['BOD'], predictions, alpha=0.5, edgecolors='w', linewidth=0.5)
    lims = [
        np.min([ax.get_xlim(), ax.get_ylim()]),
        np.max([ax.get_xlim(), ax.get_ylim()]),
    ]
    ax.plot(lims, lims, 'r--', alpha=0.75, zorder=0, label='Perfect Prediction')
    ax.set_title('Actual vs. Predicted BOD Values', fontsize=16)
    ax.set_xlabel('Actual BOD (mg/L)', fontsize=12)
    ax.set_ylabel('Predicted BOD (mg/L)', fontsize=12)
    ax.set_aspect('equal')
    ax.legend()
    ax.grid(True, linestyle='--', linewidth=0.5)
    fig.tight_layout()
    save_figure(fig, '02_actual_vs_predicted_scatter.png')

def plot_error_distribution_histogram(df, predictions):
    """3. Error Distribution Histogram"""
    errors = df['BOD'] - predictions
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(errors, bins=50, alpha=0.75, edgecolor='black')
    ax.axvline(errors.mean(), color='r', linestyle='--', label=f'Mean Error: {errors.mean():.2f}')
    ax.set_title('Distribution of Prediction Errors (Residuals)', fontsize=16)
    ax.set_xlabel('Error (Actual - Predicted)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.legend()
    ax.grid(True, linestyle='--', linewidth=0.5)
    fig.tight_layout()
    save_figure(fig, '03_error_distribution_histogram.png')

def plot_model_comparison_bar():
    """4. Model Comparison Bar Chart"""
    models = ['Linear Reg.', 'KNN', 'Random Forest', 'ANN', 'ARIMA']
    rmse_values = [12.5, 10.2, 7.8, 8.5, 9.1] # Synthetic performance data
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(models, rmse_values)
    ax.set_title('Model Comparison by Root Mean Square Error (RMSE)', fontsize=16)
    ax.set_xlabel('Model', fontsize=12)
    ax.set_ylabel('RMSE (mg/L)', fontsize=12)
    ax.bar_label(bars, fmt='%.1f')
    ax.grid(axis='y', linestyle='--', linewidth=0.5)
    fig.tight_layout()
    save_figure(fig, '04_model_comparison_bar.png')

def plot_time_series(df):
    """5. Time Series Plot (BOD, COD, DO)"""
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df.index, df['BOD'], label='BOD')
    ax.plot(df.index, df['COD'], label='COD')
    ax.plot(df.index, df['DO'], label='Dissolved Oxygen (DO)')
    ax.set_title('Wastewater Parameter Time Series', fontsize=16)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Concentration (mg/L)', fontsize=12)
    ax.legend()
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    fig.tight_layout()
    save_figure(fig, '05_time_series_plot.png')

def plot_correlation_heatmap(df):
    """6. Correlation Heatmap"""
    corr_df = df[['BOD', 'COD', 'DO', 'pH', 'NH3', 'TP']].corr()
    fig, ax = plt.subplots(figsize=(8, 7))
    cax = ax.imshow(corr_df, cmap='viridis')
    fig.colorbar(cax, label='Correlation Coefficient')
    ax.set_xticks(np.arange(len(corr_df.columns)))
    ax.set_yticks(np.arange(len(corr_df.columns)))
    ax.set_xticklabels(corr_df.columns)
    ax.set_yticklabels(corr_df.columns)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    for i in range(len(corr_df.columns)):
        for j in range(len(corr_df.columns)):
            ax.text(j, i, f"{corr_df.iloc[i, j]:.2f}",
                    ha="center", va="center", color="w")
    ax.set_title('Correlation Heatmap of Water Quality Parameters', fontsize=16)
    fig.tight_layout()
    save_figure(fig, '06_correlation_heatmap.png')

def plot_training_loss_curve():
    """7. Training vs Validation Loss Curve"""
    epochs = np.arange(1, 51)
    train_loss = 0.8 / np.sqrt(epochs) + np.random.normal(0, 0.05, 50)
    val_loss = 0.9 / np.sqrt(epochs) + np.random.normal(0, 0.03, 50) + 0.05
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(epochs, train_loss, label='Training Loss')
    ax.plot(epochs, val_loss, label='Validation Loss')
    ax.set_title('Model Training and Validation Loss Over Epochs', fontsize=16)
    ax.set_xlabel('Epoch', fontsize=12)
    ax.set_ylabel('Loss (e.g., MSE)', fontsize=12)
    ax.legend()
    ax.grid(True, linestyle='--', linewidth=0.5)
    fig.tight_layout()
    save_figure(fig, '07_training_loss_curve.png')

def plot_feature_importance():
    """8. Feature Importance Plot"""
    features = [
        'BOD_lag_1', 'DO_lag_1', 'COD_rolling_mean_24', 'pH_lag_24', 
        'hour_sin', 'day_of_week', 'NH3_lag_1', 'TP_rolling_std_6'
    ]
    importances = sorted([0.35, 0.25, 0.15, 0.10, 0.05, 0.04, 0.03, 0.03])
    features = [x for _, x in sorted(zip(importances, features))]
    
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(features, importances)
    ax.set_title('Feature Importance for BOD Prediction Model', fontsize=16)
    ax.set_xlabel('Importance Score (e.g., Gini Importance)', fontsize=12)
    ax.grid(axis='x', linestyle='--', linewidth=0.5)
    fig.tight_layout()
    save_figure(fig, '08_feature_importance.png')

def plot_anomaly_detection(df):
    """9. Anomaly Detection Graph"""
    anomalies = df[df['is_spike']]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df.index, df['BOD'], label='BOD Time Series', zorder=1)
    ax.scatter(anomalies.index, anomalies['BOD'], color='red', s=50, zorder=2, label='Detected Anomaly (Spike)')
    ax.set_title('Anomaly Detection in BOD Time Series', fontsize=16)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('BOD (mg/L)', fontsize=12)
    ax.legend()
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    fig.tight_layout()
    save_figure(fig, '09_anomaly_detection.png')

def plot_residual_plot(predictions, errors):
    """10. Residual Plot"""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(predictions, errors, alpha=0.5, edgecolors='w', linewidth=0.5)
    ax.axhline(0, color='r', linestyle='--')
    ax.set_title('Residuals vs. Predicted Values', fontsize=16)
    ax.set_xlabel('Predicted BOD (mg/L)', fontsize=12)
    ax.set_ylabel('Residuals (Actual - Predicted)', fontsize=12)
    ax.grid(True, linestyle='--', linewidth=0.5)
    fig.tight_layout()
    save_figure(fig, '10_residual_plot.png')

# --- Main Execution ---
def main():
    """Main function to generate data and all plots."""
    print("Starting graph generation...")
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate data
    print("Generating synthetic data...")
    df = generate_synthetic_data()
    predictions = simulate_predictions(df)
    errors = df['BOD'] - predictions
    print("Data generation complete.")
    
    # Generate all plots
    plot_predicted_vs_actual_line(df.head(24*7), predictions.head(24*7)) # Plot first week for clarity
    plot_actual_vs_predicted_scatter(df, predictions)
    plot_error_distribution_histogram(df, predictions)
    plot_model_comparison_bar()
    plot_time_series(df.head(24*14)) # Plot first two weeks
    plot_correlation_heatmap(df)
    plot_training_loss_curve()
    plot_feature_importance()
    plot_anomaly_detection(df.head(24*30)) # Plot first month
    plot_residual_plot(predictions, errors)
    
    print("All graphs have been generated successfully.")

if __name__ == '__main__':
    main()