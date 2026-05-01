from __future__ import annotations

from pathlib import Path
import sys
import time

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

from app.services.data_store import append_next_hour, ensure_dataset


def run_forever(interval_seconds: int = 3600, seed: int = 42) -> None:
    ensure_dataset()
    try:
        while True:
            combined = append_next_hour(seed=seed)
            latest = pd.to_datetime(combined["timestamp"]).max()
            print(f"Appended data through {latest.isoformat()} (rows={len(combined)})")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("Continuous generator stopped cleanly.")


if __name__ == "__main__":
    run_forever(interval_seconds=3600, seed=42)
