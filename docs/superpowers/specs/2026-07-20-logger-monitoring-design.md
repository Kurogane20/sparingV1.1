# Logger Monitoring — Design

**Status:** Approved (brainstorming complete)
**Date:** 2026-07-20
**Spans two repos:** the logger app `C:\Users\nurch\OneDrive\Documents\sparing_python`
(Raspberry Pi field unit, "AQMS") and this repo `sparingV1.1` (API + web).

## Problem

The logger already knows a great deal about its own health, but **none of it leaves
the Pi**. The only payload sent is `{datetime, pH, tss, debit, cod, nh3n}`
(+ `current`/`voltage` for server 1). Consequently the web can only infer device
liveness from *data arrival*, and because devices deliver hourly bursts of ~30
readings, "offline" is detected up to **90 minutes late** and with no explanation.

Signals that exist inside the logger today and are never transmitted:

| Signal | Source in logger |
|---|---|
| Per-sensor read success (`ph_ok`, `tss_ok`, `debit_ok`, `cod_ok`, `nh3n_ok`) | `models.SensorData` |
| Consecutive total-read failures (`_consec_fail`) | `main.AQMSWorker` |
| Internet connectivity | `api_client.check_internet_connection` |
| Per-server send success/failure | `api_client.send_all_data` |
| Offline buffer depth / daily sent count | `models.SensorDataBuffer`, `AQMSWorker` |
| Process start/stop/crash (systemd `Restart=always`) | `sparing.service` |
| Pi CPU temp / resources | `main` docstring (already collected) |
| Operational status NORMAL/STOPPED/CALIBRATION/MALFUNCTION | `models.OperationalState` |

**Additional defect found during design:** when operational status ≠ NORMAL, the
logger transmits the KLHK condition code (`-1`/`-2`/`-3`) **in the parameter value
fields** (`pH: -2, tss: -2, …`, per Pasal 6.2.6.6g). The API stores those as if
they were real readings, so calibration periods corrupt charts and trip the
anomaly engine with false "implausible" alerts. Fixed as part of this work.

## Goal

Monitor everything the logger knows — **including when and why it died** — in the
web app, with logger death detected in **minutes rather than 90 minutes**.

## Key constraint

**A dead logger cannot report its own death.** Death detection is therefore three
mechanisms combined:
1. **Heartbeat + server-side dead-man's switch** — liveness inferred from silence.
2. **Last gasp** — best-effort "stopped" event on graceful stop/crash (only works
   if power and network survive).
3. **Retroactive event-log sync** — the logger stores lifecycle events locally and
   uploads them on reconnect. This is what distinguishes **"logger was dead"** from
   **"logger was alive but had no internet"** — from the server both look identical
   (silence) until the logger comes back and tells its story.

## Decisions (from brainstorming)

- Logger code can be updated easily → full instrumentation is in scope.
- Heartbeat every **2 minutes**; silence > **10 minutes** ⇒ logger down ⇒ **Alarm**
  (rides the existing mandatory-note follow-up workflow).
- Scope: sensor/Modbus health, connectivity & send queue, lifecycle & Pi resources,
  KLHK operational status + the `-1/-2/-3` storage fix.
- Storage: **Approach A — snapshot + event log** (latest status row per site, plus
  an append-only log of *changes* only). No per-heartbeat time series.
- Placement: a dedicated **`/loggers`** page under *Pemantauan*.

## Out of scope

Per-heartbeat time-series history and CPU-temp trend charts (Approach B, rejected);
remote control of the logger from the web (restart/config push); changing what is
transmitted to KLHK; SMS/WhatsApp notification of logger death (backlog C from the
UI v2 work).

---

## Part 1 — Logger changes (`sparing_python`)

New module `telemetry.py`. All telemetry work is wrapped in its own try/except and
runs independently of the sensor-read/send path: **if telemetry fails, data
delivery must be completely unaffected.**

### 1.1 Heartbeat (every 2 min)

`POST {server_1}/logger/heartbeat`, authenticated with the **existing** scheme
(`get-key` → HS256 JWT), so no new auth surface. Body:

```json
{
  "uid": "SITE-UID", "ts": 1753000000, "uptime_s": 84321,
  "logger_version": "1.4.0", "op_status": 0,
  "ph_ok": true, "tss_ok": false, "debit_ok": true, "cod_ok": null, "nh3n_ok": null,
  "consec_fail": 0,
  "internet_ok": true, "last_send_ok_mm": true, "last_send_ok_klhk": false,
  "buffer_depth": 12, "daily_sent": 640,
  "cpu_temp": 52.3, "cpu_pct": 18.0, "mem_pct": 41.2, "disk_pct": 63.5
}
```
`*_ok` are tri-state: `true` OK, `false` read failed, `null` sensor not fitted.

