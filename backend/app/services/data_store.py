from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from app.core.config import CSV_PATH, FEATURES
from app.services.data_generator import STPDataGenerator


DEFAULT_HISTORY_DAYS = 183


def ensure_dataset(days: int = DEFAULT_HISTORY_DAYS) -> pd.DataFrame:
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
        if not df.empty:
            return df

    start = datetime.now(UTC) - timedelta(days=days)
    generator = STPDataGenerator(seed=42)
    df = generator.generate_days(start_date=start.replace(hour=0, minute=0, second=0, microsecond=0), days=days)
    save_dataset(df)
    return df


def save_dataset(df: pd.DataFrame) -> None:
    ordered_columns = ["timestamp", *FEATURES, "is_spike"]
    df = df[ordered_columns].copy()
    df.sort_values("timestamp", inplace=True)
    df.to_csv(CSV_PATH, index=False)


def load_dataset() -> pd.DataFrame:
    return ensure_dataset()


def append_dataset(new_rows: pd.DataFrame) -> pd.DataFrame:
    existing = ensure_dataset()
    combined = pd.concat([existing, new_rows], ignore_index=True)
    combined.drop_duplicates(subset=["timestamp"], keep="last", inplace=True)
    combined.sort_values("timestamp", inplace=True)
    save_dataset(combined)
    return combined


def regenerate_dataset(days: int = DEFAULT_HISTORY_DAYS, seed: int = 42) -> pd.DataFrame:
    start = datetime.now(UTC) - timedelta(days=days)
    generator = STPDataGenerator(seed=seed)
    df = generator.generate_days(start_date=start.replace(hour=0, minute=0, second=0, microsecond=0), days=days)
    save_dataset(df)
    return df


def append_next_day(seed: int = 42) -> pd.DataFrame:
    df = ensure_dataset()
    last_timestamp = pd.to_datetime(df["timestamp"]).max()
    next_day_start = (last_timestamp + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    generator = STPDataGenerator(seed=seed)
    new_day = generator.generate_days(start_date=next_day_start, days=1)
    return append_dataset(new_day)


def append_next_hour(seed: int = 42) -> pd.DataFrame:
    df = ensure_dataset()
    last_timestamp = pd.to_datetime(df["timestamp"]).max()
    next_timestamp = last_timestamp + timedelta(hours=1)
    next_timestamp = pd.Timestamp(next_timestamp).to_pydatetime()

    day_start = next_timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    generator = STPDataGenerator(seed=seed)
    day_rows = generator.generate_day(day_start)
    row = next(reading for reading in day_rows if reading.timestamp.hour == next_timestamp.hour)
    row_df = pd.DataFrame([row.__dict__])
    return append_dataset(row_df)


def get_recent_data(hours: int = 24) -> pd.DataFrame:
    df = ensure_dataset()
    df.sort_values("timestamp", inplace=True)
    return df.tail(hours).copy()
