# Logger Monitoring — Logger App Implementation Plan (Plan 2 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the field logger (`sparing_python`, a Raspberry Pi app) emit everything the now-deployed backend can receive — a 2-minute heartbeat and a retroactively-synced lifecycle event log — so the web can see logger health and detect death within ~10 minutes. All telemetry is strictly isolated: **if telemetry fails, sensor reads and data delivery must be completely unaffected.**

**Architecture:** A new `telemetry.py` module owns all of it. It signs heartbeat/event payloads with the *same* `JWTEncoder.create_jwt(payload, secret)` HS256 helper and the *same* fetched secret (`api_client.secret_key_1`, uid `admin-LOG`) the data path already uses — no new auth, no new dependency. Events are appended to a new table in the existing `sensor_history.db` with a `synced` flag and uploaded (idempotently, keyed by a client-generated `event_uid`) on each heartbeat. A crash-vs-clean-restart marker file distinguishes power-loss/crash from a graceful stop. Pi resources are read from `/sys` and stdlib (`/proc`, `os.statvfs`) — no psutil. A `systemd ExecStopPost=` best-effort "stopped" event is the last gasp.

**Tech Stack:** Python 3 stdlib + `requests` (already a dep) + `sqlite3` (stdlib). No new packages. Target: Raspberry Pi 4 running `main.py` under `sparing.service`.

**Reference spec:** `docs/superpowers/specs/2026-07-20-logger-monitoring-design.md` (Part 1). **Backend contract (already LIVE at `https://sparingapi.mitramutiara.co.id`):**
- `POST /logger/heartbeat` body `{"token": "<jwt>"}`, JWT payload `{"uid": "<site-uid>", "status": {…}}` signed with the site secret.
- `POST /logger/events` body `{"token": "<jwt>"}`, JWT payload `{"uid": "<site-uid>", "events": [{event_uid, type, ts, severity, detail}, …]}` (batch ≤ 200; idempotent per (site, event_uid)).
- Both reject bad/absent tokens with 400 and unknown uid with 401.

**Conventions:** this plan runs in the **separate repo** `C:\Users\nurch\OneDrive\Documents\sparing_python` (git remote `Kurogane20/sparing_python`), NOT `sparingV1.1`. Python via that repo's `venv` (`venv\Scripts\python.exe` on Windows dev; `/home/mmsparing/sparing_python/venv/bin/python` on the Pi). Deploy target is the Pi over SSH (details in Task 8). The repo has no pytest harness; tests are plain `python -m unittest` on pure functions.

---

## File Structure

- Create: `telemetry.py` — heartbeat builder, event log (SQLite), sync, crash marker, resource reads. Pure/testable core + thin I/O.
- Create: `test_telemetry.py` — stdlib `unittest` for the pure functions (status builder, event dedup/serialize, sentinel-free resource parsing, crash-marker logic).
- Create: `last_gasp.py` — tiny standalone script for `ExecStopPost=` (posts one `stopped` event, short timeout, never raises).
- Modify: `main.py` — instantiate `TelemetryClient` in `AQMSWorker`, add a `_last_heartbeat` timer tick, record events at existing state-change points, all wrapped so failure can't touch the data path.
- Modify: `api_client.py` — expose a minimal `post_json(url, payload, timeout)` OR reuse existing session; expose the resolved heartbeat/events URLs. (Prefer a 1-line URL helper over duplicating request code.)
- Modify: `config.py` — derive `logger_heartbeat_url` / `logger_events_url` from `server_url_1`; add `heartbeat_interval` (default 120s).
- Modify: `sparing.service` — add `ExecStopPost=`.
- Modify: `models.py` — add a `condition_code()` accessor if needed for op_status (read-only; the payload already encodes it).

---

### Task 0: Baseline — the app imports and runs dummy mode

- [ ] **Step 1: Confirm a clean baseline**

