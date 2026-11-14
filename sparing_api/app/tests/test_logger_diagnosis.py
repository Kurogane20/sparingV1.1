from datetime import datetime, timedelta, timezone

from app.utils.logger_diagnosis import (
    SiteInputs, cut_for_role, diagnose, duration_text, heartbeat_alive, infer_cause, local_text, sort_key,
    unknown_row,
)

NOW = datetime(2026, 11, 4, 3, 0, tzinfo=timezone.utc)          # 10:00 WIB


def _inp(**kw):
    base = dict(site_id=1, uid="LOG-1", name="Lokasi", timezone="Asia/Jakarta")
    base.update(kw)
    return SiteInputs(**base)


def _alive(**status):
    return {"last_heartbeat_at": NOW - timedelta(minutes=1), "internet_ok": True,
            "last_send_ok_mm": True, "last_send_ok_klhk": True, **status}


def _unclean(minutes_ago):
    return {"type": "started", "ts": NOW - timedelta(minutes=minutes_ago),
            "detail": "previous_shutdown_clean=False", "received_at": NOW}


def test_text_helpers():
    assert local_text(datetime(2026, 11, 1, 3, 12, tzinfo=timezone.utc), "Asia/Jakarta", NOW) == "1 Nov 10:12"
    assert local_text(NOW, "Asia/Jakarta", NOW) == "10:00"
    assert local_text(datetime(2025, 11, 1, 3, 12, tzinfo=timezone.utc), "Asia/Jakarta", NOW) == "1 Nov 2025 10:12"
    assert local_text(NOW.replace(tzinfo=None), "Asia/Jakarta", NOW) == "10:00"     # naive = UTC
    assert duration_text(161) == "2 jam 41 menit"
    assert duration_text(1500) == "1 hari 1 jam"
    assert duration_text(120) == "2 jam"
    assert duration_text(0.4) == "kurang dari 1 menit"


def test_a_healthy_logger_is_normal():
    row = diagnose(_inp(status=_alive()), NOW)
    assert row["state"] == "normal"
    assert row["findings"] == []
    assert row["headline"] == "Normal: melapor 1 menit lalu, kirim ke MM & KLHK berhasil."


def test_a_silent_logger_is_down_with_hints():
    status = _alive(last_heartbeat_at=datetime(2026, 11, 1, 3, 12, tzinfo=timezone.utc), internet_ok=False)
    row = diagnose(_inp(status=status), NOW)
    assert row["state"] == "down"
    down = row["findings"][0]
    assert down["code"] == "down" and down["severity"] == "danger"
    assert down["title"] == "Tidak melapor sejak 1 Nov 10:12. Internet sudah bermasalah sebelum logger hilang."
    assert down["action"] == "Cek di lokasi: logger menyala, lampu modem/internet, lalu restart logger."
    assert down["since"] == "2026-11-01T03:12:00+00:00"


def test_many_loggers_silent_together_points_at_the_server():
    status = _alive(last_heartbeat_at=NOW - timedelta(minutes=30))
    down = diagnose(_inp(status=status, concurrent_down=4), NOW)["findings"][0]
    assert "Beberapa logger terputus bersamaan, kemungkinan gangguan di server." in down["title"]
    assert "4 logger diam dalam ±10 menit" in down["tech"]
    assert down["action"] == "Tim MM: periksa server."


def test_a_logger_that_never_reported():
    row = diagnose(_inp(status=None), NOW)
    assert row["state"] == "down"
    assert row["headline"] == "Belum pernah mengirim heartbeat; data terakhir tidak ada."
    assert row["device"] is None


