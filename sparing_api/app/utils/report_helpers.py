from datetime import date

MONTH_NAMES = [
    "Januari","Februari","Maret","April","Mei","Juni",
    "Juli","Agustus","September","Oktober","November","Desember",
]

SYSTEM_BAKU_MUTU = {
    "ph":    {"warning_min": 6.5, "warning_max": 8.5, "danger_min": 6.0, "danger_max": 9.0, "unit": ""},
    "tss":   {"warning_min": None, "warning_max": 150,  "danger_min": None, "danger_max": 200,  "unit": "mg/L"},
    "cod":   {"warning_min": None, "warning_max": 200,  "danger_min": None, "danger_max": 300,  "unit": "mg/L"},
    "nh3n":  {"warning_min": None, "warning_max": 7,    "danger_min": None, "danger_max": 10,   "unit": "mg/L"},
    "debit": {"warning_min": 0,    "warning_max": None, "danger_min": 0,    "danger_max": None, "unit": "L/min"},
    "temp":  {"warning_min": None, "warning_max": 30,   "danger_min": None, "danger_max": 35,   "unit": "°C"},
}

PARAM_LABELS = {
    "ph": "pH", "tss": "TSS", "cod": "COD",
    "nh3n": "NH3-N", "debit": "Debit", "temp": "Temperatur",
}

REPORT_PARAMS = ["ph", "tss", "cod", "nh3n", "debit", "temp"]


def make_period_label(from_date: date, to_date: date) -> str:
    """Return 'Januari 2025' for a full calendar month, else '5 Jan – 20 Jan 2025'."""
    import calendar
    last_day = calendar.monthrange(from_date.year, from_date.month)[1]
    if (from_date.day == 1 and to_date.day == last_day
            and from_date.month == to_date.month
            and from_date.year == to_date.year):
        return f"{MONTH_NAMES[from_date.month - 1]} {from_date.year}"
    mn = MONTH_NAMES[from_date.month - 1][:3]
    mn2 = MONTH_NAMES[to_date.month - 1][:3]
    return f"{from_date.day} {mn} – {to_date.day} {mn2} {to_date.year}"


def calculate_trend(avg_first: float | None, avg_second: float | None) -> str:
    """Return 'stable', 'increasing', or 'decreasing' based on half-period comparison."""
    if avg_first is None or avg_second is None:
        return "stable"
    if avg_first == 0:
        return "stable"
    change_pct = ((avg_second - avg_first) / abs(avg_first)) * 100
    if abs(change_pct) < 5:
        return "stable"
    return "increasing" if change_pct > 0 else "decreasing"


def compliance_pct(total_with_value: int, violation_count: int) -> float:
    """Return compliance percentage given total valid readings and violation count."""
    if total_with_value == 0:
        return 100.0
    compliant = total_with_value - violation_count
    return round(compliant / total_with_value * 100, 1)


def get_baku_mutu(field: str, alert_rule) -> dict:
    """Return baku mutu dict for a field, preferring AlertRule over system defaults."""
    default = SYSTEM_BAKU_MUTU.get(field, {})
    if alert_rule:
        return {
            "min": alert_rule.danger_min,
            "max": alert_rule.danger_max,
            "unit": default.get("unit", ""),
        }
    return {
        "min": default.get("danger_min"),
        "max": default.get("danger_max"),
        "unit": default.get("unit", ""),
    }


# A gap larger than this between two consecutive violating readings ends the
# current exceedance event and starts a new one. Devices deliver a reading every
# ~2 min, so 15 min tolerates a few missed/compliant samples without splitting a
# genuinely continuous exceedance into many tiny "events".
EXCEEDANCE_GAP_MINUTES = 15


def group_exceedance_events(rows: list, gap_minutes: int = EXCEEDANCE_GAP_MINUTES) -> list:
    """Group consecutive violating readings of ONE field into exceedance events.

    `rows` is a time-ordered-ASCENDING list of (ts, value, limit_type, limit)
    where limit_type is 'above_max' or 'below_min'. A new event begins when the
    limit_type changes or the gap to the previous violating reading exceeds
    `gap_minutes`. This counts EVENTS, not rows: three consecutive exceeding
    readings are one event, not three.

    Returns a list of dicts: start_ts, end_ts, duration_minutes, peak_value,
    reading_count, limit_type, limit — ordered as encountered (ascending ts).
    """
    events: list[dict] = []
    cur: dict | None = None
    prev_ts = None
    for ts, value, limit_type, limit in rows:
        value = float(value)
        break_event = (
            cur is None
            or limit_type != cur["limit_type"]
            or (prev_ts is not None
                and (ts - prev_ts).total_seconds() / 60.0 > gap_minutes)
        )
        if break_event:
            cur = {
                "start_ts": ts, "end_ts": ts,
                "peak_value": value, "reading_count": 1,
                "limit_type": limit_type, "limit": limit,
            }
            events.append(cur)
        else:
            cur["end_ts"] = ts
            cur["reading_count"] += 1
            # peak = worst deviation: highest above a max, lowest below a min
            if limit_type == "above_max":
                cur["peak_value"] = max(cur["peak_value"], value)
            else:
                cur["peak_value"] = min(cur["peak_value"], value)
        prev_ts = ts
    for ev in events:
        ev["duration_minutes"] = round(
            (ev["end_ts"] - ev["start_ts"]).total_seconds() / 60.0, 1)
    return events


def overall_status(compliance: float) -> str:
    if compliance >= 90:
        return "good"
    if compliance >= 70:
        return "warning"
    return "danger"
