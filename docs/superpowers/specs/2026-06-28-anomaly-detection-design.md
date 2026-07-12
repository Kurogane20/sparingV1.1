# Sensor Data Quality & Anomaly Detection — Design

**Status:** Approved (brainstorming complete)
**Date:** 2026-06-28
**Author:** Kuro + Claude

## Goal

Detect sensor data-quality problems that the existing baku-mutu (compliance) alert
engine cannot catch — readings that are *abnormal or indicate a faulty sensor* even
when they sit within regulatory limits. Surface these as a new alert category and as
a per-sensor health indicator on the dashboard.

This is **Approach A**: statistical/rule-based detection now, with an architecture that
lets a lightweight ML scorer plug in later **without a schema change**. No heavy ML
(no LSTM/training pipeline) — for the four problems in scope, statistics are more
accurate, cheaper, and explainable to operators.

## Scope

**Parameters in scope:** `ph`, `tss`, `cod`, `nh3n`, `temp`, `debit`.

**Explicitly out of scope (for now):** `voltage`, `current` — the user is still
researching which power-monitoring sensors to use. The design must make it trivial to
add them later (just add config entries).

**Anomaly types detected:**

1. **Implausible value** — outside a physically sensible per-parameter range (wider
   than baku mutu).
2. **Flatline** — sensor stuck: all readings within a time window are identical
   (variance ≈ 0).
3. **Spike** — sudden jump/drop relative to the recent trend.
4. **Drift** — calibration drift: sustained slow shift of the baseline over days.

**Non-goals:** forecasting / early warning; reducing compliance-alarm volume; power
monitoring; deep learning.

## Key Decisions

- **Output: both** an alert (serious cases) **and** a dashboard health badge.
- **Email: none for now.** Data-quality alerts appear in the notification bell +
  dashboard badge only. Email can be enabled later (config flag), but is not built now.
- **Implausible handling: tighten ranges + alert, but never drop data.** Today
  `getdata.py` rejects the *entire* batch (HTTP 400) when one value is out of range,
  which can discard up to 29 good readings for one bad one. The new design treats
  tightened "plausible" ranges as a **soft flag**: the reading is **stored** and a
  data-quality alert is raised. The pre-existing hard rejects in `getdata.py` for
  genuinely impossible values (e.g. pH outside 0–14) are left as-is — we do not widen
  the set of values that cause a batch to be rejected.