def test_data_accepted_without_heartbeat_is_telemetry_not_down():
    no_row = diagnose(_inp(status=None, last_ingest_at=NOW - timedelta(minutes=30)), NOW)
    assert no_row["state"] == "attention"
    assert no_row["findings"][0]["code"] == "no_telemetry"
    assert no_row["headline"] == "Data masuk, tetapi kesehatan logger tidak terpantau."

    stopped = _alive(last_heartbeat_at=NOW - timedelta(hours=2))
    after = diagnose(_inp(status=stopped, last_ingest_at=NOW - timedelta(minutes=30)), NOW)
    assert after["findings"][0]["code"] == "no_telemetry"

    # The hourly burst accepted before the heartbeat stopped proves nothing: still down.
    quiet = _alive(last_heartbeat_at=NOW - timedelta(minutes=15))
    before = diagnose(_inp(status=quiet, last_ingest_at=NOW - timedelta(minutes=20)), NOW)
    assert before["findings"][0]["code"] == "down"


def test_a_clock_running_ahead_does_not_make_a_dead_logger_look_alive():
    quiet = _alive(last_heartbeat_at=NOW - timedelta(minutes=30))
    row = diagnose(_inp(status=quiet, last_data_ts=NOW + timedelta(minutes=15),
                        last_ingest_at=NOW - timedelta(minutes=40)), NOW)
    assert row["state"] == "down"


def _rejection(**kw):
    base = {"source": "post-data", "reason": "bad_signature", "first_at": NOW - timedelta(days=30),
            "last_at": NOW - timedelta(minutes=30), "count": 412,
            "last_detail": "n=30 data=2026-09-29T23:53Z..2026-09-30T00:52Z"}
    base.update(kw)
    return base


def test_all_data_refused_is_a_problem():
    row = diagnose(_inp(status=_alive(), rejections=[_rejection()],
                        last_ingest_at=NOW - timedelta(hours=5)), NOW)
    assert row["state"] == "problem"
    f = row["findings"][0]
    assert f["code"] == "rejected"
    assert f["title"] == "Logger mengirim data, tetapi server menolaknya: kunci logger tidak cocok."
    assert f["action"] == "Tim MM: atur ulang kunci atau uid logger. Operator tidak perlu ke lokasi."
    assert "bad_signature ×412" in f["tech"] and "2026-09-29T23:53Z" in f["tech"]


def test_some_data_refused_while_new_data_arrives_is_attention():
    row = diagnose(_inp(status=_alive(), rejections=[_rejection()],
                        last_ingest_at=NOW - timedelta(minutes=20)), NOW)
    assert row["state"] == "attention"
    f = row["findings"][0]
    assert f["code"] == "rejected_partial"
    assert f["title"] == "Sebagian kiriman ditolak server (kunci logger tidak cocok); data baru tetap masuk."


def test_old_refusals_are_ignored():
    row = diagnose(_inp(status=_alive(), rejections=[_rejection(last_at=NOW - timedelta(hours=3))]), NOW)
    assert row["state"] == "normal"


def test_sends_failing_for_three_hours():
    klhk = diagnose(_inp(status=_alive(last_send_ok_klhk=False, klhk_fail_since=NOW - timedelta(hours=4))), NOW)
    assert klhk["findings"][0]["code"] == "send_fail_klhk"
    assert klhk["findings"][0]["title"] == "Kiriman ke KLHK gagal sejak 06:00."
    recent = diagnose(_inp(status=_alive(last_send_ok_klhk=False, klhk_fail_since=NOW - timedelta(hours=1))), NOW)
    assert recent["state"] == "normal"
    assert recent["headline"] == "Normal: melapor 1 menit lalu."
    mm = diagnose(_inp(status=_alive(mm_fail_since=NOW - timedelta(hours=3), buffer_depth=27)), NOW)
    assert mm["findings"][0]["title"] == "Data tertahan di logger (27 antrean), akan terkirim setelah koneksi pulih."


def test_repeated_unclean_restarts_mean_unstable_power():
    three = diagnose(_inp(status=_alive(), events=[_unclean(60), _unclean(300), _unclean(900)]), NOW)
    assert three["findings"][0]["code"] == "unstable_power"
    assert three["findings"][0]["title"] == "Logger 3× mati mendadak dalam 24 jam, kemungkinan listrik tidak stabil."
    two = diagnose(_inp(status=_alive(), events=[_unclean(60), _unclean(300)]), NOW)
    assert two["state"] == "normal"


