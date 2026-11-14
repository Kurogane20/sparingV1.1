"""Logger diagnosis: what is wrong with a field logger, in words people can act on.

Pure functions, no I/O (logger-diagnosis spec, Bagian 2). logger_incidents
gathers the inputs from the database and stores what this module decides.

Every finding has three layers, cut per role by cut_for_role:
  title  - plain language, for everyone (clients included);
  action - what to do, for operators and admins;
  tech   - codes, uids and payloads, for admins only.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.utils.local_day import site_utc_offset

DOWN_AFTER = timedelta(minutes=10)          # same silence threshold as logger_monitor
RECENT = timedelta(hours=2)                 # refusals/acceptances that count as "now" (bursts are hourly)
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

UNCLEAN_START = "previous_shutdown_clean=False"
CODE_ORDER = ("rejected", "down", "rejected_partial", "no_telemetry", "send_fail_mm",
              "send_fail_klhk", "unstable_power", "sensor", "device_disk", "device_temp")
STATE_ORDER = {"down": 0, "problem": 1, "attention": 2, "unknown": 3, "normal": 4}
REASON_TEXT = {
    "bad_signature": "kunci logger tidak cocok",
    "expired": "token kedaluwarsa (paket lama atau jam logger salah)",
    "unknown_uid": "uid logger belum terdaftar di web",
}
FORMAT_TEXT = "format kiriman tidak dikenali"   # malformed, no_uid, missing_token, bad_data
SENSOR_NAMES = {"ph": "pH", "tss": "TSS", "debit": "Debit", "cod": "COD", "nh3n": "NH₃-N"}
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")


@dataclass
class SiteInputs:
    """Everything the diagnosis of one site needs, already read from the database."""
    site_id: int
    uid: str
    name: str
    timezone: str = "Asia/Jakarta"
    status: dict | None = None               # logger_status columns; None = never sent a heartbeat
    last_data_ts: datetime | None = None     # newest sensor_data.ts (logger clock)
    last_ingest_at: datetime | None = None   # sites.last_ingest_at: last accepted post-data (server clock)
    events: list = field(default_factory=list)       # {"type", "ts", "detail", "received_at"}
    rejections: list = field(default_factory=list)   # {"source", "reason", "first_at", "last_at", "count", "last_detail"}
    open_kinds: set = field(default_factory=set)     # kinds with an open incident (hysteresis)
    concurrent_down: int = 1                 # silent loggers (this one included) within +-10 min


# ── text helpers ────────────────────────────────────────────────────────

def utc(dt: datetime | None) -> datetime | None:
    """MySQL returns naive UTC; make every datetime aware before comparing."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


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


def recovered_pct(expected: int | None, recovered: int | None) -> int | None:
    if not expected:
        return None
    return min(100, round((recovered or 0) * 100 / expected))


# ── findings ────────────────────────────────────────────────────────────

def _finding(code, severity, title, action, tech, since=None, incident=True) -> dict:
    return {"code": code, "kind": code if incident else None, "severity": severity,
            "since": iso(since), "title": title, "action": action, "tech": tech}


def _unclean_starts(events: list, since: datetime) -> list:
    return [e for e in events
            if e["type"] == "started" and UNCLEAN_START in (e.get("detail") or "")
            and utc(e["ts"]) >= since]


def _over(value: float, high: float, ok: float, already_open: bool) -> bool:
    """Raise above `high`; once raised, clear only below `ok`."""
    return value >= ok if already_open else value > high


def _rejection_tech(rej: dict, tz: str, now: datetime) -> str:
    text = f"{rej['source']} · {rej['reason']} ×{rej['count']} sejak {local_text(rej['first_at'], tz, now)}"
    return f"{text} · {rej['last_detail']}" if rej.get("last_detail") else text


