"""Sensor data-quality / anomaly detection.

Pure detection functions (stdlib only) + DB orchestration that mirrors
app/utils/alert_engine.py. Never raises into the ingest path.
"""
from dataclasses import dataclass


@dataclass
class AnomalyResult:
    anomaly_type: str   # "implausible" | "flatline" | "spike" | "drift"
    severity: str       # "warning" | "danger"
    reason: str         # human-readable (Indonesian)


# ── Config (tunable) ────────────────────────────────────────────────
IN_SCOPE_FIELDS = ["ph", "tss", "cod", "nh3n", "temp", "debit"]

PLAUSIBLE_RANGES = {
    "ph":    (2.0, 12.0),
    "tss":   (0.0, 2000.0),
    "cod":   (0.0, 3000.0),
    "nh3n":  (0.0, 200.0),
    "temp":  (0.0, 50.0),
    "debit": (0.0, 1000.0),
}

SEVERITY_BY_TYPE = {
    "implausible": "danger",
    "flatline":    "danger",
    "spike":       "warning",
    "drift":       "warning",
}


def check_implausible(field: str, value) -> AnomalyResult | None:
    """Flag a value outside its physically plausible range."""
    rng = PLAUSIBLE_RANGES.get(field)
    if rng is None or value is None:
        return None
    lo, hi = rng
    if value < lo or value > hi:
        return AnomalyResult(
            "implausible",
            SEVERITY_BY_TYPE["implausible"],
            f"{field} {value} di luar rentang wajar {lo}–{hi}",
        )
    return None
