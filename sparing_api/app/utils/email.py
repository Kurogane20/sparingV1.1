import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import select
from app.core.config import settings
from app.core.logging import logger
from app.models.models import User, ViewerSite, Site

FIELD_LABELS = {
    "ph": "pH", "tss": "TSS (mg/L)", "cod": "COD (mg/L)",
    "nh3n": "NH3-N (mg/L)", "temp": "Temperatur (°C)",
    "noise": "Kebisingan (dB)", "pm25": "PM2.5 (µg/m³)",
    "pm10": "PM10 (µg/m³)", "device_offline": "Perangkat Offline",
}


async def _get_recipient_emails(site_id: int, db) -> list[str]:
    admin_result = await db.execute(
        select(User.email).where(User.role == "admin", User.is_active == True)
    )
    emails = list(admin_result.scalars().all())

    viewer_result = await db.execute(
        select(User.email)
        .join(ViewerSite, ViewerSite.user_id == User.id)
        .where(ViewerSite.site_id == site_id, User.is_active == True)
    )
    emails += list(viewer_result.scalars().all())
    return list(set(emails))


async def send_alert_emails(
    site_id: int,
    site_uid: str,
    data: dict,
) -> None:
    """Send alert email notifications. No-op when smtp_host is not configured.
    Creates its own DB session — safe to call via asyncio.create_task().
    """
    if not settings.smtp_host:
        return

    from app.core.db import SessionLocal
    try:
        site_name = None
        site_company = None
        recipients = []

        async with SessionLocal() as db:
            site_result = await db.execute(select(Site).where(Site.id == site_id))
            site = site_result.scalar_one_or_none()
            if not site:
                return
            site_name = site.name
            site_company = site.company_name
            recipients = await _get_recipient_emails(site_id, db)

        if not recipients:
            return

        violated_fields = []
        for field, label in FIELD_LABELS.items():
            if field == "device_offline":
                continue
            value = data.get(field)
            if value is not None:
                violated_fields.append(f"{label}: {value}")

        if not violated_fields:
            return

        body = (
            f"Peringatan Baku Mutu — {site_name} ({site_company})\n\n"
            f"Parameter berikut melebihi batas baku mutu:\n"
            + "\n".join(f"  • {v}" for v in violated_fields)
            + f"\n\nLokasi  : {site_name}\n"
            f"UID     : {site_uid}\n"
            f"Waktu   : {data.get('ts', 'N/A')}\n\n"
            f"Silakan buka dashboard SPARING untuk detail lebih lanjut."
        )

        msg = MIMEMultipart()
        msg["Subject"] = f"[SPARING] Peringatan Baku Mutu — {site_name}"
        msg["From"] = settings.smtp_from
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(body, "plain", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_pass or None,
            use_tls=False,
            start_tls=settings.smtp_tls,
        )
        logger.info(f"Alert email sent for site {site_uid} to {len(recipients)} recipients")

    except Exception:
        logger.exception(f"Failed to send alert email for site {site_uid}")