def test_a_failing_sensor_is_reported_without_an_incident():
    row = diagnose(_inp(status=_alive(cod_ok=False, sensor_fail_since=NOW - timedelta(minutes=20))), NOW)
    f = row["findings"][0]
    assert f["code"] == "sensor" and f["kind"] is None
    assert f["title"] == "Sensor COD gagal dibaca sejak 09:40."


def test_device_limits_have_hysteresis():
    assert diagnose(_inp(status=_alive(disk_pct=88)), NOW)["state"] == "normal"
    still = diagnose(_inp(status=_alive(disk_pct=88), open_kinds={"device_disk"}), NOW)
    assert still["findings"][0]["code"] == "device_disk"
    full = diagnose(_inp(status=_alive(disk_pct=91.4)), NOW)
    assert full["findings"][0]["title"] == "Penyimpanan logger hampir penuh (91%)."
    hot = diagnose(_inp(status=_alive(cpu_temp=82.2)), NOW)
    assert hot["findings"][0]["title"] == "Logger terlalu panas (82 °C)."


def test_the_worst_finding_leads():
    status = _alive(klhk_fail_since=NOW - timedelta(hours=5))
    row = diagnose(_inp(status=status, rejections=[_rejection()], last_ingest_at=NOW - timedelta(hours=5)), NOW)
    assert [f["code"] for f in row["findings"]] == ["rejected", "send_fail_klhk"]
    assert row["headline"] == row["findings"][0]["title"]


def test_content_is_cut_per_role():
    row = diagnose(_inp(status=_alive(last_heartbeat_at=NOW - timedelta(hours=1))), NOW)
    admin = cut_for_role(row, "admin")
    assert "tech" in admin and admin["device"] and admin["findings"][0]["action"] and admin["findings"][0]["tech"]
    operator = cut_for_role(row, "operator")
    assert "tech" not in operator and operator["device"]
    assert operator["findings"][0]["action"] and "tech" not in operator["findings"][0]
    viewer = cut_for_role(row, "viewer")
    assert "tech" not in viewer and "device" not in viewer
    assert set(viewer["findings"][0]) == {"code", "kind", "severity", "since", "title"}
    assert row["findings"][0]["tech"]                       # the original row is not mutated


def test_sorting_and_the_unknown_row():
    rows = [{"state": "normal", "site_name": "B"}, {"state": "down", "site_name": "Z"},
            {"state": "attention", "site_name": "a"}]
    assert [r["site_name"] for r in sorted(rows, key=sort_key)] == ["Z", "a", "B"]
    bad = unknown_row(_inp())
    assert bad["state"] == "unknown" and bad["headline"] == "Diagnosis gagal dimuat."


START = datetime(2026, 10, 29, 7, 2, tzinfo=timezone.utc)     # 14:02 WIB
END = START + timedelta(minutes=161)                          # 16:43 WIB


def _ev(kind, minutes_after_start, detail=None, received_after=0):
    ts = START + timedelta(minutes=minutes_after_start)
    return {"type": kind, "ts": ts, "detail": detail, "received_at": ts + timedelta(minutes=received_after)}


def test_internet_outage():
    events = [_ev("net_down", 1), _ev("net_up", 158)]
    cause, detail, used = infer_cause("down", START, END, events, data_expected=81, data_recovered=79)
    assert cause == "internet"
    assert detail == "Internet lokasi putus 2 jam 41 menit; data menyusul 98%."
    assert [e["type"] for e in used] == ["net_down", "net_up"]


def test_power_loss_or_crash():
    events = [_ev("started", 155, "previous_shutdown_clean=False")]
    cause, detail, _ = infer_cause("down", START, END, events, data_expected=81, data_recovered=0)
    assert cause == "power_or_crash"
    assert detail == "Logger mati mendadak (listrik padam atau aplikasi crash), menyala lagi 16:37; data menyusul 0%."


def test_planned_stop():
    cause, detail, _ = infer_cause("down", START, END, [_ev("stopping", -2), _ev("stopped", -1, "service stop")])
    assert cause == "planned"
    assert detail == "Dimatikan dengan normal (pembaruan atau restart manual)."


