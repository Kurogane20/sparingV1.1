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
    """When date_from is given, the actual-count window starts there (e.g. today
    00:00 WIB), while the target stays the full-day 30*hours."""
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
    assert body["expected"] == 1 * 30 * 24    # full-day target unchanged
