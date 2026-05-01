from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

from app.services.data_store import ensure_dataset
from app.services.model_pipeline import STPForecaster


if __name__ == "__main__":
    df = ensure_dataset(days=60)
    forecaster = STPForecaster(sequence_length=72, horizon=24)
    forecaster.train(df, epochs=10)
    print("CNN-LSTM-Attention model trained and saved.")