From the `sparing_python` repo root:
```bash
venv/Scripts/python.exe -c "import main, api_client, models, config, history; print('import ok')"
```
Expected: `import ok`. If it fails on a pre-existing error, stop and report — do not build on a broken baseline. (Do NOT try to launch the GUI/`main.py` here — it needs PyQt6 + a display; import is the gate.)

---

### Task 1: Config — derive logger URLs + heartbeat interval

**Files:** Modify `config.py`

- [ ] **Step 1: Add the derived URLs and interval**

Read `config.py` first. In `ServerConfig`, `server_url_1` is
`https://sparingapi.mitramutiara.co.id/api/post-data`. Add computed URLs rather than
hard-coding the host, so a config override of `server_url_1` carries through:

In `ServerConfig`, add a helper (or in `AppConfig.__post_init__`) that derives:
```python
    @property
    def logger_heartbeat_url(self) -> str:
        # same host as server 1, logger prefix
        base = self.server_url_1.split("/api/")[0]
        return f"{base}/logger/heartbeat"

    @property
    def logger_events_url(self) -> str:
        base = self.server_url_1.split("/api/")[0]
        return f"{base}/logger/events"
```
In `TimingConfig`, add:
```python
    heartbeat_interval: int = 120  # 2 menit
```

- [ ] **Step 2: Verify**

```bash
venv/Scripts/python.exe -c "from config import config; print(config.server.logger_heartbeat_url); print(config.server.logger_events_url); print(config.timing.heartbeat_interval)"
```
Expected:
```
https://sparingapi.mitramutiara.co.id/logger/heartbeat
https://sparingapi.mitramutiara.co.id/logger/events
120
```

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "feat(telemetry): derive logger heartbeat/events URLs + heartbeat interval"
```

---

### Task 2: `telemetry.py` — pure status + resource readers (TDD)

**Files:** Create `telemetry.py`, `test_telemetry.py`

- [ ] **Step 1: Write the failing tests**

Create `test_telemetry.py`:
```python
import unittest
from telemetry import build_status, _pct_from_meminfo, _disk_pct, clamp_pct


