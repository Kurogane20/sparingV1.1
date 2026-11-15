"""Logger diagnosis: what is wrong with a field logger, in words people can act on.

Pure functions, no I/O (logger-diagnosis spec, Bagian 2). logger_incidents
gathers the inputs from the database and stores what this module decides.

Every finding has three layers, cut per role by cut_for_role:
  title  - plain language, for everyone (clients included);
  action - what to do, for operators and admins;
  tech   - codes, uids and payloads, for admins only.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.utils.local_day import site_utc_offset
from app.utils.time import as_utc

utc = as_utc   # re-exported: logger_incidents and the API normalise datetimes through this module

DOWN_AFTER = timedelta(minutes=10)          # same silence threshold as logger_monitor
RECENT = timedelta(hours=2)                 # refusals/acceptances that count as "now" (bursts are hourly)
SETTLED_AFTER = timedelta(minutes=30)       # refusals that stopped this long before the last acceptance: the cause was fixed
DATA_RECENT = timedelta(hours=3)
SEND_FAIL_AFTER = timedelta(hours=3)
SENSOR_FAIL_AFTER = timedelta(minutes=15)   # same as logger_monitor.SENSOR_FAIL_MINUTES
UNSTABLE_RESTARTS = 3
DISK_HIGH, DISK_OK = 90.0, 85.0
TEMP_HIGH, TEMP_OK = 80.0, 75.0
CONCURRENT_SITES = 3                        # silent together (this one included) -> server side
CONCURRENT_WINDOW = timedelta(minutes=10)
EVIDENCE_SLACK = timedelta(minutes=15)
FUTURE_SKEW = timedelta(minutes=10)

UNCLEAN_START = "previous_shutdown_clean=false"   # compared lower-cased: the Pi sends "False"
CODE_ORDER = ("down", "rejected", "rejected_partial", "no_telemetry", "send_fail_mm",
              "send_fail_klhk", "unstable_power", "sensor", "device_disk", "device_temp")
# Judged from the heartbeat: while the logger is not reporting they can be
# neither confirmed nor cleared, so their incidents stay as they are.
ALIVE_ONLY_KINDS = frozenset({"send_fail_mm", "send_fail_klhk", "unstable_power", "device_disk", "device_temp"})
STATE_ORDER = {"down": 0, "problem": 1, "attention": 2, "unknown": 3, "normal": 4}
REASON_TEXT = {
    "bad_signature": "kunci logger tidak cocok",
    "expired": "token kedaluwarsa (paket lama atau jam logger salah)",
    "unknown_uid": "uid logger belum terdaftar di web",
}
FORMAT_TEXT = "format kiriman tidak dikenali"   # malformed, no_uid, missing_token, bad_data
REASON_ACTION = {
    "bad_signature": "Tim MM: atur ulang kunci atau uid logger. Operator tidak perlu ke lokasi.",
    "unknown_uid": "Tim MM: atur ulang kunci atau uid logger. Operator tidak perlu ke lokasi.",
    "expired": "Tim MM: periksa jam logger dan antrean kiriman. Operator tidak perlu ke lokasi.",
}
FORMAT_ACTION = "Tim MM: periksa versi aplikasi logger. Operator tidak perlu ke lokasi."
SENSOR_NAMES = {"ph": "pH", "tss": "TSS", "debit": "Debit", "cod": "COD", "nh3n": "NH₃-N"}
# What each role may see (an allowlist: a field added to the row later stays hidden).
ROW_KEYS = ("site_uid", "site_name", "timezone", "state", "headline", "since",
            "last_heartbeat_at", "last_data_at")
FINDING_KEYS = ("code", "kind", "severity", "since", "title")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")


@dataclass
class SiteInputs:
    """Everything the diagnosis of one site needs, already read from the database."""
    site_id: int
    uid: str
    name: str
    timezone: str = "Asia/Jakarta"
    status: dict | None = None               # logger_status columns; None = never sent a heartbeat
    last_data_ts: datetime | None = None     # newest sensor_data.ts (logger clock: display only)
    last_ingest_at: datetime | None = None   # sites.last_ingest_at: last accepted post-data (server clock)
    events: list = field(default_factory=list)       # {"type", "ts", "detail", "received_at"}
    rejections: list = field(default_factory=list)   # {"source", "reason", "first_at", "last_at", "count", "last_detail"}
    open_kinds: set = field(default_factory=set)     # kinds with an open incident (hysteresis)
    concurrent_down: int = 1                 # silent loggers (this one included) within +-10 min


# ── text helpers ────────────────────────────────────────────────────────

def iso(dt: datetime | None) -> str | None:
    return None if dt is None else utc(dt).isoformat()


def local_text(dt: datetime, tz_name: str, now: datetime) -> str:
    """'10:12' today, '1 Nov 10:12' this year, '1 Nov 2025 10:12' otherwise, on the site's clock."""
    dt, now = utc(dt), utc(now)
    local = dt + site_utc_offset(tz_name, dt)
    today = now + site_utc_offset(tz_name, now)
    clock = f"{local:%H:%M}"
    if local.date() == today.date():
        return clock
    day = f"{local.day} {_MONTHS[local.month - 1]}"
    return f"{day} {clock}" if local.year == today.year else f"{day} {local.year} {clock}"