def _rejection_finding(inp: SiteInputs, hb: datetime | None, now: datetime) -> dict | None:
    recent = [r for r in inp.rejections if utc(r["last_at"]) >= now - RECENT]
    if not recent:
        return None

    def accepted_recently(source: str) -> bool:
        last = utc(inp.last_ingest_at) if source == "post-data" else hb
        return last is not None and last >= now - RECENT

    refused = [r for r in recent if not accepted_recently(r["source"])]
    pick = max(refused or recent, key=lambda r: utc(r["last_at"]))
    tech = _rejection_tech(pick, inp.timezone, now)
    if refused:
        return _finding("rejected", "danger",
                        f"Logger mengirim data, tetapi server menolaknya: {reason_text(pick['reason'])}.",
                        "Tim MM: atur ulang kunci atau uid logger. Operator tidak perlu ke lokasi.",
                        tech, since=pick["first_at"])
    return _finding("rejected_partial", "warning",
                    f"Sebagian kiriman ditolak server ({reason_text(pick['reason'])}); data baru tetap masuk.",
                    "Tim MM: periksa antrean kiriman di logger; ada paket lama yang terus ditolak.",
                    tech, since=pick["first_at"])


def _silence_finding(inp: SiteInputs, hb, last_data, rejecting: bool, now: datetime) -> dict:
    """The logger stopped reporting: telemetry only (data still arrives) or down."""
    tz, st = inp.timezone, inp.status or {}
    if hb is not None:
        # Data recorded after the heartbeat stopped proves the logger kept running;
        # the hourly burst from before it stopped proves nothing.
        data_after = last_data is not None and last_data > hb + DOWN_AFTER and last_data >= now - DATA_RECENT
    else:
        data_after = last_data is not None and last_data >= now - DATA_RECENT
    if data_after:
        seen = local_text(hb, tz, now) if hb else "tidak pernah"
        return _finding("no_telemetry", "warning",
                        "Data masuk, tetapi kesehatan logger tidak terpantau.",
                        "Tim MM: perbarui aplikasi logger.",
                        f"heartbeat terakhir {seen} · data terakhir {local_text(last_data, tz, now)}",
                        since=hb)

    if hb is None:
        last = local_text(last_data, tz, now) if last_data else "tidak ada"
        parts, since = [f"Belum pernah mengirim heartbeat; data terakhir {last}."], last_data
    else:
        parts, since = [f"Tidak melapor sejak {local_text(hb, tz, now)}."], hb
    if rejecting:
        parts.append("Logger masih mencoba mengirim, tetapi ditolak server.")
    if st.get("internet_ok") is False:
        parts.append("Internet sudah bermasalah sebelum logger hilang.")
    if hb is not None and len(_unclean_starts(inp.events, hb - timedelta(hours=24))) >= 2:
        parts.append("Logger sering mati mendadak sebelumnya.")
    together = hb is not None and inp.concurrent_down >= CONCURRENT_SITES
    if together:
        parts.append(f"{inp.concurrent_down} logger terputus bersamaan, kemungkinan gangguan di server.")
    action = ("Tim MM: periksa server." if together
              else "Cek di lokasi: logger menyala, lampu modem/internet, lalu restart logger.")
    tech = f"heartbeat terakhir {iso(hb) or '—'} · data terakhir {iso(last_data) or '—'}"
    return _finding("down", "danger", " ".join(parts), action, tech, since=since)