- **Dedup:** do not raise the same anomaly for the same (site, field, type) more than
  once per 30 minutes (mirrors the existing alert engine's dedup window).
- **Graceful degradation:** when history is insufficient (new site, <window of data),
  history-dependent checks (spike, drift, flatline) are skipped without error or false
  positives. Implausible-range checks still run (they need only the current value).

## Architecture

New module `app/utils/anomaly_engine.py`, modeled on the existing
`app/utils/alert_engine.py` (creates its own DB session, total try/except so it can
never break ingest, fire-and-forget via `asyncio.create_task`).

Two execution paths:

1. **Realtime (on ingest)** — hooked into `getdata.py::post_data`, after `db.commit()`,
   alongside the existing `trigger_alerts(...)` call (`getdata.py:169`). Handles the
   checks that need only the latest reading + recent history pulled from the DB:
   implausible, flatline, spike.
2. **Scheduled (drift)** — a new APScheduler job registered in `app/main.py`'s
   `startup_event` next to `offline_device_check` (`main.py:163`). Handles drift, which
   needs medium-term baseline comparison. Default cadence: hourly.

### Data flow

```
POST /api/post-data (getdata.py)
  → store rows → db.commit()
  → asyncio.create_task(trigger_alerts(...))         # existing, unchanged
  → asyncio.create_task(detect_realtime(...))        # NEW
       → for each in-scope field on the latest reading:
            implausible / flatline / spike checks (history from DB)
       → if anomaly: insert Alert(category="data_quality", ...) + upsert sensor_health

APScheduler hourly (main.py)
  → detect_drift_all_sites(db)
       → per active site × field: compare recent vs baseline window
       → if drift: insert Alert(...) + upsert sensor_health

Dashboard
  → GET /sites/{uid}/sensor-health  (badge per sensor)
  → GET /alerts                     (bell; data_quality alerts shown distinctly)
```

## Data Model

### A. Extend `alerts` table (Alembic migration)

Existing columns (unchanged): `id, site_id, device_uid, field, value, threshold_type,
status, triggered_at, acknowledged_at, acknowledged_by_user_id`.

Add three columns, with server defaults so existing rows become `compliance`:

| Column | Type | Notes |
|---|---|---|
| `category` | `VARCHAR(16)` default `'compliance'` | `compliance` \| `data_quality` |
| `anomaly_type` | `VARCHAR(16)` NULL | `implausible` \| `flatline` \| `spike` \| `drift` (only for `data_quality`) |
| `detail` | `VARCHAR(255)` NULL | human-readable reason, e.g. `"pH 13.9 di luar rentang wajar 2–12"` |

For `data_quality` alerts, `threshold_type` is set to `warning` or `danger` based on
severity (reuse the existing column rather than inventing a new severity field).

Severity → `sensor_health.status` mapping: `danger → bad`, `warning → warning`, no
anomaly → `ok`. Default per-type severity: implausible = `danger`, flatline = `danger`,
spike = `warning`, drift = `warning` (tunable in `ANOMALY_CONFIG`).

### B. New table `sensor_health`

Latest health status per (site, parameter); the source for the dashboard badge.

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `site_id` | FK → sites.id, `ondelete=CASCADE`, index | |
| `field` | `VARCHAR(32)` | parameter name |
| `status` | `VARCHAR(16)` | `ok` \| `warning` \| `bad` |
| `anomaly_type` | `VARCHAR(16)` NULL | last anomaly type, if any |
| `reason` | `VARCHAR(255)` NULL | human reason text |
| `last_value` | `Float` NULL | value at last evaluation |
| `score` | `Float` NULL | **reserved for future ML scorer**; null/0 now |
| `updated_at` | `DateTime(tz)` | |

Unique constraint `(site_id, field)` → upsert on each detection.

## Components

### `anomaly_engine.py`

**Pure detection functions** (input series/value → result; no DB, no I/O — trivially
unit-testable). Each returns a small result object:
`{ is_anomaly: bool, anomaly_type: str, severity: "warning"|"danger", reason: str }`.

- `check_implausible(field, value, config) -> result | None`
  Per-parameter plausible range. Outside range → anomaly (`danger`).
- `check_flatline(samples, config) -> result | None`
  `samples` = list of `(ts, value)` within the flatline window. If the window spans
  ≥ `min_minutes` and all values are identical (or variance ≈ 0) → anomaly.
- `check_spike(value, history, config) -> result | None`
  Compute `median` and `MAD` over the trailing window. Flag if
  `|value - median| > k * MAD` **and** `|value - median| > min_abs_delta`. MAD is used
  (not mean/std) for robustness to outliers. Requires ≥ `min_points`.
- `check_drift(recent, baseline, config) -> result | None`
  Compare `mean(recent_window)` vs `mean(baseline_window)`. Flag if the relative shift
  `|recent_mean - baseline_mean| / max(|baseline_mean|, min_baseline)` exceeds
  `drift_pct` (e.g. 0.25). The `min_baseline` floor prevents tiny baselines from
  producing huge percentages. Requires both windows populated.

**Orchestration functions** (own DB session, write alerts + upsert sensor_health,
apply dedup):

- `detect_realtime(site_id, site_uid, device_uid, latest_reading)` — runs implausible,
  flatline, spike. Pulls recent history per field from `sensor_data`.
- `detect_drift_all_sites(db)` — iterates active sites × in-scope fields.

**Config** `ANOMALY_CONFIG` — a module-level dict (like `DEFAULT_ALERT_RULES`),
per-parameter, easy to tune. Starting values (tunable):

| Param | Plausible range |
|---|---|
| ph | 2 – 12 |
| tss | 0 – 2000 mg/L |
| cod | 0 – 3000 mg/L |
| nh3n | 0 – 200 mg/L |
| temp | 0 – 50 °C |
| debit | 0 – 1000 m³/j |

Shared defaults (tunable): flatline window 15 min; spike trailing window 2 h, `k = 5`,
`min_points` ~10; drift recent window 24 h vs baseline 7 days.

### Integration

- `getdata.py::post_data` — add `asyncio.create_task(detect_realtime(...))` after the
  existing `trigger_alerts` task. Pass the last stored row (parity with current
  behavior; flatline/spike/drift derive the rest from DB history).
- `main.py::startup_event` — `scheduler.add_job(_detect_drift, "interval", hours=1,
  id="anomaly_drift_check")`, with its own wrapper like `_check_offline_devices`.

### API

- `GET /sites/{uid}/sensor-health` → list of per-parameter health rows for the site.
  Respects viewer site filtering via the existing `get_viewer_site_uids` dependency
  (returns 403 if a viewer requests a site they don't own, mirroring `get_site`).
- Anomaly alerts flow through the existing `/alerts` endpoints; responses must include
  the new `category`, `anomaly_type`, `detail` fields.

### Frontend

- `SensorCard.vue` (dashboard) — small status dot (green `ok` / yellow `warning` /
  red `bad`) driven by `sensor_health` fetched per site. Tooltip shows the reason.
- `AlertDropdown.vue` — render `data_quality` alerts with a distinct icon/label
  ("Kualitas Data") so they're visually separated from compliance alerts.

## Error Handling

- All detection wrapped in total `try/except` with `logger.exception(...)`; ingest and
  the scheduler are never affected by detection failures (mirrors `trigger_alerts` and
  `check_offline_devices`).
- Fire-and-forget on ingest (`asyncio.create_task`) so ingest latency is unchanged.
- Insufficient history → checks skipped, no false positives.
- Dedup query before insert (same (site, field, category, anomaly_type) active alert
  within 30 min → skip).

## Testing (TDD)

Pure detection functions are tested with synthetic series — fast, deterministic:

- **Flatline:** identical series spanning window → flagged; varying series → not.
- **Spike:** one injected outlier → flagged; normal noise → not; series shorter than
  `min_points` → not (graceful).
- **Drift:** shifted/ramped baseline → flagged; stable series → not.
- **Implausible:** out-of-range value → flagged; in-range → not; boundary values.
- **Dedup:** second identical anomaly within 30 min → only one alert row.
- **Orchestration (lighter integration test):** `detect_realtime` writes an alert and
  upserts one `sensor_health` row for a seeded anomaly.

## Future ML Hook (Approach A → ML)

`sensor_health.score` plus the uniform detector result interface mean a future
unsupervised scorer (e.g. Isolation Forest) can be added as just another "detector"
that writes to the same `sensor_health` row and the same `data_quality` alert path —
**no schema change, no API change**. Recommended once ~2–3 months of data accumulate;
not built now.

## Amendment (2026-06-29) — burst-ingest anchoring

Real devices deliver **hourly bursts of ~30 readings spaced ~2 min apart**, not a
near-real-time stream. Server-time-anchored windows therefore never matched the
data, and only the implausible check could ever fire. Revised behavior:

- `detect_realtime` receives the **whole burst** (not just the last row); all
  windows are anchored to the newest **data** timestamp in the burst.
- Every new reading is evaluated (implausible-first, then spike vs the values
  strictly before it) via the pure, unit-tested `scan_batch`; flatline runs on
  the 15-min tail relative to the anchor. Health badge = newest reading.
- `detect_drift_all_sites` anchors windows to each site's newest data timestamp
  and skips sites with no data in the last 24 h (offline alert covers those).
- `getdata.py` defaults a missing/zero device `datetime` to ingest time instead
  of epoch 1970.

## Out of Scope / Deferred

- Email notifications for data-quality alerts (config flag, off; not built now).
- `voltage` / `current` detection (pending sensor research).
- ML scorer layer (deferred until more data).
- Per-site / per-parameter configurable thresholds in the DB (start with the
  module-level `ANOMALY_CONFIG`; YAGNI until tuning demands it).