def duration_text(minutes: float) -> str:
    total = max(0, int(round(minutes)))
    if total < 1:
        return "kurang dari 1 menit"
    days, rest = divmod(total, 1440)
    hours, mins = divmod(rest, 60)
    if days:
        return f"{days} hari {hours} jam" if hours else f"{days} hari"
    if hours:
        return f"{hours} jam {mins} menit" if mins else f"{hours} jam"
    return f"{mins} menit"


def relative_text(dt: datetime, now: datetime) -> str:
    minutes = (utc(now) - utc(dt)).total_seconds() / 60
    return "baru saja" if minutes < 1 else f"{duration_text(minutes)} lalu"


def reason_text(reason: str) -> str:
    return REASON_TEXT.get(reason, FORMAT_TEXT)


def reason_action(reason: str) -> str:
    return REASON_ACTION.get(reason, FORMAT_ACTION)


def recovered_pct(expected: int | None, recovered: int | None) -> int | None:
    if not expected:
        return None
    return min(100, round((recovered or 0) * 100 / expected))


def heartbeat_alive(inp: "SiteInputs", now: datetime) -> bool:
    hb = utc((inp.status or {}).get("last_heartbeat_at"))
    return hb is not None and utc(now) - hb <= DOWN_AFTER


# ── findings ────────────────────────────────────────────────────────────

def _finding(code: str, severity: str, title: str, action: str | None, tech: str | None,
             since: datetime | None = None, incident: bool = True) -> dict:
    return {"code": code, "kind": code if incident else None, "severity": severity,
            "since": iso(since), "title": title, "action": action, "tech": tech}


def _is_unclean_start(event: dict) -> bool:
    return event["type"] == "started" and UNCLEAN_START in (event.get("detail") or "").lower()


def _unclean_starts(events: list, since: datetime, until: datetime | None = None) -> list:
    return [e for e in events if _is_unclean_start(e) and utc(e["ts"]) >= since
            and (until is None or utc(e["ts"]) <= until)]


def _over(value: float, high: float, ok: float, already_open: bool) -> bool:
    """Raise above `high`; once raised, clear only below `ok`."""
    return value >= ok if already_open else value > high


def _number(value) -> float | None:
    """A numeric status field; bools and text are not numbers here."""
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _rejection_tech(rej: dict, tz: str, now: datetime) -> str:
    text = f"{rej['source']} · {rej['reason']} ×{rej['count']} sejak {local_text(rej['first_at'], tz, now)}"
    return f"{text} · {rej['last_detail']}" if rej.get("last_detail") else text


