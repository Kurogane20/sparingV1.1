from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from datetime import datetime, timezone, date

from app.core.db import get_db
from app.api.deps import get_current_user, get_viewer_site_uids
from app.models.models import Site, SensorData, AlertRule
from app.schemas.report import (
    ReportOut, ReportSummaryOut, ParameterReportOut, DailySummaryOut,
    ViolationOut, BakuMutuOut, StatsOut,
)
from app.utils.report_helpers import (
    make_period_label, calculate_trend, compliance_pct,
    get_baku_mutu, overall_status, REPORT_PARAMS, PARAM_LABELS,
)

router = APIRouter()


def _build_violation_filter(col, bm: dict):
    """Build SQLAlchemy WHERE clause for values outside baku mutu limits."""
    conditions = []
    if bm.get("max") is not None:
        conditions.append(col > bm["max"])
    if bm.get("min") is not None:
        conditions.append(col < bm["min"])
    if not conditions:
        return None
    return or_(*conditions)


@router.get("/generate", response_model=ReportOut)
async def generate_report(
    site_uid: str = Query(...),
    period_from: str = Query(..., description="YYYY-MM-DD"),
    period_to: str = Query(..., description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    site = (await db.execute(select(Site).where(Site.uid == site_uid))).scalar_one_or_none()
    if not site:
        raise HTTPException(404, "Site not found")
    if viewer_uids and site_uid not in viewer_uids:
        raise HTTPException(403, "Forbidden")

    try:
        from_date = date.fromisoformat(period_from)
        to_date = date.fromisoformat(period_to)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    if from_date > to_date:
        raise HTTPException(400, "period_from must not be after period_to")

    from_dt = datetime(from_date.year, from_date.month, from_date.day, 0, 0, 0, tzinfo=timezone.utc)
    to_dt = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59, tzinfo=timezone.utc)
    mid_dt = from_dt + (to_dt - from_dt) / 2

    rules_result = await db.execute(
        select(AlertRule).where(AlertRule.site_id == site.id, AlertRule.is_active == True)
    )
    rules_by_field = {r.field: r for r in rules_result.scalars().all()}

    total_records = (await db.execute(
        select(func.count(SensorData.id)).where(
            SensorData.site_id == site.id,
            SensorData.ts.between(from_dt, to_dt),
        )
    )).scalar_one() or 0

    parameters = []
    all_compliance = []

    for field in REPORT_PARAMS:
        col = getattr(SensorData, field)
        bm_rule = rules_by_field.get(field)
        bm = get_baku_mutu(field, bm_rule)

        stats_row = (await db.execute(
            select(
                func.avg(col),
                func.min(col),
                func.max(col),
                func.count(col),
                func.stddev_pop(col),
            ).where(
                SensorData.site_id == site.id,
                SensorData.ts.between(from_dt, to_dt),
                col.isnot(None),
            )
        )).one()

        avg_val, min_val, max_val, count_val, stddev_val = stats_row
        count_val = count_val or 0

        avg_first = (await db.execute(
            select(func.avg(col)).where(
                SensorData.site_id == site.id,
                SensorData.ts >= from_dt,
                SensorData.ts < mid_dt,
                col.isnot(None),
            )
        )).scalar_one_or_none()

        avg_second = (await db.execute(
            select(func.avg(col)).where(
                SensorData.site_id == site.id,
                SensorData.ts >= mid_dt,
                SensorData.ts <= to_dt,
                col.isnot(None),
            )
        )).scalar_one_or_none()

        trend = calculate_trend(
            float(avg_first) if avg_first is not None else None,
            float(avg_second) if avg_second is not None else None,
        )

        viol_count = 0
        if count_val > 0:
            viol_filter = _build_violation_filter(col, bm)
            if viol_filter is not None:
                viol_count = (await db.execute(
                    select(func.count(SensorData.id)).where(
                        SensorData.site_id == site.id,
                        SensorData.ts.between(from_dt, to_dt),
                        col.isnot(None),
                        viol_filter,
                    )
                )).scalar_one() or 0

        cpct = compliance_pct(count_val, viol_count)
        if count_val > 0:
            all_compliance.append(cpct)

        parameters.append(ParameterReportOut(
            field=field,
            label=PARAM_LABELS[field],
            baku_mutu=BakuMutuOut(min=bm["min"], max=bm["max"], unit=bm["unit"]),
            stats=StatsOut(
                avg=round(float(avg_val), 3) if avg_val is not None else None,
                min=round(float(min_val), 3) if min_val is not None else None,
                max=round(float(max_val), 3) if max_val is not None else None,
                std_dev=round(float(stddev_val), 3) if stddev_val is not None else None,
                count=count_val,
            ),
            compliance_pct=cpct,
            violation_count=viol_count,
            trend=trend,
        ))

    overall_compliance = round(sum(all_compliance) / len(all_compliance), 1) if all_compliance else 100.0

    _day_expr = func.date(func.convert_tz(SensorData.ts, '+00:00', '+07:00'))
    daily_rows = (await db.execute(
        select(
            _day_expr.label("day"),
            func.avg(SensorData.ph).label("ph_avg"),
            func.avg(SensorData.tss).label("tss_avg"),
            func.avg(SensorData.cod).label("cod_avg"),
            func.avg(SensorData.nh3n).label("nh3n_avg"),
            func.avg(SensorData.debit).label("debit_avg"),
            func.avg(SensorData.temp).label("temp_avg"),
        ).where(
            SensorData.site_id == site.id,
            SensorData.ts.between(from_dt, to_dt),
        ).group_by(_day_expr)
        .order_by(_day_expr)
    )).all()

    daily_summary = [
        DailySummaryOut(
            date=str(row.day),
            ph_avg=round(float(row.ph_avg), 2) if row.ph_avg is not None else None,
            tss_avg=round(float(row.tss_avg), 2) if row.tss_avg is not None else None,
            cod_avg=round(float(row.cod_avg), 2) if row.cod_avg is not None else None,
            nh3n_avg=round(float(row.nh3n_avg), 2) if row.nh3n_avg is not None else None,
            debit_avg=round(float(row.debit_avg), 2) if row.debit_avg is not None else None,
            temp_avg=round(float(row.temp_avg), 2) if row.temp_avg is not None else None,
        )
        for row in daily_rows
    ]

    violations = []
    for field in REPORT_PARAMS:
        col = getattr(SensorData, field)
        bm = get_baku_mutu(field, rules_by_field.get(field))
        viol_filter = _build_violation_filter(col, bm)
        if viol_filter is None:
            continue
        viol_rows = (await db.execute(
            select(SensorData.ts, col.label("value")).where(
                SensorData.site_id == site.id,
                SensorData.ts.between(from_dt, to_dt),
                col.isnot(None),
                viol_filter,
            ).order_by(SensorData.ts.desc()).limit(50)
        )).all()
        for row in viol_rows:
            if bm["max"] is not None and float(row.value) > bm["max"]:
                violations.append(ViolationOut(
                    ts=row.ts, field=field, value=round(float(row.value), 3),
                    limit_type="above_max", limit=bm["max"],
                ))
            elif bm["min"] is not None and float(row.value) < bm["min"]:
                violations.append(ViolationOut(
                    ts=row.ts, field=field, value=round(float(row.value), 3),
                    limit_type="below_min", limit=bm["min"],
                ))

    violations.sort(key=lambda v: v.ts, reverse=True)
    violations = violations[:200]

    return ReportOut(
        site={"uid": site.uid, "name": site.name, "company_name": site.company_name, "timezone": site.timezone or 'Asia/Jakarta'},
        period={
            "from": period_from,
            "to": period_to,
            "label": make_period_label(from_date, to_date),
        },
        generated_at=datetime.now(timezone.utc),
        summary=ReportSummaryOut(
            total_records=total_records,
            compliance_overall=overall_compliance,
            overall_status=overall_status(overall_compliance),
        ),
        parameters=parameters,
        daily_summary=daily_summary,
        violations=violations,
    )
