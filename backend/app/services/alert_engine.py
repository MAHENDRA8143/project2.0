from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.core.config import ALERT_THRESHOLDS


def _format_hour(ts: datetime) -> str:
    if not hasattr(ts, "strftime"):
        return str(ts)
    return ts.strftime("%I %p").lstrip("0")


def _severity_rank(severity: str) -> int:
    return {"warning": 1, "critical": 2}.get(severity, 0)


def _alert_phrase(metric: str, source: str, level: str, time_text: str) -> str:
    if metric == "BOD":
        if level == "critical":
            return f"Critical: BOD {'will exceed' if source == 'predicted' else 'exceeded'} safe limit at {time_text}"
        return f"Warning: BOD {'will exceed' if source == 'predicted' else 'exceeded'} safe limit at {time_text}"

    if metric == "DO":
        return f"Critical: DO {'dropping dangerously' if source == 'predicted' else 'dropped dangerously'} at {time_text}"

    if metric == "pH":
        return f"Warning: pH {'will be' if source == 'predicted' else 'is'} imbalanced at {time_text}"

    return f"Warning: {metric} anomaly at {time_text}"


def _is_new_violation(metric: str, value: float, previous: Dict[str, Any] | None) -> bool:
    if previous is None:
        return True

    previous_value = float(previous[metric])

    if metric == "BOD":
        crossed_warning = previous_value <= ALERT_THRESHOLDS["BOD_WARNING"] < value
        crossed_critical = previous_value <= ALERT_THRESHOLDS["BOD_CRITICAL"] < value
        return crossed_warning or crossed_critical

    if metric == "DO":
        return previous_value >= ALERT_THRESHOLDS["DO_DANGEROUS"] > value

    if metric == "pH":
        previous_bad = previous_value < ALERT_THRESHOLDS["PH_LOW"] or previous_value > ALERT_THRESHOLDS["PH_HIGH"]
        current_bad = value < ALERT_THRESHOLDS["PH_LOW"] or value > ALERT_THRESHOLDS["PH_HIGH"]
        return current_bad and not previous_bad

    return True


def evaluate_alerts(records: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    previous_row: Dict[str, Any] | None = None

    for row in records:
        timestamp = row["timestamp"]
        if not isinstance(timestamp, datetime):
            timestamp = datetime.fromisoformat(str(timestamp))

        bod = float(row["BOD"])
        do = float(row["DO"])
        ph = float(row["pH"])

        time_text = _format_hour(timestamp)
        issues: List[Dict[str, str]] = []

        if bod > ALERT_THRESHOLDS["BOD_CRITICAL"] and _is_new_violation("BOD", bod, previous_row):
            issues.append({"metric": "BOD", "severity": "critical"})
        elif bod > ALERT_THRESHOLDS["BOD_WARNING"] and _is_new_violation("BOD", bod, previous_row):
            issues.append({"metric": "BOD", "severity": "warning"})

        if do < ALERT_THRESHOLDS["DO_DANGEROUS"] and _is_new_violation("DO", do, previous_row):
            issues.append({"metric": "DO", "severity": "critical"})

        if (ph < ALERT_THRESHOLDS["PH_LOW"] or ph > ALERT_THRESHOLDS["PH_HIGH"]) and _is_new_violation("pH", ph, previous_row):
            issues.append({"metric": "pH", "severity": "warning"})

        if issues:
            severity = max((issue["severity"] for issue in issues), key=_severity_rank)
            metrics = ", ".join(issue["metric"] for issue in issues)

            if len(issues) == 1:
                metric = issues[0]["metric"]
                message = _alert_phrase(metric, source, severity, time_text)
            else:
                message = (
                    f"Critical: {metrics} {'will exceed' if source == 'predicted' else 'exceeded'} safe limits at {time_text}"
                    if severity == "critical"
                    else f"Warning: {metrics} {'will exceed' if source == 'predicted' else 'exceeded'} safe limits at {time_text}"
                )

            alerts.append({"severity": severity, "message": message, "time": timestamp.isoformat(), "source": source})

        previous_row = row

    alerts.sort(key=lambda x: x["time"])
    return alerts