def _active_rejections(inp: SiteInputs, hb: datetime | None, now: datetime) -> list:
    """Recent refusals that still go on: not ones that stopped while data kept being accepted."""
    def last_accept(source: str):
        return utc(inp.last_ingest_at) if source == "post-data" else hb

    def settled(rej: dict) -> bool:
        last = last_accept(rej["source"])
        return last is not None and utc(rej["last_at"]) < last - SETTLED_AFTER

    return [r for r in inp.rejections if utc(r["last_at"]) >= now - RECENT and not settled(r)]


def _rejection_finding(inp: SiteInputs, hb: datetime | None, now: datetime) -> dict | None:
    recent = _active_rejections(inp, hb, now)
    if not recent:
        return None

    def accepted_since(rej: dict) -> bool:
        """The same path accepted data recently AND after this refusal run began."""
        last = utc(inp.last_ingest_at) if rej["source"] == "post-data" else hb
        return last is not None and last >= now - RECENT and last > utc(rej["first_at"])

    refused = [r for r in recent if not accepted_since(r)]
    group = refused or recent
    pick = max(group, key=lambda r: utc(r["last_at"]))
    since = min(utc(r["first_at"]) for r in group)
    tech = _rejection_tech(pick, inp.timezone, now)
    if refused:
        return _finding("rejected", "danger",
                        f"Logger mengirim data, tetapi server menolaknya: {reason_text(pick['reason'])}.",
                        reason_action(pick["reason"]), tech, since=since)
    return _finding("rejected_partial", "warning",
                    f"Sebagian kiriman ditolak server ({reason_text(pick['reason'])}); data baru tetap masuk.",
                    "Tim MM: periksa antrean kiriman di logger; ada paket lama yang terus ditolak.",
                    tech, since=since)


def _telemetry_finding(inp: SiteInputs, hb: datetime | None, ingest: datetime | None, now: datetime) -> dict:
    tz = inp.timezone
    seen = local_text(hb, tz, now) if hb else "tidak pernah"
    taken = local_text(ingest, tz, now) if ingest else "—"
    return _finding("no_telemetry", "warning",
                    "Data masuk, tetapi kesehatan logger tidak terpantau.",
                    "Tim MM: perbarui aplikasi logger.",
                    f"heartbeat terakhir {seen} · data diterima {taken}",
                    since=hb)


def _silence_finding(inp: SiteInputs, hb: datetime | None, now: datetime,
                     rejection_code: str | None = None) -> dict | None:
    """The heartbeat stopped: telemetry only (the logger still runs), refused
    (the rejection finding explains it, so None), or down."""
    tz, st = inp.timezone, inp.status or {}
    last_data = utc(inp.last_data_ts)
    ingest = utc(inp.last_ingest_at)   # server clock: a logger clock running ahead cannot fake it
    after = hb + DOWN_AFTER if hb is not None else None

    # Data accepted after the heartbeat stopped proves the logger kept running.
    if ingest is not None and ingest >= now - DATA_RECENT and (after is None or ingest > after):
        return _telemetry_finding(inp, hb, ingest, now)
    # So does a refusal recorded after it stopped.
    late = [r for r in inp.rejections
            if utc(r["last_at"]) >= now - RECENT and (after is None or utc(r["last_at"]) > after)]
    if late:
        heartbeat_refused = any(r["source"] in ("heartbeat", "events") for r in late)
        if rejection_code == "rejected_partial" and not heartbeat_refused:
            return _telemetry_finding(inp, hb, ingest, now)
        return None   # the heartbeat itself (or every send) is refused: the rejection finding says why

    if hb is None:
        last = local_text(last_data, tz, now) if last_data else "tidak ada"
        parts = [f"Belum pernah mengirim heartbeat; data terakhir {last}."]
        # When the data stopped, on the server's clock if known; never in the future.
        since = ingest or (min(last_data, now) if last_data else None)
    else:
        parts, since = [f"Tidak melapor sejak {local_text(hb, tz, now)}."], hb
    if st.get("internet_ok") is False:
        parts.append("Internet sudah bermasalah sebelum logger hilang.")
    if hb is not None and len(_unclean_starts(inp.events, hb - timedelta(hours=24), hb + EVIDENCE_SLACK)) >= 2:
        parts.append("Logger sering mati mendadak sebelumnya.")
    together = hb is not None and inp.concurrent_down >= CONCURRENT_SITES
    if together:
        # No count in the words: it spans other clients' loggers (admins see it in tech).
        parts.append("Beberapa logger terputus bersamaan, kemungkinan gangguan di server.")
    action = ("Tim MM: periksa server." if together
              else "Cek di lokasi: logger menyala, lampu modem/internet, lalu restart logger.")
    tech = f"heartbeat terakhir {iso(hb) or '—'} · data terakhir {iso(last_data) or '—'}"
    if together:
        tech += f" · {inp.concurrent_down} logger diam dalam ±10 menit"
    return _finding("down", "danger", " ".join(parts), action, tech, since=since)


