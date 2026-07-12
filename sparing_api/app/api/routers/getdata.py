from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
import jwt
import asyncio
from datetime import datetime, timezone
from fastapi.responses import PlainTextResponse

from app.core.config import settings as _settings
from app.core.db import get_db
from app.models.models import Site, SensorData, IngestLog, SensorDevice
from app.utils.alert_engine import trigger_alerts
from app.utils.anomaly_engine import detect_realtime

router = APIRouter()


def _global_secret() -> str:
    return _settings.getdata_secret

@router.get("/api/get-key", response_class=PlainTextResponse)
async def get_key(uid: str | None = None, db: AsyncSession = Depends(get_db)):
    if not uid:
        return _global_secret()
    site = (await db.execute(select(Site).where(Site.uid == uid))).scalar_one_or_none()
    if not site:
        raise HTTPException(404, "Site not found")
    return site.device_secret or _global_secret()

@router.post("/api/post-data")
async def post_data(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    token = body.get("token")
    if not token:
        raise HTTPException(400, "Token is required")
    
    # Step 1: Decode without verification to read uid (safe — we verify below with site's secret)
    try:
        unverified = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=["HS256"]
        )
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Invalid token format")

    uid = unverified.get("uid")
    if not uid:
        raise HTTPException(400, "Invalid data format")

    # Step 2: Look up site and determine correct signing secret
    site = (await db.execute(select(Site).where(Site.uid == uid))).scalar_one_or_none()
    if not site:
        raise HTTPException(401, "Invalid UID")

    signing_secret = site.device_secret or _global_secret()

    # Step 3: Verify JWT with the site's secret (raises on invalid/expired)
    try:
        decode = jwt.decode(token, signing_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(400, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Invalid token format")

    device_id_str = decode.get("device_id")  # Device identifier string like "DEVICE-001"
    data = decode.get("data")

    if not isinstance(data, list) or len(data) == 0 or len(data) > 30:
        raise HTTPException(400, "Invalid data format")
    
    # Lookup device by serial_no or name if device_id is provided
    # Auto-provision device if it doesn't exist
    device_db_id = None
    if device_id_str:
        device = (await db.execute(
            select(SensorDevice).where(
                SensorDevice.site_id == site.id,
                (SensorDevice.serial_no == device_id_str) | (SensorDevice.name == device_id_str)
            )
        )).scalar_one_or_none()
        
        if device:
            device_db_id = device.id
        else:
            # Auto-create device if not exists
            new_device = SensorDevice(
                site_id=site.id,
                name=device_id_str,
                serial_no=device_id_str,
                model="Auto-provisioned",
                modbus_addr=1,
                is_active=True
            )
            db.add(new_device)
            await db.flush()  # Get the ID without committing
            device_db_id = new_device.id
    
    rows = []
    now = datetime.now(timezone.utc)
    
    for d in data:
        # Parse timestamp — fall back to ingest time when the device omits it
        # (epoch 0 would otherwise date the reading 1970 and poison the
        # anomaly-detection windows)
        try:
            epoch = int(d.get("datetime", 0))
        except (TypeError, ValueError):
            epoch = 0
        ts = datetime.fromtimestamp(epoch, tz=timezone.utc) if epoch > 0 else now
        
        # Parse pH (handle both "ph" and "pH")
        ph_value = d.get("pH") or d.get("ph")
        ph = float(ph_value) if ph_value is not None else None
        if ph is not None and not (0 <= ph <= 14):
            raise HTTPException(400, "Invalid pH value")
        
        # Parse COD
        cod_value = d.get("cod") or d.get("COD")
        cod = float(cod_value) if cod_value is not None else None
        if cod is not None and cod < 0:
            raise HTTPException(400, "Invalid COD value")
        
        # Parse TSS
        tss_value = d.get("tss") or d.get("TSS")
        tss = float(tss_value) if tss_value is not None else None
        if tss is not None and tss < 0:
            raise HTTPException(400, "Invalid TSS value")
        
        # Parse Debit
        debit_value = d.get("debit") or d.get("Debit")
        debit = float(debit_value) if debit_value is not None else None
        if debit is not None and debit < 0:
            raise HTTPException(400, "Invalid Debit value")
        
        # Parse Voltage
        voltage_value = d.get("voltage") or d.get("Voltage")
        voltage = float(voltage_value) if voltage_value is not None else None
        
        # Parse Current
        current_value = d.get("current") or d.get("Current")
        current = float(current_value) if current_value is not None else None
        
        # Parse NH3N
        nh3n_value = d.get("nh3n") or d.get("NH3N") or d.get("nh3N")
        nh3n = float(nh3n_value) if nh3n_value is not None else None

        # Parse Temperature
        temp_value = d.get("temp") or d.get("temperature") or d.get("Temperature")
        temp = float(temp_value) if temp_value is not None else None

        rows.append({
            "site_id": site.id,
            "device_id": device_db_id,
            "device_uid": device_id_str,  # Store device identifier string directly
            "ts": ts,
            "ph": ph,
            "cod": cod,
            "tss": tss,
            "debit": debit,
            "voltage": voltage,
            "current": current,
            "nh3n": nh3n,
            "temp": temp,
            "created_at": now,
            "ingest_source": "getdata",
            "payload": None
        })
    
    if rows:
        await db.execute(insert(SensorData), rows)
        site.last_ingest_at = datetime.now(timezone.utc)
        db.add(IngestLog(
            source_ip=(request.client.host if request.client else None),
            api_key_or_user_id="getdata",
            status="ok",
        ))
        await db.commit()

        last_row = rows[-1]
        asyncio.create_task(trigger_alerts(
            site_id=site.id,
            site_uid=uid,
            device_uid=device_id_str,
            data=last_row,
        ))
        # Anomaly detection evaluates the WHOLE burst (devices send ~30
        # readings per hour), windows anchored to the data timestamps.
        asyncio.create_task(detect_realtime(
            site_id=site.id,
            site_uid=uid,
            device_uid=device_id_str,
            readings=rows,
        ))
    
    return {"message": "Data Berhasil Disimpan", "rows": len(rows), "uid": uid, "device_id": device_id_str}

