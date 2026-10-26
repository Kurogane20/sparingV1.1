from datetime import datetime, timezone, timedelta

import pytest

from app.core.security import hash_password
from app.models.models import User, Site, SensorData, AlertRule


async def _auth_headers(client, db, email="op@example.com"):
    db.add(User(name="Op", email=email, password_hash=hash_password("Secret123"),
                role="operator", is_active=True))
    await db.commit()
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _make_site(db, uid="TST-1"):
    site = Site(uid=uid, name="Test", company_name="C", is_active=True)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


def _row(site_id, ts, **vals):
    return SensorData(site_id=site_id, ts=ts,
                      created_at=datetime.now(timezone.utc), **vals)


@pytest.mark.anyio
async def test_completeness_counts_window(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    now = datetime.now(timezone.utc)
    for i in range(45):  # 45 rows inside the last 24h
        db_session.add(_row(site.id, now - timedelta(minutes=5 * i), ph=7.0))
    db_session.add(_row(site.id, now - timedelta(hours=30), ph=7.0))  # outside window
    await db_session.commit()

    res = await client.get("/stats/completeness", params={"hours": 24}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["actual"] == 45
    assert body["expected"] == 1 * 30 * 24  # sites * 30/hour * hours
    assert body["pct"] == round(45 * 100.0 / 720, 1)


@pytest.mark.anyio
async def test_completeness_excludes_op_status_rows(client, db_session):
    """#4: operational-status rows (calibration/stopped/malfunction) are not
    measurements — they must not inflate the completeness numerator. A flagged
    anomaly row IS delivered data and still counts."""
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    now = datetime.now(timezone.utc)
    db_session.add(_row(site.id, now - timedelta(minutes=10), ph=7.0))                       # real
    db_session.add(_row(site.id, now - timedelta(minutes=20), ph=999.0, quality_flag="anomaly"))  # delivered → counts
    db_session.add(_row(site.id, now - timedelta(minutes=30), ph=None, op_status=-2))        # calibration → excluded
    db_session.add(_row(site.id, now - timedelta(minutes=40), ph=8.0, op_status=-3))         # malfunction w/ stale value → excluded
    await db_session.commit()

    res = await client.get("/stats/completeness", params={"hours": 24}, headers=headers)
    body = res.json()
    assert body["actual"] == 2   # real + anomaly; the two op_status rows excluded


@pytest.mark.anyio
async def test_compliance_math_with_anomaly_exclusion(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    db_session.add(AlertRule(site_id=site.id, field="tss",
                             warning_min=None, warning_max=150.0,
                             danger_min=None, danger_max=200.0, is_active=True,
                             created_at=datetime.now(timezone.utc),
                             updated_at=datetime.now(timezone.utc)))
    now = datetime.now(timezone.utc)
    # window: 3 compliant + 1 violation + 1 flagged-anomaly violation (excluded).
    # Distinct timestamps — (site_id, ts) is now unique.
    for i, v in enumerate((50.0, 60.0, 70.0)):
        db_session.add(_row(site.id, now - timedelta(hours=1, minutes=i), tss=v))
    db_session.add(_row(site.id, now - timedelta(hours=2), tss=250.0))
    db_session.add(_row(site.id, now - timedelta(hours=3), tss=999.0, quality_flag="anomaly"))
    await db_session.commit()

    res = await client.get("/stats/compliance", params={"days": 30}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["checked"] == 4          # anomaly row excluded
    assert body["violations"] == 1
    assert body["compliance_pct"] == 75.0
    assert body["prev_pct"] == 100.0     # empty previous window counts as fully compliant
    assert body["delta_pct"] == -25.0


@pytest.mark.anyio
async def test_compliance_daily_statuses(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    db_session.add(AlertRule(site_id=site.id, field="tss",
                             warning_min=None, warning_max=150.0,
                             danger_min=None, danger_max=200.0, is_active=True,
                             created_at=datetime.now(timezone.utc),
                             updated_at=datetime.now(timezone.utc)))
    # day 1: compliant; day 2: warning-band; day 3: danger violation; day 4: no data
    db_session.add(_row(site.id, datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc), tss=50.0))
    db_session.add(_row(site.id, datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc), tss=170.0))
    db_session.add(_row(site.id, datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc), tss=250.0))
    await db_session.commit()

    res = await client.get("/stats/compliance-daily", params={"month": "2026-07"}, headers=headers)
    assert res.status_code == 200
    days = {d["date"]: d["status"] for d in res.json()["days"]}
    assert days["2026-07-01"] == "ok"
    assert days["2026-07-02"] == "warning"
    assert days["2026-07-03"] == "violation"
    assert days["2026-07-04"] == "none"
    assert len(days) >= 28


@pytest.mark.anyio
async def test_compliance_daily_bad_month_400(client, db_session):
    headers = await _auth_headers(client, db_session)
    res = await client.get("/stats/compliance-daily", params={"month": "banana"}, headers=headers)
    assert res.status_code == 400


@pytest.mark.anyio
async def test_compliance_excludes_op_status_rows(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    db_session.add(AlertRule(site_id=site.id, field="tss",
                             warning_min=None, warning_max=150.0,
                             danger_min=None, danger_max=200.0, is_active=True,
                             created_at=datetime.now(timezone.utc),
                             updated_at=datetime.now(timezone.utc)))
    now = datetime.now(timezone.utc)
    db_session.add(_row(site.id, now - timedelta(hours=1), tss=50.0))
    # calibration row with params NULL — must not be counted
    db_session.add(_row(site.id, now - timedelta(hours=2), tss=None, op_status=-2))
    # a malfunction row that still carries a stale value — must ALSO be excluded,
    # otherwise exclusion would only work by accident via the NULL check
    db_session.add(_row(site.id, now - timedelta(hours=3), tss=999.0, op_status=-3))
    await db_session.commit()

    res = await client.get("/stats/compliance", params={"days": 30}, headers=headers)
    body = res.json()
    assert body["checked"] == 1          # only the real reading
    assert body["violations"] == 0
    assert body["compliance_pct"] == 100.0


@pytest.mark.anyio
async def test_calibration_only_day_is_not_reported_compliant(client, db_session):
    """A day containing nothing but operational-status rows measured nothing —
    it must not show as 'ok' (patuh penuh) on the heatmap."""
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    db_session.add(_row(site.id, datetime(2026, 7, 5, 10, 0, tzinfo=timezone.utc),
                        tss=None, op_status=-2))
    db_session.add(_row(site.id, datetime(2026, 7, 6, 10, 0, tzinfo=timezone.utc), tss=40.0))
    await db_session.commit()

    res = await client.get("/stats/compliance-daily", params={"month": "2026-07"},
                           headers=headers)
    days = {d["date"]: d["status"] for d in res.json()["days"]}
    assert days["2026-07-05"] == "none"   # calibration-only → not compliant
    assert days["2026-07-06"] == "ok"     # real reading → compliant


@pytest.mark.anyio
async def test_completeness_scoped_to_one_site(client, db_session):
    headers = await _auth_headers(client, db_session)
    a = await _make_site(db_session, uid="ST-A")
    b = await _make_site(db_session, uid="ST-B")
    now = datetime.now(timezone.utc)
    for i in range(10):
        db_session.add(_row(a.id, now - timedelta(minutes=5 * i), ph=7.0))
    for i in range(20):
        db_session.add(_row(b.id, now - timedelta(minutes=5 * i), ph=7.0))
    await db_session.commit()

    res = await client.get("/stats/completeness", params={"hours": 24, "site_uid": "ST-A"},
                           headers=headers)
    body = res.json()
    assert body["actual"] == 10                 # only site A's rows
    assert body["expected"] == 1 * 30 * 24       # ONE site, not two


@pytest.mark.anyio
async def test_compliance_scoped_to_one_site(client, db_session):
    headers = await _auth_headers(client, db_session)
    a = await _make_site(db_session, uid="SC-A")
    b = await _make_site(db_session, uid="SC-B")
    for site in (a, b):
        db_session.add(AlertRule(site_id=site.id, field="tss",
                                 warning_min=None, warning_max=150.0,
                                 danger_min=None, danger_max=200.0, is_active=True,
                                 created_at=datetime.now(timezone.utc),
                                 updated_at=datetime.now(timezone.utc)))
    now = datetime.now(timezone.utc)
    # A: all compliant; B: all violations
    db_session.add(_row(a.id, now - timedelta(hours=1), tss=50.0))
    db_session.add(_row(b.id, now - timedelta(hours=1), tss=250.0))
    await db_session.commit()

    res = await client.get("/stats/compliance", params={"days": 30, "site_uid": "SC-A"},
                           headers=headers)
    body = res.json()
    assert body["checked"] == 1
    assert body["violations"] == 0
    assert body["compliance_pct"] == 100.0       # site A only, not dragged down by B


@pytest.mark.anyio
async def test_completeness_window_starts_at_date_from(client, db_session):
    """When date_from is given, the window starts there (e.g. today 00:00 WIB)
    and the target covers only the time elapsed since then — a full-day target
    read 42% at 10:00 for a station that had delivered every reading."""
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=3)
    db_session.add(_row(site.id, now - timedelta(hours=1), ph=7.0))       # after
    db_session.add(_row(site.id, now - timedelta(hours=2), ph=7.0))       # after
    db_session.add(_row(site.id, now - timedelta(minutes=30), ph=7.0))    # after
    db_session.add(_row(site.id, now - timedelta(hours=5), ph=7.0))       # before → excluded
    db_session.add(_row(site.id, now - timedelta(hours=6), ph=7.0))       # before → excluded
    await db_session.commit()

    res = await client.get("/stats/completeness",
                           params={"hours": 24, "date_from": cutoff.isoformat()}, headers=headers)
    body = res.json()
    assert body["actual"] == 3                # only rows at/after date_from
    assert body["expected"] == 1 * 30 * 3     # 3 h elapsed since date_from
    assert body["pct"] == round(3 * 100.0 / 90, 1)
    # The full-window target and the moment of calculation, for the day-progress bar.
    assert body["expected_total"] == 1 * 30 * 24
    assert datetime.fromisoformat(body["as_of"]) >= now


def test_expected_readings_follow_elapsed_time():
    from app.api.routers.stats import expected_readings
    now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)

    assert expected_readings(now - timedelta(hours=10), now, max_hours=24) == 300
    assert expected_readings(now - timedelta(hours=30), now, max_hours=24) == 720
    assert expected_readings(now + timedelta(minutes=5), now, max_hours=24) == 0


@pytest.mark.anyio
async def test_compliance_daily_uses_the_sites_calendar_day(client, db_session):
    """A breach at 03:00 WIB on 3 Jul is 20:00 UTC on 2 Jul — it belongs to 3 Jul."""
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)  # Asia/Jakarta (WIB, UTC+7)
    db_session.add(AlertRule(site_id=site.id, field="tss", warning_max=150.0, danger_max=200.0,
                             is_active=True, created_at=datetime.now(timezone.utc),
                             updated_at=datetime.now(timezone.utc)))
    db_session.add(_row(site.id, datetime(2026, 7, 2, 20, 0, tzinfo=timezone.utc), tss=250.0))
    # 1 Jul 01:00 WIB is still 30 Jun in UTC: it belongs to July in WIB.
    db_session.add(_row(site.id, datetime(2026, 6, 30, 18, 0, tzinfo=timezone.utc), tss=40.0))
    # 1 Aug 01:00 WIB is 31 Jul in UTC: it is not July any more.
    db_session.add(_row(site.id, datetime(2026, 7, 31, 18, 0, tzinfo=timezone.utc), tss=250.0))
    await db_session.commit()

    res = await client.get("/stats/compliance-daily", params={"month": "2026-07"}, headers=headers)

    days = {d["date"]: d["status"] for d in res.json()["days"]}
    assert days["2026-07-03"] == "violation"
    assert days["2026-07-02"] == "none"
    assert days["2026-07-01"] == "ok"
    assert days["2026-07-31"] == "none"