def _alive_findings(inp: SiteInputs, now: datetime) -> list:
    tz, st, out = inp.timezone, inp.status or {}, []
    mm_since = utc(st.get("mm_fail_since"))
    if mm_since is not None and now - mm_since >= SEND_FAIL_AFTER:
        depth = _number(st.get("buffer_depth"))
        queue = f" ({int(depth)} antrean)" if depth is not None else ""
        out.append(_finding("send_fail_mm", "warning",
                            f"Data tertahan di logger{queue}, akan terkirim setelah koneksi pulih.",
                            "Cek internet di lokasi.",
                            f"last_send_ok_mm=false sejak {iso(mm_since)}", since=mm_since))
    klhk_since = utc(st.get("klhk_fail_since"))
    if klhk_since is not None and now - klhk_since >= SEND_FAIL_AFTER:
        out.append(_finding("send_fail_klhk", "warning",
                            f"Kiriman ke KLHK gagal sejak {local_text(klhk_since, tz, now)}.",
                            "Tim MM: periksa uid KLHK (uid_2) di konfigurasi logger.",
                            f"last_send_ok_klhk=false sejak {iso(klhk_since)}", since=klhk_since))
    starts = _unclean_starts(inp.events, now - timedelta(hours=24))
    if len(starts) >= UNSTABLE_RESTARTS:
        out.append(_finding("unstable_power", "warning",
                            f"Logger {len(starts)}× mati mendadak dalam 24 jam, kemungkinan listrik tidak stabil.",
                            "Periksa sumber listrik atau UPS logger.",
                            "started previous_shutdown_clean=False: "
                            + ", ".join(local_text(e["ts"], tz, now) for e in starts),
                            since=min(utc(e["ts"]) for e in starts)))
    fail_since = utc(st.get("sensor_fail_since"))
    if fail_since is not None and now - fail_since >= SENSOR_FAIL_AFTER:
        for key, name in SENSOR_NAMES.items():
            if st.get(f"{key}_ok") is False:
                out.append(_finding("sensor", "warning",
                                    f"Sensor {name} gagal dibaca sejak {local_text(fail_since, tz, now)}.",
                                    f"Periksa kabel atau sensor {name}.", f"{key}_ok=false",
                                    since=fail_since, incident=False))
    disk = _number(st.get("disk_pct"))
    if disk is not None and _over(disk, DISK_HIGH, DISK_OK, "device_disk" in inp.open_kinds):
        out.append(_finding("device_disk", "warning", f"Penyimpanan logger hampir penuh ({round(disk)}%).",
                            "Tim MM: bersihkan penyimpanan logger.", f"disk_pct={disk}"))
    temp = _number(st.get("cpu_temp"))
    if temp is not None and _over(temp, TEMP_HIGH, TEMP_OK, "device_temp" in inp.open_kinds):
        out.append(_finding("device_temp", "warning", f"Logger terlalu panas ({round(temp)} °C).",
                            "Cek ventilasi panel logger.", f"cpu_temp={temp}"))
    return out