def test_many_loggers_at_once_and_telemetry_only_win():
    cause, detail, used = infer_cause("down", START, END, [_ev("net_down", 1), _ev("net_up", 150)], concurrent=3)
    assert (cause, detail) == ("server", "Gangguan di server atau jaringan pusat; beberapa logger terputus bersamaan.")
    assert used == [{"type": "concurrent", "count": 3}]
    cause, detail, _ = infer_cause("down", START, END, [], ended_by="no_telemetry")
    assert (cause, detail) == ("telemetry_only", "Logger tetap merekam; hanya status (heartbeat) yang berhenti.")


def test_unknown_and_untrusted_evidence():
    future = [_ev("net_down", 1, received_after=-30), _ev("net_up", 150)]   # dated 30 min after it arrived
    far = [_ev("net_down", -60), _ev("net_up", 150)]                         # outside the 15 min slack
    for events in (future, far, []):
        cause, detail, _ = infer_cause("down", START, END, events, data_expected=81, data_recovered=40)
        assert cause == "unknown"
        assert detail == "Penyebab tidak diketahui; data menyusul 49%."


def test_other_kinds_keep_their_finding():
    cause, detail, _ = infer_cause(
        "rejected", START, START + timedelta(days=3), [],
        title="Logger mengirim data, tetapi server menolaknya: kunci logger tidak cocok.")
    assert cause == "rejected"
    assert detail == "Logger mengirim data, tetapi server menolaknya: kunci logger tidak cocok; berlangsung 3 hari."


def test_reason_texts_and_actions():
    cases = {
        "bad_signature": ("kunci logger tidak cocok", "Tim MM: atur ulang kunci atau uid logger. Operator tidak perlu ke lokasi."),
        "unknown_uid": ("uid logger belum terdaftar di web", "Tim MM: atur ulang kunci atau uid logger. Operator tidak perlu ke lokasi."),
        "expired": ("token kedaluwarsa (paket lama atau jam logger salah)", "Tim MM: periksa jam logger dan antrean kiriman. Operator tidak perlu ke lokasi."),
        "malformed": ("format kiriman tidak dikenali", "Tim MM: periksa versi aplikasi logger. Operator tidak perlu ke lokasi."),
    }
    for reason, (text, action) in cases.items():
        f = diagnose(_inp(status=_alive(), rejections=[_rejection(reason=reason)],
                          last_ingest_at=NOW - timedelta(hours=5)), NOW)["findings"][0]
        assert f["title"] == f"Logger mengirim data, tetapi server menolaknya: {text}."
        assert f["action"] == action


def test_a_refusal_after_the_heartbeat_stopped_means_running_not_down():
    status = _alive(last_heartbeat_at=NOW - timedelta(hours=3))
    row = diagnose(_inp(status=status, rejections=[_rejection()], last_ingest_at=NOW - timedelta(hours=5)), NOW)
    assert [f["code"] for f in row["findings"]] == ["rejected"]
    assert row["state"] == "problem"
    assert row["since"] == (NOW - timedelta(days=30)).isoformat()


def test_a_refusal_before_the_silence_does_not_hide_down():
    status = _alive(last_heartbeat_at=NOW - timedelta(minutes=30))
    row = diagnose(_inp(status=status, rejections=[_rejection(last_at=NOW - timedelta(minutes=90))]), NOW)
    assert [f["code"] for f in row["findings"]] == ["rejected", "down"]
    assert row["state"] == "down"
    assert all("masih mencoba" not in f["title"] for f in row["findings"])


def test_partial_needs_data_accepted_after_the_refusals_began():
    just_rotated = _rejection(first_at=NOW - timedelta(minutes=20), last_at=NOW - timedelta(minutes=5))
    row = diagnose(_inp(status=_alive(), rejections=[just_rotated], last_ingest_at=NOW - timedelta(minutes=60)), NOW)
    assert row["findings"][0]["code"] == "rejected"
    heartbeat_path = _rejection(source="heartbeat", first_at=NOW - timedelta(days=1))
    row = diagnose(_inp(status=_alive(), rejections=[heartbeat_path]), NOW)
    assert row["findings"][0]["code"] == "rejected_partial"