@pytest.mark.anyio
async def test_compliance_daily_follows_each_sites_own_timezone(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = Site(uid="WITA-1", name="Makassar", company_name="C", timezone="Asia/Makassar", is_active=True)
    db_session.add(site)
    await db_session.commit()
    # 16:30 UTC = 23:30 WIB but 00:30 WITA the next day.
    db_session.add(_row(site.id, datetime(2026, 7, 9, 16, 30, tzinfo=timezone.utc), tss=40.0))
    await db_session.commit()

    res = await client.get("/stats/compliance-daily", params={"month": "2026-07"}, headers=headers)

    days = {d["date"]: d["status"] for d in res.json()["days"]}
    assert days["2026-07-10"] == "ok"
    assert days["2026-07-09"] == "none"


@pytest.mark.anyio
async def test_compliance_daily_can_be_scoped_to_one_site(client, db_session):
    headers = await _auth_headers(client, db_session)
    site_a = await _make_site(db_session, uid="CD-A")
    site_b = await _make_site(db_session, uid="CD-B")
    for site in (site_a, site_b):
        db_session.add(AlertRule(site_id=site.id, field="tss",
                                 warning_min=None, warning_max=150.0,
                                 danger_min=None, danger_max=200.0, is_active=True,
                                 created_at=datetime.now(timezone.utc),
                                 updated_at=datetime.now(timezone.utc)))
    db_session.add(_row(site_a.id, datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc), tss=250.0))
    db_session.add(_row(site_b.id, datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc), tss=50.0))
    await db_session.commit()

    async def days(**params):
        res = await client.get("/stats/compliance-daily",
                               params={"month": "2026-07", **params}, headers=headers)
        assert res.status_code == 200
        return {d["date"]: d["status"] for d in res.json()["days"]}

    only_a = await days(site_uid="CD-A")
    assert only_a["2026-07-03"] == "violation"
    assert only_a["2026-07-01"] == "none"

    only_b = await days(site_uid="CD-B")
    assert only_b["2026-07-01"] == "ok"
    assert only_b["2026-07-03"] == "none"

    # Without site_uid nothing changes: every accessible site counts.
    both = await days()
    assert both["2026-07-01"] == "ok"
    assert both["2026-07-03"] == "violation"


