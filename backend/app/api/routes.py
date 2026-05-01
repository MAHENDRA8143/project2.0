from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response

from app.api.schemas import LoginRequest, TokenResponse
from app.core.auth import User, authenticate_user, get_current_user, require_admin
from app.core.security import create_access_token
from app.services.alert_engine import evaluate_alerts
from app.services.data_store import ensure_dataset, get_recent_data, regenerate_dataset, save_dataset
from app.services.explainability import feature_delta_summary, trend_explanation
from app.services.model_pipeline import STPForecaster

router = APIRouter(prefix="/api")
IST = ZoneInfo("Asia/Kolkata")


def _next_ist_hour_as_utc() -> datetime:
    now_ist = datetime.now(IST)
    next_ist_hour = (now_ist.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    return next_ist_hour.astimezone(UTC)


def _forecast_condition(record: dict) -> str:
    bod = float(record["BOD"])
    do = float(record["DO"])
    ph = float(record["pH"])
    if bod > 50 or do < 3 or ph < 6.5 or ph > 8.5:
        return "critical"
    if bod > 30:
        return "warning"
    return "safe"


def _build_7_day_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """Build a 7-day forecast by chaining the stable next-day forecaster."""
    working_df = df.copy()
    all_predictions = []
    start_time = _next_ist_hour_as_utc()

    for day_index in range(7):
        forecaster = STPForecaster(sequence_length=72, horizon=24)
        result = forecaster.predict_next_day(working_df)
        day_df = result.prediction_df.copy()
        day_df["timestamp"] = [start_time + timedelta(hours=day_index * 24 + hour) for hour in range(len(day_df))]
        all_predictions.append(day_df)

        working_df = pd.concat([working_df.iloc[24:], day_df], ignore_index=True)

    return pd.concat(all_predictions, ignore_index=True)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username/password")
    token = create_access_token(subject=user.username, role=user.role)
    return TokenResponse(access_token=token, role=user.role)


@router.get("/data/current")
def current_data(hours: int = 24, _: User = Depends(get_current_user)):
    df = get_recent_data(hours)
    records = df.to_dict(orient="records")
    for item in records:
        item["timestamp"] = pd.Timestamp(item["timestamp"]).isoformat()
    return {"hours": hours, "records": records}


@router.get("/predictions/next-day")
def next_day_prediction(history_hours: int = 72, _: User = Depends(get_current_user)):
    df = ensure_dataset()
    if len(df) < history_hours:
        raise HTTPException(status_code=400, detail="Not enough historical data")

    history_df = df.tail(history_hours).copy()
    history_df.sort_values("timestamp", inplace=True)

    forecaster = STPForecaster(sequence_length=min(72, history_hours), horizon=24)
    result = forecaster.predict_next_day(df)

    start_time = _next_ist_hour_as_utc()
    pred_df = result.prediction_df.copy()
    pred_df["timestamp"] = [start_time + timedelta(hours=i) for i in range(24)]

    explanation = trend_explanation(history_df, pred_df)
    deltas = feature_delta_summary(history_df, pred_df)

    out = pred_df.to_dict(orient="records")
    for item in out:
        timestamp = pd.Timestamp(item["timestamp"])
        item["timestamp"] = timestamp.isoformat()
        ist_timestamp = timestamp.tz_convert(IST) if timestamp.tzinfo else timestamp.tz_localize(UTC).tz_convert(IST)
        item["hour_label"] = ist_timestamp.strftime("%H:%M")
        item["condition"] = _forecast_condition(item)

    return {
        "history_hours": history_hours,
        "predictions": out,
        "explanation": explanation,
        "feature_deltas": deltas,
    }


@router.get("/predictions/next-7-days")
def next_7_days_prediction(_: User = Depends(get_current_user)):
    df = ensure_dataset()
    if len(df) < 72:
        raise HTTPException(status_code=400, detail="Not enough historical data")

    try:
        pred_df = _build_7_day_forecast(df)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"7-day forecast failed: {exc}") from exc

    out = pred_df.to_dict(orient="records")
    for index, item in enumerate(out):
        timestamp = pd.Timestamp(item["timestamp"])
        item["timestamp"] = timestamp.isoformat()
        ist_timestamp = timestamp.tz_convert(IST) if timestamp.tzinfo else timestamp.tz_localize(UTC).tz_convert(IST)
        item["hour_label"] = ist_timestamp.strftime("%H:%M")
        item["day_label"] = ist_timestamp.strftime("%a, %b %d")
        item["condition"] = _forecast_condition(item)
        item["day_index"] = index // 24 + 1

    return {
        "forecast_hours": len(out),
        "predictions": out,
    }


@router.get("/predictions/next-7-days/download")
def next_7_days_download(_: User = Depends(get_current_user)):
    """Generate 7-day forecast and return as downloadable CSV."""
    df = ensure_dataset()
    if len(df) < 72:
        raise HTTPException(status_code=400, detail="Not enough historical data")

    forecaster = STPForecaster(sequence_length=72, horizon=24)
    result = forecaster.predict_next_7_days(df)

    start_time = _next_ist_hour_as_utc()
    pred_df = result.prediction_df.copy()
    
    # Create timestamps and format for IST
    timestamps_ist = []
    for i in range(len(pred_df)):
        ts_utc = start_time + timedelta(hours=i)
        # Convert to IST string
        ts_ist = ts_utc.astimezone(IST) if ts_utc.tzinfo else ts_utc.replace(tzinfo=UTC).astimezone(IST)
        timestamps_ist.append(ts_ist.strftime("%Y-%m-%d %H:%M:%S IST"))
    
    output_df = pred_df.copy()
    output_df["timestamp"] = timestamps_ist

    # Generate CSV
    csv_content = output_df.to_csv(index=False)
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=forecast_7days.csv"},
    )


@router.get("/alerts")
def alerts(source: Literal["realtime", "predicted", "both"] = "both", user: User = Depends(get_current_user)):
    df = ensure_dataset()
    realtime_df = df.tail(24).copy()
    realtime_df["timestamp"] = pd.to_datetime(realtime_df["timestamp"])

    response = {"source": source, "alerts": []}

    if source in ("realtime", "both"):
        response["alerts"].extend(evaluate_alerts(realtime_df.to_dict(orient="records"), source="realtime"))

    if source in ("predicted", "both"):
        pred_payload = next_day_prediction(72, user)
        pred_df = pd.DataFrame(pred_payload["predictions"])
        pred_df["timestamp"] = pd.to_datetime(pred_df["timestamp"])
        response["alerts"].extend(evaluate_alerts(pred_df.to_dict(orient="records"), source="predicted"))

    deduped = {}
    for alert in response["alerts"]:
        key = (alert["time"], alert["severity"], alert["message"].split(" at ")[0])
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = alert
            continue

        # Prefer predicted alerts over realtime duplicates for the same hour.
        if existing["source"] == "realtime" and alert["source"] == "predicted":
            deduped[key] = alert

    response["alerts"] = sorted(deduped.values(), key=lambda x: x["time"])
    return response


@router.post("/admin/regenerate")
def admin_regenerate(days: int = 45, seed: int = 42, _: User = Depends(require_admin)):
    df = regenerate_dataset(days=days, seed=seed)
    save_dataset(df)
    return {"status": "ok", "rows": len(df), "days": days, "seed": seed}