def test_unclean_start_detail_is_matched_in_any_case():
    lower = [{**_unclean(m), "detail": "previous_shutdown_clean=false"} for m in (60, 300, 900)]
    assert diagnose(_inp(status=_alive(), events=lower), NOW)["findings"][0]["code"] == "unstable_power"


def test_the_restart_history_hint_counts_only_before_the_silence():
    hb = NOW - timedelta(hours=3)
    after = [_unclean(60), _unclean(70)]                 # after the heartbeat stopped
    row = diagnose(_inp(status=_alive(last_heartbeat_at=hb), events=after), NOW)
    assert "sering mati mendadak" not in row["headline"]
    before = [_unclean(300), _unclean(320)]              # in the 24 h before it stopped
    row = diagnose(_inp(status=_alive(last_heartbeat_at=hb), events=before), NOW)
    assert "Logger sering mati mendadak sebelumnya." in row["headline"]


def test_odd_buffer_depths():
    status = dict(mm_fail_since=NOW - timedelta(hours=4))
    yes = diagnose(_inp(status=_alive(buffer_depth=True, **status)), NOW)["findings"][0]["title"]
    assert yes == "Data tertahan di logger, akan terkirim setelah koneksi pulih."
    floats = diagnose(_inp(status=_alive(buffer_depth=27.0, **status)), NOW)["findings"][0]["title"]
    assert floats == "Data tertahan di logger (27 antrean), akan terkirim setelah koneksi pulih."


def test_temperature_hysteresis_and_heartbeat_alive():
    assert diagnose(_inp(status=_alive(cpu_temp=77), open_kinds={"device_temp"}), NOW)["findings"][0]["code"] == "device_temp"
    assert diagnose(_inp(status=_alive(cpu_temp=74), open_kinds={"device_temp"}), NOW)["state"] == "normal"
    assert heartbeat_alive(_inp(status=_alive()), NOW)
    assert not heartbeat_alive(_inp(status=None), NOW)
    assert local_text(NOW, "Asia/Jakarta", NOW) == "10:00"


def test_the_viewer_cut_is_an_allowlist():
    row = diagnose(_inp(status=_alive(last_heartbeat_at=NOW - timedelta(hours=1))), NOW)
    row["evidence"] = {"secret": 1}                      # a field added later
    viewer = cut_for_role(row, "viewer")
    assert set(viewer) == {"site_uid", "site_name", "timezone", "state", "headline", "since",
                           "last_heartbeat_at", "last_data_at", "findings"}
    assert "evidence" not in cut_for_role(row, "operator")
    assert cut_for_role(row, "admin")["evidence"] == {"secret": 1}
    assert set(cut_for_role(row, "nobody")) == set(viewer)


def test_a_restart_or_reconnect_before_the_silence_is_not_the_cause():
    early_crash = [_ev("started", -10, "previous_shutdown_clean=False")]
    assert infer_cause("down", START, END, early_crash)[0] == "unknown"
    early_net = [_ev("net_down", -12), _ev("net_up", -5)]
    assert infer_cause("down", START, END, early_net)[0] == "unknown"
    lower = [_ev("started", 155, "previous_shutdown_clean=false")]
    assert infer_cause("down", START, END, lower)[0] == "power_or_crash"


def test_the_first_matching_rule_wins():
    both = [_ev("net_down", 1), _ev("net_up", 150), _ev("started", 155, "previous_shutdown_clean=False")]
    assert infer_cause("down", START, END, both)[0] == "internet"
    crash_and_stop = [_ev("stopping", -2), _ev("started", 155, "previous_shutdown_clean=False")]
    assert infer_cause("down", START, END, crash_and_stop)[0] == "power_or_crash"
    assert infer_cause("down", START, END, [], concurrent=2)[0] == "unknown"
    late_stop = [_ev("stopping", 30)]
    assert infer_cause("down", START, END, late_stop)[0] == "unknown"
