"""Pure analytics helpers (stdlib only): data-gap detection, debit→volume
integration, full-series statistics, and uptime reconstruction. No DB or
framework imports so they stay trivially unit-testable."""
import statistics
from datetime import datetime


def percentile(sorted_values: list[float], p: float) -> float:
    """Linear-interpolated percentile (p in [0,100]) over an ASCENDING list.
    Matches the common 'index = p/100 * (n-1)' definition."""
    n = len(sorted_values)
    if n == 0:
        return 0.0
    if n == 1:
        return float(sorted_values[0])
    rank = (p / 100.0) * (n - 1)
    lo = int(rank)
    hi = min(lo + 1, n - 1)
    frac = rank - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def compute_stats(values: list[float]) -> dict | None:
    """Full-series statistics over ALL values (not a chart sample): count, avg,
    min, max, median, p95, p99, std_dev (sample). Returns None when empty."""
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return None
    s = sorted(vals)
    return {
        "count": len(s),
        "avg": statistics.fmean(s),
        "min": s[0],
        "max": s[-1],
        "median": percentile(s, 50),
        "p95": percentile(s, 95),
        "p99": percentile(s, 99),
        "std_dev": statistics.stdev(s) if len(s) > 1 else 0.0,
    }


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


def integrate_uptime(transitions: list[tuple], start: datetime, end: datetime,
                     initial_up: bool) -> float:
    """Fraction of [start, end] spent in the 'up' state.

    `transitions` is a list of (ts, up: bool) — each a state change AT ts (up=True
    means it came online, up=False means it went offline) — sorted ascending and
    already clipped to the window. `initial_up` is the state at `start` (from the
    last transition before the window). Returns a fraction in [0, 1]; 1.0 for a
    zero-length window.
    """
    total = (end - start).total_seconds()
    if total <= 0:
        return 1.0
    up_seconds = 0.0
    cursor = start
    state = initial_up
    for ts, up in transitions:
        if ts < start or ts > end:
            continue
        if state:
            up_seconds += (ts - cursor).total_seconds()
        cursor = ts
        state = up
    if state:
        up_seconds += (end - cursor).total_seconds()
    return max(0.0, min(1.0, up_seconds / total))


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
