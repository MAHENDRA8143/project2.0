from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from typing import List

import pandas as pd


@dataclass
class HourlyReading:
    timestamp: datetime
    BOD: float
    COD: float
    pH: float
    DO: float
    NH3_N: float
    TP: float
    is_spike: int


class STPDataGenerator:
    """
    Generates realistic, pattern-based hourly STP data.

    Normal readings are modeled around plausible treated wastewater operating
    ranges. Every day includes 3-6 anomaly hours so the dashboard can show
    problematic operating situations and alerts.
    """

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    def _time_load_factor(self, hour: int) -> float:
        if 6 <= hour <= 10:
            return 1.35
        if 12 <= hour <= 16:
            return 1.15
        if 0 <= hour <= 4 or 21 <= hour <= 23:
            return 0.8
        return 1.0

    def _daily_wave(self, hour: int) -> float:
        return 1.0 + 0.12 * math.sin((hour / 24.0) * 2 * math.pi)

    def _day_seed(self, day_start: datetime, suffix: str = "values") -> int:
        day_key = f"{self.seed}:{suffix}:{day_start.date().isoformat()}".encode("utf-8")
        return int(sha256(day_key).hexdigest(), 16) % (2**32)

    def _daily_anomaly_plan(self, day_start: datetime) -> dict[int, str]:
        rng = random.Random(self._day_seed(day_start, suffix="anomalies"))

        anomaly_count = rng.randint(3, 6)
        preferred_hours = [6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 18, 19, 20, 21]
        anomaly_hours = rng.sample(preferred_hours, k=min(anomaly_count, len(preferred_hours)))
        anomaly_types = ["organic_overload", "low_do", "ph_shock", "nutrient_spike"]
        return {hour: rng.choice(anomaly_types) for hour in anomaly_hours}

    def generate_hour(self, timestamp: datetime, anomaly_type: str | None = None) -> HourlyReading:
        hour = timestamp.hour

        load_factor = self._time_load_factor(hour)
        wave = self._daily_wave(hour)

        # Typical treated STP effluent baseline: BOD mostly 8-28 mg/L,
        # COD proportional to BOD, DO inversely related to organic load.
        base_bod = 18.0 * load_factor * wave
        noise_bod = self.rng.uniform(-3.0, 3.5)
        bod = max(8.0, base_bod + noise_bod)

        cod_ratio = self.rng.uniform(1.95, 2.95)
        cod = max(18.0, cod_ratio * bod + self.rng.uniform(-4.0, 5.5))

        do = 7.8 - 0.1 * bod + self.rng.uniform(-0.4, 0.5)
        do = min(8.8, max(2.6, do))

        ph = 7.2 + self.rng.uniform(-0.25, 0.28) - 0.0015 * (bod - 18)
        ph = min(8.2, max(6.7, ph))

        nh3_n = 2.5 + 0.15 * bod + self.rng.uniform(-0.6, 0.8)
        nh3_n = max(1.2, nh3_n)

        tp = 0.60 + 0.06 * bod + self.rng.uniform(-0.2, 0.3)
        tp = max(0.35, tp)

        is_spike = 1 if anomaly_type else 0
        if anomaly_type == "organic_overload":
            multiplier = self.rng.uniform(1.65, 2.5)
            bod *= multiplier
            cod *= self.rng.uniform(1.5, 2.2)
            nh3_n *= self.rng.uniform(1.3, 1.8)
            tp *= self.rng.uniform(1.2, 1.6)
            do = max(0.5, do - self.rng.uniform(1.8, 3.5))
            ph = min(8.8, max(6.2, ph + self.rng.uniform(-0.2, 0.2)))
        elif anomaly_type == "low_do":
            bod *= self.rng.uniform(1.1, 1.4)
            cod *= self.rng.uniform(1.1, 1.4)
            do = max(0.4, do - self.rng.uniform(2.5, 4.5))
        elif anomaly_type == "ph_shock":
            ph = self.rng.choice([
                self.rng.uniform(5.2, 6.2),
                self.rng.uniform(8.8, 9.5),
            ])
            bod *= self.rng.uniform(1.1, 1.3)
            cod *= self.rng.uniform(1.1, 1.3)
            do = max(1.2, do - self.rng.uniform(0.5, 1.8))
        elif anomaly_type == "nutrient_spike":
            nh3_n *= self.rng.uniform(2.0, 3.2)
            tp *= self.rng.uniform(1.9, 3.0)
            bod *= self.rng.uniform(1.15, 1.5)
            cod *= self.rng.uniform(1.15, 1.4)
            do = max(1.0, do - self.rng.uniform(1.0, 2.5))

        return HourlyReading(
            timestamp=timestamp,
            BOD=round(bod, 2),
            COD=round(cod, 2),
            pH=round(ph, 2),
            DO=round(do, 2),
            NH3_N=round(nh3_n, 2),
            TP=round(tp, 2),
            is_spike=is_spike,
        )

    def generate_day(self, day_start: datetime) -> List[HourlyReading]:
        self.rng = random.Random(self._day_seed(day_start))
        anomaly_plan = self._daily_anomaly_plan(day_start)
        readings: List[HourlyReading] = []

        for hour in range(24):
            ts = day_start + timedelta(hours=hour)
            readings.append(self.generate_hour(ts, anomaly_type=anomaly_plan.get(hour)))

        return readings

    def generate_days(self, start_date: datetime, days: int) -> pd.DataFrame:
        records = []
        for day_idx in range(days):
            day_start = start_date + timedelta(days=day_idx)
            records.extend(self.generate_day(day_start))

        df = pd.DataFrame([reading.__dict__ for reading in records])
        df.sort_values("timestamp", inplace=True)
        return df