def _alive_findings(inp: SiteInputs, now: datetime) -> list:
    tz, st, out = inp.timezone, inp.status or {}, []
    mm_since = utc(st.get("mm_fail_since"))
    if mm_since is not None and now - mm_since >= SEND_FAIL_AFTER:
        depth = st.get("buffer_depth")
        queue = f" ({depth} antrean)" if isinstance(depth, int) else ""
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
    disk = st.get("disk_pct")
    if isinstance(disk, (int, float)) and _over(disk, DISK_HIGH, DISK_OK, "device_disk" in inp.open_kinds):
        out.append(_finding("device_disk", "warning", f"Penyimpanan logger hampir penuh ({round(disk)}%).",
                            "Tim MM: bersihkan penyimpanan logger.", f"disk_pct={disk}"))
    temp = st.get("cpu_temp")
    if isinstance(temp, (int, float)) and _over(temp, TEMP_HIGH, TEMP_OK, "device_temp" in inp.open_kinds):
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
    last_data = utc(inp.last_data_ts)
    alive = hb is not None and now - hb <= DOWN_AFTER

    findings = []
    rejection = _rejection_finding(inp, hb, now)
    if rejection:
        findings.append(rejection)
    if alive:
        findings += _alive_findings(inp, now)
    else:
        findings.append(_silence_finding(inp, hb, last_data, rejection is not None, now))
    findings.sort(key=lambda f: (f["severity"] != "danger", CODE_ORDER.index(f["code"])))

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
        "last_heartbeat_at": iso(hb), "last_data_at": iso(last_data),
        "findings": findings,
        "device": _device(st, hb) if inp.status is not None else None,
        "tech": _tech(inp),
    }


def cut_for_role(row: dict, role: str) -> dict:
    """viewer: status and words; operator: + actions and device; admin: + tech."""
    out = {**row, "findings": [dict(f) for f in row.get("findings", [])]}
    if role != "admin":
        out.pop("tech", None)
        for f in out["findings"]:
            f.pop("tech", None)
    if role not in ("admin", "operator"):
        out.pop("device", None)
        for f in out["findings"]:
            f.pop("action", None)
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
    return [{"type": e["type"], "ts": iso(e["ts"])} for e in events]


def infer_cause(kind: str, started_at: datetime, ended_at: datetime, events: list, *,
                tz: str = "Asia/Jakarta", data_expected: int | None = None,
                data_recovered: int | None = None, concurrent: int = 1,
                ended_by: str | None = None, title: str | None = None) -> tuple[str, str, list]:
    """(cause, cause_detail, evidence) of an ended incident; the first rule that
    matches wins (spec, Bagian 2)."""
    start, end = utc(started_at), utc(ended_at)
    minutes = (end - start).total_seconds() / 60
    if kind != "down":
        base = (title or "Gangguan").rstrip(".")
        return kind, f"{base}; berlangsung {duration_text(minutes)}.", []

    pct = recovered_pct(data_expected, data_recovered)
    caught_up = f"; data menyusul {pct}%" if pct is not None else ""
    if ended_by == "no_telemetry":
        return "telemetry_only", "Logger tetap merekam; hanya status (heartbeat) yang berhenti.", []
    if concurrent >= CONCURRENT_SITES:
        return ("server", f"Gangguan di server atau jaringan pusat; {concurrent} logger terputus bersamaan.", [])

    ev = evidence_events(events, start, end)
    net_down = [e for e in ev if e["type"] == "net_down"]
    net_up = [e for e in ev if e["type"] == "net_up" and net_down and utc(e["ts"]) >= utc(net_down[0]["ts"])]
    if net_down and net_up:
        return ("internet", f"Internet lokasi putus {duration_text(minutes)}{caught_up}.",
                _used([net_down[0], net_up[-1]]))
    crashes = [e for e in ev if e["type"] == "started" and UNCLEAN_START in (e.get("detail") or "")]
    if crashes:
        back = local_text(crashes[-1]["ts"], tz, end)
        return ("power_or_crash",
                f"Logger mati mendadak (listrik padam atau aplikasi crash), menyala lagi {back}{caught_up}.",
                _used(crashes))
    planned = [e for e in ev if e["type"] in ("stopping", "stopped") and utc(e["ts"]) <= start + EVIDENCE_SLACK]
    if planned:
        return "planned", f"Dimatikan dengan normal (pembaruan atau restart manual){caught_up}.", _used(planned)
    return "unknown", f"Penyebab tidak diketahui{caught_up}.", []
