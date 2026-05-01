from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "backend" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = DATA_DIR / "synthetic_stp_data.csv"
MODEL_PATH = DATA_DIR / "cnn_lstm_attention.keras"
SCALER_X_PATH = DATA_DIR / "scaler_x.joblib"
SCALER_Y_PATH = DATA_DIR / "scaler_y.joblib"

FEATURES = ["BOD", "COD", "pH", "DO", "NH3_N", "TP"]

ALERT_THRESHOLDS = {
    "BOD_WARNING": 30.0,
    "BOD_CRITICAL": 50.0,
    "DO_DANGEROUS": 3.0,
    "PH_LOW": 6.5,
    "PH_HIGH": 8.5,
}

JWT_SECRET_KEY = "change-this-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60
