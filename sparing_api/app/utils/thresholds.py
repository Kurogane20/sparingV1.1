"""KLHK baku mutu thresholds — logs warnings on exceedance."""
from app.core.logging import logger

# Baku mutu air limbah (Permen LH No. 5/2014) & ISPU udara
LIMITS = {
    "ph":           (6.0, 9.0),   # outside range = violation
    "tss":          (None, 200),  # mg/L
    "nh3n":         (None, 10),   # mg/L
    "cod":          (None, 300),  # mg/L
    "noise":        (None, 70),   # dB(A) ambient limit
    "pm25":         (None, 65),   # µg/m³ (24h ISPU boundary)
    "pm10":         (None, 150),  # µg/m³
    "so2":          (None, 900),  # µg/m³
    "no2":          (None, 200),  # µg/m³
    "co":           (None, 10000),# µg/m³
}


def check_thresholds(site_uid: str, data) -> list[str]:
    """Return list of threshold violations and log each one."""
    violations = []

    def _check(param: str, value):
        if value is None:
            return
        limits = LIMITS.get(param)
        if limits is None:
            return
        lo, hi = limits
        exceeded = False
        if lo is not None and value < lo:
            exceeded = True
        if hi is not None and value > hi:
            exceeded = True
        if exceeded:
            msg = f"[THRESHOLD] site={site_uid} {param}={value} melebihi baku mutu {limits}"
            logger.warning(msg)
            violations.append(msg)

    for param in LIMITS:
        _check(param, getattr(data, param, None))

    return violations
