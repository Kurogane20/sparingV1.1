"""Compliance report: the period and its daily table follow the site's calendar
days, and compliance uses the same exclusions as the dashboard."""
from datetime import datetime, timezone

import pytest

from app.core.security import hash_password
from app.models.models import SensorData, Site, User


async def _headers(client, db_session):
    db_session.add(User(name="Op", email="report@example.com", password_hash=hash_password("Secret123"),
                        role="admin", is_active=True))
    await db_session.commit()
    login = await client.post("/auth/login", json={"email": "report@example.com", "password": "Secret123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _row(site_id, utc_hour_ts, **values):
    return SensorData(site_id=site_id, ts=utc_hour_ts, created_at=utc_hour_ts, **values)


def utc(day, hour):
    return datetime(2026, 7, day, hour, 0, tzinfo=timezone.utc)


@pytest.mark.anyio
async def test_report_day_is_the_sites_calendar_day_with_dashboard_exclusions(client, db_session):
    site = Site(uid="RPT-WIB", name="Report", company_name="C", timezone="Asia/Jakarta", is_active=True)
    db_session.add(site)
    await db_session.commit()
    db_session.add_all([
        _row(site.id, utc(1, 16), ph=8.8),                    # 1 Jul 23:00 WIB -> outside 2 Jul
        _row(site.id, utc(1, 18), ph=7.0),                    # 2 Jul 01:00 WIB
        _row(site.id, utc(2, 5), ph=13.0, op_status=-3),      # malfunction marker -> excluded
        _row(site.id, utc(2, 6), ph=12.0, quality_flag="sensor_error", quality_fields=",ph,"),  # bad pH -> excluded
        _row(site.id, utc(2, 7), ph=9.5, nh3n=0.0, quality_flag="sensor_error", quality_fields=",nh3n,"),  # pH valid
        _row(site.id, utc(2, 10), ph=7.2),                    # 2 Jul 17:00 WIB
        _row(site.id, utc(2, 18), ph=7.4),                    # 3 Jul 01:00 WIB -> outside 2 Jul
    ])
    await db_session.commit()
    headers = await _headers(client, db_session)

    res = await client.get("/reports/generate", headers=headers, params={
        "site_uid": site.uid, "period_from": "2026-07-02", "period_to": "2026-07-02",
    })

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["summary"]["total_records"] == 4          # 2 Jul WIB, markers excluded
    ph = next(p for p in body["parameters"] if p["field"] == "ph")
    assert ph["stats"]["count"] == 3                      # 7.0, 9.5, 7.2
    assert (ph["stats"]["min"], ph["stats"]["max"]) == (7.0, 9.5)
    assert ph["stats"]["std_dev"] is not None
    assert ph["violation_count"] == 1                     # 9.5 > 9.0; flagged 12.0 not counted
    assert ph["compliance_pct"] == 66.7
    assert [d["date"] for d in body["daily_summary"]] == ["2026-07-02"]
    assert body["daily_summary"][0]["ph_avg"] == 7.9
    assert [(v["field"], v["value"]) for v in body["violations"]] == [("ph", 9.5)]
