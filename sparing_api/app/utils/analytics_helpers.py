"""Pure analytics helpers (stdlib only): data-gap detection and debit→volume
integration. No DB or framework imports so they stay trivially unit-testable."""
from datetime import datetime


def find_data_gaps(timestamps: list[datetime], interval_seconds: int = 120,
                   gap_factor: float = 2.0) -> list[dict]:
    """Detect missing-data gaps between consecutive readings.

    `timestamps` is the list of measurement instants (any order; sorted here).
    A gap is a pair of consecutive readings more than `interval_seconds *
    gap_factor` apart — i.e. at least one expected reading is missing. The factor
    (default 2) tolerates a single late/jittered reading without flagging it.

    Returns [{gap_start, gap_end, duration_minutes, missing_estimate}] ascending,
    where missing_estimate is how many readings were expected in the gap but did
    not arrive.
    """
    ts = sorted(t for t in timestamps if t is not None)
    if len(ts) < 2 or interval_seconds <= 0:
        return []
    threshold = interval_seconds * gap_factor
    gaps = []
    for a, b in zip(ts, ts[1:]):
        delta = (b - a).total_seconds()
        if delta > threshold:
            missing = max(0, round(delta / interval_seconds) - 1)
            gaps.append({
                "gap_start": a,
                "gap_end": b,
                "duration_minutes": round(delta / 60.0, 1),
                "missing_estimate": missing,
            })
    return gaps


def integrate_volume(samples: list[tuple], max_gap_minutes: float = 15.0) -> float:
    """Integrate flow (debit, L/min) over time into a total volume in litres.

    `samples` is a list of (ts, debit) — sorted here. Uses the trapezoidal rule
    between consecutive samples. Intervals longer than `max_gap_minutes` are
    skipped: when the device was offline we must not assume flow continued across
    the gap (that would invent volume). Returns litres.
    """
    pts = sorted(((t, v) for t, v in samples if t is not None and v is not None),
                 key=lambda s: s[0])
    if len(pts) < 2:
        return 0.0
    total = 0.0
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        dt_min = (t1 - t0).total_seconds() / 60.0
        if dt_min <= 0 or dt_min > max_gap_minutes:
            continue
        total += (v0 + v1) / 2.0 * dt_min   # (L/min) * min = L
    return total
