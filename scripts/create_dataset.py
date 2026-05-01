from pathlib import Path
import sys
from datetime import UTC, datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

from app.services.data_generator import STPDataGenerator
from app.services.data_store import save_dataset


if __name__ == "__main__":
    days = 183
    start = datetime.now(UTC) - timedelta(days=days)
    generator = STPDataGenerator(seed=42)
    df = generator.generate_days(start_date=start.replace(hour=0, minute=0, second=0, microsecond=0), days=days)
    save_dataset(df)
    print(f"Dataset created with {len(df)} rows and saved.")