def _device(st: dict, hb) -> dict:
    return {
        "last_heartbeat_at": iso(hb), "internet_ok": st.get("internet_ok"),
        "buffer_depth": st.get("buffer_depth"), "daily_sent": st.get("daily_sent"),
        "last_send_ok_mm": st.get("last_send_ok_mm"), "last_send_ok_klhk": st.get("last_send_ok_klhk"),
        "op_status": st.get("op_status"),
        "sensors": {key: st.get(f"{key}_ok") for key in SENSOR_NAMES},
    }


def _tech(inp: SiteInputs) -> dict:
    st = inp.status or {}
    keys = ("logger_version", "uptime_s", "consec_fail", "cpu_temp", "cpu_pct", "mem_pct", "disk_pct")
    return {
        "uid": inp.uid,
        **{key: st.get(key) for key in keys},
        "rejections": [{"source": r["source"], "reason": r["reason"], "count": r["count"],
                        "first_at": iso(r["first_at"]), "last_at": iso(r["last_at"]),
                        "last_detail": r.get("last_detail")} for r in inp.rejections],
    }


def diagnose(inp: SiteInputs, now: datetime) -> dict:
    """The diagnosis row of one site: state, headline and findings, worst first."""
    now = utc(now)
    st = inp.status or {}
    hb = utc(st.get("last_heartbeat_at"))

    findings = []
    rejection = _rejection_finding(inp, hb, now)
    if rejection:
        findings.append(rejection)
    if heartbeat_alive(inp, now):
        alive_findings = _alive_findings(inp, now)
        if any(r["source"] == "post-data" for r in _active_rejections(inp, hb, now)):
            # The MM send fails because the server refuses it, not because of the internet.
            alive_findings = [f for f in alive_findings if f["code"] != "send_fail_mm"]
        findings += alive_findings
    else:
        silence = _silence_finding(inp, hb, now, rejection["code"] if rejection else None)
        if silence:
            findings.append(silence)
    findings.sort(key=lambda f: CODE_ORDER.index(f["code"]))

    if any(f["code"] == "down" for f in findings):
        state = "down"
    elif any(f["severity"] == "danger" for f in findings):
        state = "problem"
    else:
        state = "attention" if findings else "normal"
    if findings:
        headline = findings[0]["title"]
    else:
        both_ok = st.get("last_send_ok_mm") is True and st.get("last_send_ok_klhk") is True
        headline = (f"Normal: melapor {relative_text(hb, now)}"
                    + (", kirim ke MM & KLHK berhasil." if both_ok else "."))
    return {
        "site_uid": inp.uid, "site_name": inp.name, "timezone": inp.timezone,
        "state": state, "headline": headline,
        "since": findings[0]["since"] if findings else None,
        "last_heartbeat_at": iso(hb), "last_data_at": iso(inp.last_data_ts),
        "findings": findings,
        "device": _device(st, hb) if inp.status is not None else None,
        "tech": _tech(inp),
    }


def cut_for_role(row: dict, role: str) -> dict:
    """admin: everything; operator: + actions and device; anyone else: words only.
    An allowlist, so a field added to the row later never reaches a viewer."""
    if role == "admin":
        return {**row, "findings": [dict(f) for f in row.get("findings", [])]}
    operator = role == "operator"
    row_keys = ROW_KEYS + (("device",) if operator else ())
    finding_keys = FINDING_KEYS + (("action",) if operator else ())
    out = {key: row[key] for key in row_keys if key in row}
    out["findings"] = [{key: f[key] for key in finding_keys if key in f} for f in row.get("findings", [])]
    return out


def sort_key(row: dict):
    return (STATE_ORDER.get(row["state"], 9), (row.get("site_name") or "").lower())


