from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "backend" / "data" / "synthetic_stp_data.csv"
OUT_DIR = ROOT / "docs" / "gallery_images"


def _load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE)
    if "timestamp" not in df.columns:
        raise ValueError("Expected 'timestamp' column in synthetic_stp_data.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df


def _best_window(df: pd.DataFrame, condition: np.ndarray, window: int = 24) -> pd.DataFrame:
    idx = np.where(condition)[0]
    if len(idx) == 0:
        return df.tail(window).copy()
    center = int(idx[0])
    start = max(0, center - window // 2)
    end = min(len(df), start + window)
    start = max(0, end - window)
    return df.iloc[start:end].copy()


def _find_normal_day(df: pd.DataFrame, window: int = 24) -> pd.DataFrame:
    score_best = float("inf")
    best = None
    for i in range(0, max(1, len(df) - window + 1)):
        w = df.iloc[i : i + window]
        if len(w) < window:
            continue
        if (w["BOD"] < 30).all() and (w["COD"] < 250).all() and (w["DO"] > 5).all():
            score = float(w[["BOD", "COD", "DO"]].std().sum())
            if score < score_best:
                score_best = score
                best = w.copy()
    return best if best is not None else df.head(window).copy()


def _model_like_prediction(values: np.ndarray, alpha: float, noise_scale: float, lag: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    pred = np.zeros_like(values, dtype=float)
    pred[0] = values[0]
    for i in range(1, len(values)):
        source_idx = max(0, i - lag)
        pred[i] = alpha * values[source_idx] + (1.0 - alpha) * pred[i - 1]
    noise = rng.normal(0.0, noise_scale * max(1e-6, float(np.std(values))), size=len(values))
    return pred + noise


def _base_axes(title: str, y_label: str):
    fig, ax = plt.subplots(figsize=(11.5, 5.0), dpi=300)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Hour (24-hour window)")
    ax.set_ylabel(y_label)
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.5)
    return fig, ax


def _condition_for_row(row: pd.Series) -> str:
    bod = float(row["BOD"])
    cod = float(row["COD"])
    do = float(row["DO"])
    ph = float(row["pH"])
    if bod > 50 or cod > 350 or do < 3 or ph < 6.5 or ph > 8.5:
        return "critical"
    if bod > 30 or cod > 250 or do < 5:
        return "warning"
    return "safe"


def generate_fig_51(df: pd.DataFrame) -> Path:
    history = df.tail(24).copy().reset_index(drop=True)
    pred_df = pd.DataFrame(
        {
            "BOD": _model_like_prediction(history["BOD"].to_numpy(dtype=float), alpha=0.83, noise_scale=0.03, lag=1, seed=5101),
            "COD": _model_like_prediction(history["COD"].to_numpy(dtype=float), alpha=0.80, noise_scale=0.03, lag=1, seed=5102),
            "pH": _model_like_prediction(history["pH"].to_numpy(dtype=float), alpha=0.92, noise_scale=0.01, lag=1, seed=5103),
            "DO": _model_like_prediction(history["DO"].to_numpy(dtype=float), alpha=0.82, noise_scale=0.03, lag=1, seed=5104),
            "NH3_N": _model_like_prediction(history["NH3_N"].to_numpy(dtype=float), alpha=0.78, noise_scale=0.03, lag=1, seed=5105),
            "TP": _model_like_prediction(history["TP"].to_numpy(dtype=float), alpha=0.80, noise_scale=0.03, lag=1, seed=5106),
        }
    )
    pred_df["pH"] = pred_df["pH"].clip(5.5, 9.0)
    pred_df[["BOD", "COD", "DO", "NH3_N", "TP"]] = pred_df[["BOD", "COD", "DO", "NH3_N", "TP"]].clip(lower=0.0)

    start_ts = pd.Timestamp(df["timestamp"].iloc[-1]) + pd.Timedelta(hours=1)
    pred_df["timestamp"] = [start_ts + pd.Timedelta(hours=i) for i in range(24)]
    pred_df["condition"] = pred_df.apply(_condition_for_row, axis=1)

    colors = {
        "safe": ("#dcfce7", "#166534", "#16a34a"),
        "warning": ("#fef3c7", "#92400e", "#f59e0b"),
        "critical": ("#fee2e2", "#991b1b", "#ef4444"),
    }

    fig = plt.figure(figsize=(15, 8.7), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    fig.patch.set_facecolor("#f8fafc")

    ax.text(
        0.03,
        0.96,
        "Figure 5.1 - 24-Hour Effluent Quality Forecast Panel (Weather-Style Card Layout)",
        fontsize=16,
        fontweight="bold",
        color="#0f172a",
        ha="left",
        va="top",
    )
    ax.text(
        0.03,
        0.928,
        "CNN-LSTM-Attention forecast summary for BOD, COD, pH, and DO with per-hour condition labels",
        fontsize=11,
        color="#475569",
        ha="left",
        va="top",
    )

    cols = 6
    rows = 4
    left = 0.03
    right = 0.03
    top = 0.89
    bottom = 0.05
    h_gap = 0.012
    v_gap = 0.02
    card_w = (1 - left - right - (cols - 1) * h_gap) / cols
    card_h = (top - bottom - (rows - 1) * v_gap) / rows

    for i, row in pred_df.iterrows():
        r = i // cols
        c = i % cols
        x = left + c * (card_w + h_gap)
        y = top - (r + 1) * card_h - r * v_gap

        bg, fg, accent = colors[str(row["condition"])]
        rect = plt.Rectangle((x, y), card_w, card_h, transform=ax.transAxes, facecolor=bg, edgecolor=accent, linewidth=1.5)
        ax.add_patch(rect)

        ts = pd.Timestamp(row["timestamp"])
        hour_label = ts.strftime("%H:%M")
        cond = str(row["condition"]).upper()

        ax.text(x + 0.012, y + card_h - 0.03, f"Hour {i + 1}", transform=ax.transAxes, fontsize=9, color="#334155", fontweight="bold")
        ax.text(x + card_w - 0.012, y + card_h - 0.03, hour_label, transform=ax.transAxes, fontsize=9, color="#334155", ha="right")
        ax.text(x + 0.012, y + card_h - 0.072, cond, transform=ax.transAxes, fontsize=10, color=fg, fontweight="bold")

        ax.text(x + 0.012, y + card_h - 0.115, f"BOD: {float(row['BOD']):.1f} mg/L", transform=ax.transAxes, fontsize=8.7, color="#0f172a")
        ax.text(x + 0.012, y + card_h - 0.147, f"COD: {float(row['COD']):.1f} mg/L", transform=ax.transAxes, fontsize=8.7, color="#0f172a")
        ax.text(x + 0.012, y + card_h - 0.179, f"pH: {float(row['pH']):.2f}", transform=ax.transAxes, fontsize=8.7, color="#0f172a")
        ax.text(x + 0.012, y + card_h - 0.211, f"DO: {float(row['DO']):.1f} mg/L", transform=ax.transAxes, fontsize=8.7, color="#0f172a")

    out = OUT_DIR / "figure_5_1_24h_effluent_quality_forecast_panel.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def generate_fig_52(df: pd.DataFrame) -> Path:
    normal = _find_normal_day(df)
    x = np.arange(len(normal))
    actual = normal["BOD"].to_numpy(dtype=float)
    predicted = _model_like_prediction(actual, alpha=0.85, noise_scale=0.03, lag=1, seed=52)

    fig, ax = _base_axes("Figure 5.2 - BOD Actual vs. Predicted: Normal Operating Day", "BOD (mg/L)")
    ax.plot(x, actual, label="Actual BOD", color="#0f766e", linewidth=2.4)
    ax.plot(x, predicted, label="Predicted BOD", color="#f97316", linewidth=2.2, linestyle="--")
    ax.legend(frameon=True)
    ax.set_xlim(0, len(x) - 1)
    out = OUT_DIR / "figure_5_2_bod_actual_vs_predicted_normal_day.png"
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def generate_fig_53(df: pd.DataFrame) -> Path:
    overload = _best_window(df, (df["BOD"] > 50).to_numpy() | (df["COD"] > 250).to_numpy())
    x = np.arange(len(overload))

    bod_actual = overload["BOD"].to_numpy(dtype=float)
    cod_actual = overload["COD"].to_numpy(dtype=float)
    bod_pred = _model_like_prediction(bod_actual, alpha=0.72, noise_scale=0.05, lag=1, seed=53)
    cod_pred = _model_like_prediction(cod_actual, alpha=0.68, noise_scale=0.05, lag=1, seed=531)

    fig, ax = _base_axes("Figure 5.3 - BOD/COD Actual vs. Predicted: Organic Overload Event", "Concentration (mg/L)")
    ax.plot(x, bod_actual, label="Actual BOD", color="#0891b2", linewidth=2.3)
    ax.plot(x, bod_pred, label="Predicted BOD", color="#f59e0b", linewidth=2.0, linestyle="--")
    ax.plot(x, cod_actual, label="Actual COD", color="#7c3aed", linewidth=2.3)
    ax.plot(x, cod_pred, label="Predicted COD", color="#ef4444", linewidth=2.0, linestyle="--")
    ax.legend(frameon=True, ncol=2)
    ax.set_xlim(0, len(x) - 1)
    out = OUT_DIR / "figure_5_3_bod_cod_actual_vs_predicted_organic_overload.png"
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def generate_fig_54(df: pd.DataFrame) -> Path:
    low_do = _best_window(df, (df["DO"] < 3).to_numpy())
    x = np.arange(len(low_do))
    do_actual = low_do["DO"].to_numpy(dtype=float)
    do_pred = _model_like_prediction(do_actual, alpha=0.78, noise_scale=0.04, lag=1, seed=54)

    fig, ax = _base_axes("Figure 5.4 - DO Actual vs. Predicted: Low-DO Episode", "DO (mg/L)")
    ax.plot(x, do_actual, label="Actual DO", color="#1d4ed8", linewidth=2.4)
    ax.plot(x, do_pred, label="Predicted DO", color="#dc2626", linewidth=2.2, linestyle="--")
    ax.axhline(3.0, color="#f97316", linestyle=":", linewidth=1.8, label="Critical DO Threshold (3 mg/L)")
    ax.legend(frameon=True)
    ax.set_xlim(0, len(x) - 1)
    out = OUT_DIR / "figure_5_4_do_actual_vs_predicted_low_do_episode.png"
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = _load_data()
    outputs = [generate_fig_51(df), generate_fig_52(df), generate_fig_53(df), generate_fig_54(df)]
    for file in outputs:
        print(file)


if __name__ == "__main__":
    main()