class TestStatusBuilder(unittest.TestCase):
    def test_build_status_shape_and_values(self):
        snap = {
            "uptime_s": 3600, "logger_version": "1.4.0", "op_status": 0,
            "sensor_ok": {"ph": True, "tss": False, "debit": True, "cod": None, "nh3n": None},
            "consec_fail": 2, "internet_ok": True,
            "last_send_ok_mm": True, "last_send_ok_klhk": False,
            "buffer_depth": 12, "daily_sent": 640,
            "cpu_temp": 52.3, "cpu_pct": 18.0, "mem_pct": 41.2, "disk_pct": 63.5,
        }
        st = build_status(snap)
        self.assertEqual(st["ph_ok"], True)
        self.assertEqual(st["tss_ok"], False)
        self.assertIsNone(st["cod_ok"])
        self.assertEqual(st["op_status"], 0)
        self.assertEqual(st["buffer_depth"], 12)
        self.assertEqual(st["logger_version"], "1.4.0")
        # flattened sensor_ok, no nested dict left behind
        self.assertNotIn("sensor_ok", st)

    def test_clamp_pct(self):
        self.assertEqual(clamp_pct(-5), 0.0)
        self.assertEqual(clamp_pct(150), 100.0)
        self.assertEqual(clamp_pct(42.4), 42.4)

    def test_meminfo_parsing(self):
        sample = "MemTotal: 1000 kB\nMemAvailable: 250 kB\n"
        # 75% used
        self.assertAlmostEqual(_pct_from_meminfo(sample), 75.0, places=1)

    def test_meminfo_garbage_returns_none(self):
        self.assertIsNone(_pct_from_meminfo("nonsense"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

```bash
venv/Scripts/python.exe -m unittest test_telemetry -v
```
Expected: FAIL/ERROR — `telemetry` module or functions don't exist.

- [ ] **Step 3: Implement the pure core**

Create `telemetry.py` (this step only the pure functions; I/O in later tasks):
```python
"""Logger self-telemetry: heartbeat + lifecycle event log.

STRICT ISOLATION: nothing in this module may raise into main.py's sensor-read
or data-send path. Every public entry point swallows its own exceptions and
degrades to a no-op. Telemetry going dark must never take data delivery with it.
"""
from __future__ import annotations

import os

SENSOR_KEYS = ("ph", "tss", "debit", "cod", "nh3n")


def clamp_pct(v) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(100.0, round(v, 1)))


def build_status(snap: dict) -> dict:
    """Flatten an internal snapshot into the wire `status` dict the server expects.
    Pure: no I/O. Unknown/missing sensors stay None (tri-state)."""
    sensor_ok = snap.get("sensor_ok") or {}
    status = {
        "uptime_s": snap.get("uptime_s"),
        "logger_version": snap.get("logger_version"),
        "op_status": snap.get("op_status"),
        "consec_fail": snap.get("consec_fail"),
        "internet_ok": snap.get("internet_ok"),
        "last_send_ok_mm": snap.get("last_send_ok_mm"),
        "last_send_ok_klhk": snap.get("last_send_ok_klhk"),
        "buffer_depth": snap.get("buffer_depth"),
        "daily_sent": snap.get("daily_sent"),
        "cpu_temp": snap.get("cpu_temp"),
        "cpu_pct": snap.get("cpu_pct"),
        "mem_pct": snap.get("mem_pct"),
        "disk_pct": snap.get("disk_pct"),
    }
    for k in SENSOR_KEYS:
        status[f"{k}_ok"] = sensor_ok.get(k)
    return status


def _pct_from_meminfo(text: str):
    """Parse /proc/meminfo text → used %. Returns None on garbage."""
    total = avail = None
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            total = float(line.split()[1])
        elif line.startswith("MemAvailable:"):
            avail = float(line.split()[1])
    if not total or avail is None:
        return None
    return clamp_pct(100.0 * (total - avail) / total)


def _disk_pct(path: str = "/"):
    """Disk used % via os.statvfs. None on unsupported platforms (e.g. Windows dev)."""
    try:
        s = os.statvfs(path)
    except (OSError, AttributeError):
        return None
    total = s.f_blocks * s.f_frsize
    free = s.f_bfree * s.f_frsize
    if total <= 0:
        return None
    return clamp_pct(100.0 * (total - free) / total)


def read_cpu_temp():
    """Raspberry Pi CPU temp in °C from sysfs. None if unavailable."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read().strip()) / 1000.0, 1)
    except (OSError, ValueError):
        return None


def read_mem_pct():
    try:
        with open("/proc/meminfo") as f:
            return _pct_from_meminfo(f.read())
    except OSError:
        return None


def read_cpu_pct():
    """Best-effort load-based CPU %: 1-min loadavg / ncpu * 100. None on failure."""
    try:
        load1 = os.getloadavg()[0]
        n = os.cpu_count() or 1
        return clamp_pct(100.0 * load1 / n)
    except (OSError, AttributeError):
        return None


def read_resources() -> dict:
    """All Pi resource metrics; each independently degrades to None off-Pi."""
    return {
        "cpu_temp": read_cpu_temp(),
        "cpu_pct": read_cpu_pct(),
        "mem_pct": read_mem_pct(),
        "disk_pct": _disk_pct("/"),
    }
```

- [ ] **Step 4: Run to verify green**

```bash
venv/Scripts/python.exe -m unittest test_telemetry -v
```
Expected: all pass. (`read_resources`/`_disk_pct` return None on Windows dev — that's fine; the tested functions are the pure parsers.)

- [ ] **Step 5: Commit**

```bash
git add telemetry.py test_telemetry.py
git commit -m "feat(telemetry): pure status builder + Pi resource readers"
```

---

### Task 3: Event log in SQLite + idempotent serialization (TDD)

**Files:** Modify `telemetry.py`, `test_telemetry.py`

- [ ] **Step 1: Write the failing tests** — append to `test_telemetry.py`:

```python
import os
import tempfile
from telemetry import EventLog


class TestEventLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".db")
        self.log = EventLog(self.tmp)

    def tearDown(self):
        try:
            os.remove(self.tmp)
        except OSError:
            pass

    def test_append_and_unsynced_roundtrip(self):
        self.log.append("started", severity="info", detail="clean=false")
        self.log.append("net_down", severity="warning")
        rows = self.log.unsynced(limit=200)
        self.assertEqual(len(rows), 2)
        # each row has a client-generated unique event_uid
        uids = {r["event_uid"] for r in rows}
        self.assertEqual(len(uids), 2)
        self.assertTrue(all(r["type"] in ("started", "net_down") for r in rows))

    def test_mark_synced_removes_from_unsynced(self):
        self.log.append("started")
        self.log.append("net_up")
        rows = self.log.unsynced()
        self.log.mark_synced([r["event_uid"] for r in rows])
        self.assertEqual(self.log.unsynced(), [])

    def test_unsynced_survives_reopen(self):
        self.log.append("buffer_high")
        reopened = EventLog(self.tmp)   # simulate process restart
        self.assertEqual(len(reopened.unsynced()), 1)

    def test_append_never_raises_on_bad_db(self):
        broken = EventLog("/nonexistent-dir/telemetry.db")
        broken.append("started")   # must swallow, not raise
        self.assertEqual(broken.unsynced(), [])
```

- [ ] **Step 2: Run to verify it fails** — `EventLog` doesn't exist yet.

- [ ] **Step 3: Implement** — append to `telemetry.py`:

```python
import sqlite3
import time
import uuid


class EventLog:
    """Append-only local event store with a `synced` flag. Client-generates a
    unique `event_uid` per event (the server's idempotency key). All methods
    swallow sqlite errors — telemetry must never crash the app."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ok = self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=5)

    def _init_db(self) -> bool:
        try:
            with self._connect() as c:
                c.execute(
                    "CREATE TABLE IF NOT EXISTS telemetry_events ("
                    " event_uid TEXT PRIMARY KEY, type TEXT NOT NULL, ts INTEGER NOT NULL,"
                    " severity TEXT DEFAULT 'info', detail TEXT, synced INTEGER DEFAULT 0)"
                )
            return True
        except sqlite3.Error:
            return False

    def append(self, etype: str, severity: str = "info", detail: str = None, ts: int = None) -> None:
        if not self._ok:
            return
        try:
            with self._connect() as c:
                c.execute(
                    "INSERT INTO telemetry_events (event_uid, type, ts, severity, detail)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (uuid.uuid4().hex, etype, int(ts or time.time()), severity, detail),
                )
        except sqlite3.Error:
            pass

    def unsynced(self, limit: int = 200) -> list:
        if not self._ok:
            return []
        try:
            with self._connect() as c:
                cur = c.execute(
                    "SELECT event_uid, type, ts, severity, detail FROM telemetry_events"
                    " WHERE synced = 0 ORDER BY ts ASC LIMIT ?",
                    (limit,),
                )
                return [
                    {"event_uid": r[0], "type": r[1], "ts": r[2], "severity": r[3], "detail": r[4]}
                    for r in cur.fetchall()
                ]
        except sqlite3.Error:
            return []

    def mark_synced(self, event_uids: list) -> None:
        if not self._ok or not event_uids:
            return
        try:
            with self._connect() as c:
                c.executemany(
                    "UPDATE telemetry_events SET synced = 1 WHERE event_uid = ?",
                    [(u,) for u in event_uids],
                )
        except sqlite3.Error:
            pass

    def prune_synced(self, keep_days: int = 30) -> None:
        """Housekeeping: drop long-since-synced rows so the table can't grow forever."""
        if not self._ok:
            return
        try:
            cutoff = int(time.time()) - keep_days * 86400
            with self._connect() as c:
                c.execute("DELETE FROM telemetry_events WHERE synced = 1 AND ts < ?", (cutoff,))
        except sqlite3.Error:
            pass
```

- [ ] **Step 4: Run to verify green** — `venv/Scripts/python.exe -m unittest test_telemetry -v` → all pass.

- [ ] **Step 5: Commit**

```bash
git add telemetry.py test_telemetry.py
git commit -m "feat(telemetry): local SQLite event log with synced flag + idempotent uids"
```

---

### Task 4: Crash-vs-clean-restart marker (TDD)

**Files:** Modify `telemetry.py`, `test_telemetry.py`

- [ ] **Step 1: Write the failing tests** — append:

```python
from telemetry import RunMarker


class TestRunMarker(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mktemp(suffix=".marker")

    def tearDown(self):
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_first_ever_boot_is_treated_as_clean(self):
        m = RunMarker(self.path)
        # no marker file at all → previous_shutdown_clean True (nothing crashed)
        self.assertTrue(m.previous_shutdown_clean())
        m.mark_running()

    def test_running_marker_present_means_prior_crash(self):
        m = RunMarker(self.path)
        m.mark_running()                       # boot 1 starts
        # ... process killed without clean shutdown; marker left behind ...
        m2 = RunMarker(self.path)              # boot 2
        self.assertFalse(m2.previous_shutdown_clean())

    def test_clean_shutdown_clears_marker(self):
        m = RunMarker(self.path)
        m.mark_running()
        m.mark_clean_shutdown()
        m2 = RunMarker(self.path)
        self.assertTrue(m2.previous_shutdown_clean())
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** — append to `telemetry.py`:

```python
class RunMarker:
    """A file that exists while the process is running. If it's present at
    startup, the previous run did not shut down cleanly (crash / power loss).
    `previous_shutdown_clean()` MUST be called before `mark_running()`."""

    def __init__(self, path: str):
        self.path = path
        self._prev_present = os.path.exists(path)

    def previous_shutdown_clean(self) -> bool:
        # marker present at construction → prior run crashed; absent → clean/first boot
        return not self._prev_present

    def mark_running(self) -> None:
        try:
            with open(self.path, "w") as f:
                f.write(str(int(time.time())))
        except OSError:
            pass

    def mark_clean_shutdown(self) -> None:
        try:
            os.remove(self.path)
        except OSError:
            pass
```

- [ ] **Step 4: Run to verify green.**

- [ ] **Step 5: Commit**

```bash
git add telemetry.py test_telemetry.py
git commit -m "feat(telemetry): crash-vs-clean-restart marker"
```

---

### Task 5: `TelemetryClient` — signing + send, fully isolated (TDD for the builder)

**Files:** Modify `telemetry.py`, `test_telemetry.py`

- [ ] **Step 1: Write the failing test** (the JWT payload builder is pure; the HTTP send is smoke-tested live in Task 8) — append:

```python
from telemetry import build_heartbeat_payload, build_events_payload


class TestPayloadBuilders(unittest.TestCase):
    def test_heartbeat_payload_wraps_uid_and_status(self):
        p = build_heartbeat_payload("admin-LOG", {"buffer_depth": 3})
        self.assertEqual(p["uid"], "admin-LOG")
        self.assertEqual(p["status"]["buffer_depth"], 3)

    def test_events_payload_wraps_uid_and_list(self):
        evs = [{"event_uid": "a", "type": "started", "ts": 1}]
        p = build_events_payload("admin-LOG", evs)
        self.assertEqual(p["uid"], "admin-LOG")
        self.assertEqual(p["events"], evs)
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** — append to `telemetry.py`. The signer/sender reuses the
existing `JWTEncoder.create_jwt` and `requests`; read `api_client.py` to confirm the
static method name/signature before wiring:

```python
def build_heartbeat_payload(uid: str, status: dict) -> dict:
    return {"uid": uid, "status": status}


def build_events_payload(uid: str, events: list) -> dict:
    return {"uid": uid, "events": events}


class TelemetryClient:
    """Signs and posts heartbeat/events. Every network op is best-effort and
    time-boxed; a failure returns False and is never raised to the caller."""

    def __init__(self, uid: str, heartbeat_url: str, events_url: str, log_cb=None):
        self.uid = uid
        self.heartbeat_url = heartbeat_url
        self.events_url = events_url
        self._log = log_cb or (lambda msg: None)

    def _post_signed(self, url: str, payload: dict, secret: str, timeout: float = 8.0) -> bool:
        if not secret:
            return False
        try:
            import requests
            from api_client import JWTEncoder
            token = JWTEncoder.create_jwt(payload, secret)
            r = requests.post(url, json={"token": token}, timeout=timeout)
            return r.status_code == 200
        except Exception as e:   # noqa: BLE001 — telemetry must never raise
            self._log(f"[TELEMETRY] send failed: {e}")
            return False

    def send_heartbeat(self, status: dict, secret: str) -> bool:
        return self._post_signed(
            self.heartbeat_url, build_heartbeat_payload(self.uid, status), secret
        )

    def send_events(self, events: list, secret: str) -> bool:
        if not events:
            return True
        return self._post_signed(
            self.events_url, build_events_payload(self.uid, events), secret
        )
```

- [ ] **Step 4: Run to verify green.**

- [ ] **Step 5: Commit**

```bash
git add telemetry.py test_telemetry.py
git commit -m "feat(telemetry): signed heartbeat/events client (isolated, best-effort)"
```

---

### Task 6: Wire telemetry into `main.py` (isolated)

**Files:** Modify `main.py`

No unit test here (the worker needs sensors/GUI); correctness rests on the isolation
guarantee + the live smoke test in Task 8. Read `AQMSWorker.__init__` and `_run_loop`
first.

- [ ] **Step 1: Construct telemetry in `AQMSWorker.__init__`**

After `self.history = SensorHistory()` etc., add (all guarded):
```python
        # --- self-telemetry (fully isolated: never affects the data path) ---
        try:
            from telemetry import TelemetryClient, EventLog, RunMarker, read_resources
            self._telemetry = TelemetryClient(
                config.server.uid_1,
                config.server.logger_heartbeat_url,
                config.server.logger_events_url,
                log_cb=lambda m: signal_bridge.log_entry.emit(m),
            )
            self._event_log = EventLog("telemetry_events.db")
            self._run_marker = RunMarker("logger_running.marker")
            self._prev_clean = self._run_marker.previous_shutdown_clean()
            self._run_marker.mark_running()
            self._event_log.append(
                "started", severity="info",
                detail=f"previous_shutdown_clean={self._prev_clean}",
            )
            self._last_heartbeat = 0
            self._start_time = time.time()
            self._read_resources = read_resources
        except Exception as e:   # telemetry init must not stop the worker
            print(f"[WARN] telemetry init failed (continuing without it): {e}")
            self._telemetry = None
```

- [ ] **Step 2: Add a heartbeat tick to the loop**

In `_run_loop`'s `while self.running:` body, after the sensor-read block, add:
```python
            # Self-telemetry heartbeat (isolated — wrapped so it can never
            # interrupt sensor reads or sending)
            if self._telemetry is not None and \
               current_time - self._last_heartbeat >= config.timing.heartbeat_interval:
                self._last_heartbeat = current_time
                try:
                    self._emit_heartbeat()
                except Exception as e:   # noqa: BLE001
                    print(f"[WARN] heartbeat tick failed: {e}")
```

- [ ] **Step 3: Add `_emit_heartbeat` + a helper to snapshot state**

Add methods to `AQMSWorker`:
```python
    def _current_sensor_ok(self) -> dict:
        """Latest per-sensor read status from the most recent SensorData, if any."""
        last = self.data_buffer.data[-1] if self.data_buffer.data else None
        if last is None:
            return {}
        return {"ph": last.ph_ok, "tss": last.tss_ok, "debit": last.debit_ok,
                "cod": last.cod_ok, "nh3n": last.nh3n_ok}

    def _emit_heartbeat(self):
        from telemetry import build_status
        from models import OperationalState
        res = self._read_resources()
        snap = {
            "uptime_s": int(time.time() - self._start_time),
            "logger_version": getattr(config, "VERSION", "unknown"),
            "op_status": int(OperationalState.get()),
            "sensor_ok": self._current_sensor_ok(),
            "consec_fail": self._consec_fail,
            "internet_ok": bool(self._internet_connected),
            "last_send_ok_mm": getattr(self, "_last_send_ok_mm", None),
            "last_send_ok_klhk": getattr(self, "_last_send_ok_klhk", None),
            "buffer_depth": len(self.data_buffer.data),
            "daily_sent": self.daily_sent_count,
            **res,
        }
        secret = self.api_client.secret_key_1
        # push any unsynced events first, then the heartbeat
        pending = self._event_log.unsynced(limit=200)
        if pending and self._telemetry.send_events(pending, secret):
            self._event_log.mark_synced([e["event_uid"] for e in pending])
        self._telemetry.send_heartbeat(snap, secret)
```
(If `_last_send_ok_mm`/`_klhk` don't exist yet, set them where `send_all_data`'s
result is handled — a one-line assignment each — so per-server send status is real.
If that's more than a trivial touch, leave them as `None` for this task and note it.)

- [ ] **Step 4: Record events at existing state-change points**

At the connection-flip in `_check_connection` (where `self._internet_connected`
changes), append `net_down`/`net_up` via `self._event_log` (guarded with
`if getattr(self, "_event_log", None)`). Do the same for a graceful stop in `stop()`:
`self._event_log.append("stopping"); self._run_marker.mark_clean_shutdown()`.
Keep each addition tiny and guarded; do NOT restructure existing logic.

- [ ] **Step 5: Verify import + a dry construction**

```bash
venv/Scripts/python.exe -c "import ast; ast.parse(open('main.py').read()); print('main.py parses')"
venv/Scripts/python.exe -m unittest test_telemetry -v
```
Expected: `main.py parses`, telemetry unit tests still green. (Full `main.py` run needs the Pi.)

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "feat(telemetry): emit heartbeat + lifecycle events from the worker (isolated)"
```

---

### Task 7: Last gasp (`ExecStopPost`) + service file

**Files:** Create `last_gasp.py`; modify `sparing.service`

- [ ] **Step 1: Create `last_gasp.py`**

A standalone best-effort "stopped" event, run by systemd on stop:
```python
"""ExecStopPost hook: post a single 'stopped' logger event, best-effort.

Runs as its own short-lived process when the service stops (graceful or crash-
after-restart). If power/network are gone it simply fails silently and the
server's dead-man's switch reports the outage instead."""
import sys
import time
import uuid

try:
    import requests
    from config import config
    from api_client import JWTEncoder, APIClient

    api = APIClient()
    api.fetch_all_secret_keys()
    secret = api.secret_key_1
    if secret:
        payload = {"uid": config.server.uid_1, "events": [{
            "event_uid": uuid.uuid4().hex, "type": "stopped",
            "ts": int(time.time()), "severity": "info",
            "detail": "service stop",
        }]}
        token = JWTEncoder.create_jwt(payload, secret)
        requests.post(config.server.logger_events_url, json={"token": token}, timeout=5)
except Exception:
    pass
sys.exit(0)
```

- [ ] **Step 2: Add `ExecStopPost` to `sparing.service`**

In the `[Service]` block, after `ExecStart=`, add:
```ini
# Best-effort "stopped" event on shutdown (works only if power/network survive;
# otherwise the server-side dead-man's switch reports the outage).
ExecStopPost=/home/mmsparing/sparing_python/venv/bin/python /home/mmsparing/sparing_python/last_gasp.py
```
Leave `Restart=always` / `RestartSec=10` unchanged.

- [ ] **Step 3: Verify syntax**

```bash
venv/Scripts/python.exe -c "import ast; ast.parse(open('last_gasp.py').read()); print('ok')"
```

- [ ] **Step 4: Commit**

```bash
git add last_gasp.py sparing.service
git commit -m "feat(telemetry): systemd ExecStopPost last-gasp stopped event"
```

---

### Task 8: Deploy to the Pi + live end-to-end verification

The backend is already live, so a real heartbeat can be verified reaching production.

- [ ] **Step 1: Push the logger repo**

```bash
git push origin main
```

- [ ] **Step 2: Deploy to the Pi** (SSH; the app runs under `sparing.service`)

The Pi's exact SSH alias/host is operator-provided — do NOT assume `mitramutiara-prod`
(that is the API server, a different machine). Ask the user for the logger Pi's SSH
target if unknown. Then:
```bash
ssh <logger-pi> "cd /home/mmsparing/sparing_python && git pull && sudo cp sparing.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl restart sparing"
```
Expected: service restarts cleanly; `systemctl status sparing` shows `active (running)`.

- [ ] **Step 3: Confirm the heartbeat reaches prod**

Within ~2 minutes of restart, from any machine with an operator token:
```bash
TOKEN=$(curl -s -X POST https://sparingapi.mitramutiara.co.id/auth/login \
  -H 'Content-Type: application/json' -d "{\"email\":\"$SPARING_EMAIL\",\"password\":\"$SPARING_PASS\"}" | jq -r .access_token)
curl -s -H "Authorization: Bearer $TOKEN" https://sparingapi.mitramutiara.co.id/logger/status | jq '.[] | {site_uid, state, minutes_since_heartbeat, logger_version, buffer_depth}'
```
Expected: the logger's site shows `state: "alive"`, a small `minutes_since_heartbeat`,
and a `started` event visible via `GET /logger/events`.

- [ ] **Step 4: Confirm a `started` event with crash detage**

```bash
curl -s -H "Authorization: Bearer $TOKEN" "https://sparingapi.mitramutiara.co.id/logger/events?type=started" | jq '.[0] | {type, detail, ts}'
```
Expected: a `started` event whose `detail` carries `previous_shutdown_clean=…`.

- [ ] **Step 5: Report** the live status and hand off to Plan 3 (the `/loggers` web page).

---

## Self-Review Notes

- **Spec coverage (Part 1):** §1.1 heartbeat → Tasks 1,2,5,6; §1.2 event log + retro sync
  → Tasks 3,6 (unsynced pushed before each heartbeat, marked synced on 200); §1.3 crash
  marker → Task 4 (+ wired in Task 6); §1.4 last gasp → Task 7. Resource reads (spec's Pi
  metrics) → Task 2.
- **Isolation guarantee (the spec's hard requirement):** every telemetry entry point in
  `main.py` is wrapped in try/except; `TelemetryClient._post_signed` catches `Exception`;
  `EventLog`/`RunMarker` swallow all `sqlite`/`OSError`. Telemetry init failure sets
  `self._telemetry = None` and the loop simply skips the tick. There is no code path where
  a telemetry error propagates into `_read_sensors` or `send_all_data`.
- **Auth reuse:** signs with `JWTEncoder.create_jwt` + `api_client.secret_key_1` + uid
  `admin-LOG` — identical to the data path; no new secret, no PyJWT (the server accepts the
  hand-rolled HS256 already).
- **No new dependency:** stdlib (`sqlite3`, `uuid`, `os`) + existing `requests`.
- **Idempotency:** client generates `event_uid` (uuid4); re-uploads after a flaky link are
  deduped server-side per (site, event_uid) — the backend fix already shipped in Plan 1.
- **Deferred:** Plan 3 (frontend `/loggers` page, dashboard chip, Alarm category filter,
  History "Kalibrasi" badge). The `_last_send_ok_mm/_klhk` wiring is best-effort in Task 6;
  if non-trivial it degrades to `None` without blocking.
```