def unknown_row(inp: SiteInputs) -> dict:
    return {"site_uid": inp.uid, "site_name": inp.name, "timezone": inp.timezone,
            "state": "unknown", "headline": "Diagnosis gagal dimuat.", "since": None,
            "last_heartbeat_at": None, "last_data_at": None, "findings": []}


# ── causes of ended incidents ───────────────────────────────────────────

def evidence_events(events: list, start: datetime, end: datetime) -> list:
    """Events that may explain [start, end]: within 15 min of it and not dated
    more than 10 min after they reached the server (a clock running ahead)."""
    out = []
    for e in events:
        ts, received = utc(e["ts"]), utc(e.get("received_at"))
        if received is not None and ts > received + FUTURE_SKEW:
            continue
        if start - EVIDENCE_SLACK <= ts <= end + EVIDENCE_SLACK:
            out.append(e)
    return sorted(out, key=lambda e: utc(e["ts"]))


def _used(events: list) -> list:
    """Evidence entries: the event's id when it came from the database, its type and time."""
    return [{**({"id": e["id"]} if e.get("id") is not None else {}), "type": e["type"], "ts": iso(e["ts"])}
            for e in events]


def infer_cause(kind: str, started_at: datetime, ended_at: datetime, events: list, *,
                tz: str = "Asia/Jakarta", data_expected: int | None = None,
                data_recovered: int | None = None, concurrent: int = 1,
                ended_by: str | None = None, title: str | None = None) -> tuple[str, str, list]:
    """(cause, cause_detail, evidence) of an ended incident; the first rule that
    matches wins (spec, Bagian 2)."""
    start, end = utc(started_at), utc(ended_at)
    minutes = (end - start).total_seconds() / 60
    if ended_by == "site_inactive":
        return "site_inactive", "Lokasi dinonaktifkan; pemantauan logger dihentikan.", []
    if kind != "down":
        base = (title or "Gangguan").rstrip(".")
        return kind, f"{base}; berlangsung {duration_text(minutes)}.", []

    pct = recovered_pct(data_expected, data_recovered)
    caught_up = f"; data menyusul {pct}%" if pct is not None else ""
    if ended_by == "no_telemetry" and (pct is None or pct >= 90):
        return "telemetry_only", "Logger tetap merekam; hanya status (heartbeat) yang berhenti.", []
    if ended_by == "rejected":
        return "refused", "Logger tetap hidup; kirimannya ditolak server.", []
    if concurrent >= CONCURRENT_SITES:
        # No count in the words (they reach viewers); the evidence keeps it for admins.
        return ("server", "Gangguan di server atau jaringan pusat; beberapa logger terputus bersamaan.",
                [{"type": "concurrent", "count": concurrent}])

    ev = evidence_events(events, start, end)
    net_down = [e for e in ev if e["type"] == "net_down"]
    # The reconnect and the restart that end an outage happen after it began.
    net_up = [e for e in ev if e["type"] == "net_up" and net_down
              and utc(e["ts"]) >= max(start, utc(net_down[0]["ts"]))]
    if net_down and net_up:
        up = net_up[-1]
        down = [e for e in net_down if utc(e["ts"]) <= utc(up["ts"])][-1]   # the drop this reconnect ended
        return ("internet", f"Internet lokasi putus {duration_text(minutes)}{caught_up}.", _used([down, up]))
    crashes = [e for e in ev if _is_unclean_start(e) and utc(e["ts"]) >= start]
    if crashes:
        back = local_text(crashes[-1]["ts"], tz, end)
        return ("power_or_crash",
                f"Logger mati mendadak (listrik padam atau aplikasi crash), menyala lagi {back}{caught_up}.",
                _used(crashes))
    planned = [e for e in ev if e["type"] in ("stopping", "stopped") and utc(e["ts"]) <= start + EVIDENCE_SLACK]
    if planned:
        return "planned", f"Dimatikan dengan normal (pembaruan atau restart manual){caught_up}.", _used(planned)
    return "unknown", f"Penyebab tidak diketahui{caught_up}.", []