@pytest.mark.anyio
async def test_compliance_daily_site_uid_cannot_widen_a_viewers_scope(client, db_session):
    from app.models.models import ViewerSite
    site_a = await _make_site(db_session, uid="CV-A")
    site_b = await _make_site(db_session, uid="CV-B")
    db_session.add(AlertRule(site_id=site_b.id, field="tss",
                             warning_min=None, warning_max=150.0,
                             danger_min=None, danger_max=200.0, is_active=True,
                             created_at=datetime.now(timezone.utc),
                             updated_at=datetime.now(timezone.utc)))
    db_session.add(_row(site_b.id, datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc), tss=250.0))
    viewer = User(name="Klien", email="klien@example.com",
                  password_hash=hash_password("Secret123"), role="viewer", is_active=True)
    db_session.add(viewer)
    await db_session.commit()
    await db_session.refresh(viewer)
    db_session.add(ViewerSite(user_id=viewer.id, site_id=site_a.id))
    await db_session.commit()
    login = await client.post("/auth/login",
                              json={"email": "klien@example.com", "password": "Secret123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = await client.get("/stats/compliance-daily",
                           params={"month": "2026-07", "site_uid": "CV-B"}, headers=headers)

    assert res.status_code == 200
    assert {d["status"] for d in res.json()["days"]} == {"none"}