### 1.2 Local event log + retroactive sync

New table `events` in the existing `sensor_history.db`:
`(event_uid TEXT PRIMARY KEY, type TEXT, ts INTEGER, severity TEXT, detail TEXT, synced INTEGER DEFAULT 0)`.
`event_uid` is generated client-side (uuid4) — it is the **idempotency key** so a
re-upload can never duplicate.

Events are appended only on **state change**, never per cycle:

| Type | Emitted when | Severity |
|---|---|---|
| `started` | process boot; carries `previous_shutdown_clean` | info |
| `stopping` | SIGTERM / graceful shutdown | info |
| `sensor_fail` / `sensor_recover` | a sensor's read status flips (per sensor, in `detail`) | warning / info |
| `net_down` / `net_up` | internet check flips (`net_up` carries how many buffered rows flushed) | warning / info |
| `send_fail` | a server rejects/times out after retries (`detail`: which server) | warning |
| `opstatus_change` | OperationalState changes (`detail`: from → to) | info |
| `buffer_high` | buffer depth crosses a high-water mark | warning |

Every heartbeat also uploads unsynced events in a batch to
`POST {server_1}/logger/events`, marking them `synced=1` on HTTP 200. A logger that
was alive but offline therefore **proves** it was alive once it reconnects.

### 1.3 Crash vs clean restart

A marker file is written on graceful shutdown and removed/checked at boot. If the
marker is absent at startup, the previous run ended uncleanly (crash or power
loss), and the `started` event carries `previous_shutdown_clean: false`. This is
what answers *why* the logger died, not merely *when*.

### 1.4 Last gasp

`sparing.service` gains `ExecStopPost=` running a small script that POSTs a
`stopped` event with a short timeout (best effort). If power/network are gone, the
server-side dead-man's switch catches it instead.

---

## Part 2 — Backend (`sparing_api`)

### 2.1 Tables (migration `0009_logger_monitoring`)

**`logger_status`** — one row per site, upserted on each heartbeat:
`id`, `site_id` (FK, **unique**), `last_heartbeat_at`, `logger_version`, `uptime_s`,
`op_status`, `ph_ok`, `tss_ok`, `debit_ok`, `cod_ok`, `nh3n_ok`, `consec_fail`,
`internet_ok`, `last_send_ok_mm`, `last_send_ok_klhk`, `buffer_depth`, `daily_sent`,
`cpu_temp`, `cpu_pct`, `mem_pct`, `disk_pct`, `state` (`alive`|`down`), `state_since`.

**`logger_events`** — append-only:
`id`, `site_id` (FK), `event_uid` (**unique**), `type`, `ts` (logger clock),
`received_at` (server clock), `severity`, `detail` (TEXT).

### 2.2 Endpoints

Device-authenticated (identical signing to `/api/post-data`), and added to the
existing ingest rate-limit prefix:
- `POST /logger/heartbeat` — upsert `logger_status`; if `state` was `down`, flip to
  `alive` and auto-resolve the open logger alert.
- `POST /logger/events` — batch insert, **idempotent on `event_uid`** (duplicate
  uids are ignored, not errors).

Web-authenticated, **viewer site-scoped** (consistent with the security fixes):
- `GET /logger/status` — per-site snapshot + derived `state` + minutes since
  heartbeat.
- `GET /logger/events` — filters (site, type, severity, date range) + the
  `{items,total,page,per_page}` pagination convention when `page` is passed.

### 2.3 Dead-man's switch

Scheduler job every 2 minutes: for each active site with a `logger_status` row,
if `now - last_heartbeat_at > 10 min` and `state != 'down'` → set `state='down'`,
`state_since=now`, and create an Alert. On heartbeat return → `state='alive'` +
auto-resolve with the system note (`AUTO_RESOLVE_NOTE` pattern), so recovery is
never blocked by the mandatory-note rule.

⚠️ Two gunicorn workers run the scheduler concurrently — the job **must** use the
same idempotent/unbounded-dedup pattern already applied in `alert_engine`
(`.scalars().first()`, one active alert per (site, field)).

### 2.4 Alarm noise policy

| Condition | Alarm? |
|---|---|
| Logger silent > 10 min | ✅ `danger`, category `logger`, field `logger_down` |
| A sensor reporting `*_ok=false` on every heartbeat for > 15 min | ✅ `warning`, category `logger`, field `sensor_<name>` |
| Internet down only | ❌ status + event only (logger buffers; self-heals) |
| Restart / crash | ❌ event only (visible in the timeline) |

Category `logger` joins `compliance`/`data_quality`, so these inherit the
mandatory-note follow-up workflow automatically.

### 2.5 Operational-status storage fix (migration `0010_sensor_data_op_status`)

New nullable column `sensor_data.op_status` (SMALLINT). During ingest, when **all
present** water-quality parameters of a row carry the *same* negative sentinel
(`-1`/`-2`/`-3`), store those parameters as `NULL` and record the sentinel in
`op_status` instead. If only some parameters are negative it is **not** a sentinel
row — those values fall through to the existing `_num()` impossible-value handling
unchanged. Safe because pH/TSS/COD/NH3-N/debit can never legitimately be negative.
`current`/`voltage` are never sentinel-coded (the logger sends them verbatim) and
are left untouched.

Effects: charts no longer dive to −2; the anomaly engine skips these rows (no more
false "implausible"); compliance stats exclude them (alongside `quality_flag`);
History renders a "Kalibrasi"/"Berhenti"/"Rusak" badge. **What KLHK receives is
unchanged** — this is purely how we store it.

---

## Part 3 — Frontend

### 3.1 New page `/loggers` (sidebar group *Pemantauan*, red pill when any logger down)

- **KPI row**: Logger hidup `X/Y` · Alarm logger aktif · Event 24 jam terakhir.
- **Per-site table/cards**: state chip (Hidup/Mati + since), last heartbeat
  (relative), uptime, logger version, operational-status chip, **five sensor health
  dots** (pH/TSS/debit/COD/NH₃-N), internet chip, buffer depth, sent today, and
  mini bars for CPU temp / RAM / disk.
- **Click a site → event timeline**: chronological, icon+severity per type, e.g.
  "Logger start — shutdown sebelumnya TIDAK bersih (crash/listrik padam)". Filter by
  type/severity, paginated.

### 3.2 Integration

- **Dashboard**: a logger-health chip so status is visible without navigating.
- **Alarm page**: Kategori filter gains "Logger"; wording map for logger fields;
  bell + follow-up workflow apply automatically.
- **History**: rows with `op_status` render a badge (Kalibrasi / Berhenti / Rusak)
  instead of showing −2 values.

All reuse existing v2 components (PageHeader, badges, tables) — no new visual
language.

---

## Part 4 — Testing, migrations, rollout

### Testing
- **Backend (pytest, existing async harness):** heartbeat upsert creates/updates a
  single row per site; event batch is idempotent on repeated `event_uid`; viewer
  scoping on both GET endpoints; dead-man's switch flips state + creates exactly one
  alert (even with concurrent runs) and auto-resolves on heartbeat return with the
  system note; sentinel rows store `op_status` with NULL parameters and are excluded
  from compliance/anomaly.
- **Logger:** telemetry failures must not affect the data path (inject a failing
  heartbeat endpoint and assert sends still succeed); marker-file crash detection;
  unsynced events survive restart and sync later.
- **Frontend:** `npm run build` gate (no JS test infra).

### Migrations
`0009_logger_monitoring` (two new tables) and `0010_sensor_data_op_status` (one
nullable column) — additive and safe on existing data.

### Rollout order (cross-repo, matters)
1. **Backend first** — endpoints must exist before the logger starts calling them
   (a logger POSTing to a 404 would just log failures). Deploy + verify.
2. **Logger second** — deploy `telemetry.py` + service change to the Pi; confirm
   heartbeats arrive and the site shows `alive`.
3. **Frontend last** — `/loggers` page, dashboard chip, Alarm category, History badge.

### Risks & mitigations
- *False "logger down" from flaky field internet* → 10-minute threshold plus
  auto-resolve on return; internet-only outages deliberately do not alarm.
- *Scheduler double-run across 2 workers* → idempotent dedup pattern (§2.3).
- *Clock skew on the Pi* → server records `received_at` alongside the logger's `ts`;
  liveness is judged on `received_at`, never on logger-reported time.
- *Telemetry breaking data delivery* → strict isolation + independent try/except (§1).
