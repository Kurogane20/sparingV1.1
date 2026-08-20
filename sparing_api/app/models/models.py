from sqlalchemy import String, Integer, SmallInteger, Boolean, DateTime, ForeignKey, Float, JSON, UniqueConstraint, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.core.db import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))  # admin/operator/viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    viewer_sites: Mapped[list["ViewerSite"]] = relationship(back_populates="user")

class Site(Base):
    __tablename__ = "sites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    company_name: Mapped[str] = mapped_column(String(255))
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default='Asia/Jakarta', server_default='Asia/Jakarta')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    device_secret: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    last_ingest_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    devices: Mapped[list["SensorDevice"]] = relationship(back_populates="site")

class ViewerSite(Base):
    __tablename__ = "viewer_sites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    user: Mapped["User"] = relationship(back_populates="viewer_sites")
    site: Mapped["Site"] = relationship()

    __table_args__ = (UniqueConstraint("user_id", "site_id", name="uq_viewer_site"),)

class SensorType(Base):
    __tablename__ = "sensor_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

class SensorDevice(Base):
    __tablename__ = "sensor_devices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    modbus_addr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    serial_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    site: Mapped["Site"] = relationship(back_populates="devices")

class SensorData(Base):
    __tablename__ = "sensor_data"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("sensor_devices.id"), nullable=True, index=True)
    device_uid: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # Device identifier string
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    tss: Mapped[float | None] = mapped_column(Float, nullable=True)
    debit: Mapped[float | None] = mapped_column(Float, nullable=True)
    nh3n: Mapped[float | None] = mapped_column(Float, nullable=True)
    cod: Mapped[float | None] = mapped_column(Float, nullable=True)
    temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    rh: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    noise: Mapped[float | None] = mapped_column(Float, nullable=True)
    co: Mapped[float | None] = mapped_column(Float, nullable=True)
    so2: Mapped[float | None] = mapped_column(Float, nullable=True)
    no2: Mapped[float | None] = mapped_column(Float, nullable=True)
    o3: Mapped[float | None] = mapped_column(Float, nullable=True)
    pm25: Mapped[float | None] = mapped_column(Float, nullable=True)
    pm10: Mapped[float | None] = mapped_column(Float, nullable=True)
    tvoc: Mapped[float | None] = mapped_column(Float, nullable=True)
    voltage: Mapped[float | None] = mapped_column(Float, nullable=True)
    current: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_flag: Mapped[str | None] = mapped_column(String(16), nullable=True)  # NULL = valid, 'anomaly' = flagged by anomaly engine
    op_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # -1 stopped, -2 calibration, -3 malfunction (KLHK Pasal 6.2.6.6g)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    ingest_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ingest_idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    __table_args__ = (
        # One reading per (site, timestamp). SPARING stations are single-logger:
        # a duplicate (site_id, ts) means the device re-sent the same burst, and a
        # second copy would corrupt completeness/averages/exceedance. The unique
        # constraint's index also serves the site+ts range scans, so the old plain
        # index is dropped in migration 0011.
        UniqueConstraint("site_id", "ts", name="uq_sensor_data_site_ts"),
    )

class IngestLog(Base):
    __tablename__ = "ingest_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    api_key_or_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(128))
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    scopes: Mapped[str | None] = mapped_column(String(255), nullable=True)  # comma-separated
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AuthTokenBlacklist(Base):
    __tablename__ = "auth_token_blacklist"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

class AlertRule(Base):
    __tablename__ = "alert_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    field: Mapped[str] = mapped_column(String(32))
    warning_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    warning_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    danger_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    danger_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    site: Mapped["Site"] = relationship()

    __table_args__ = (UniqueConstraint("site_id", "field", name="uq_alert_rule_site_field"),)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    device_uid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    field: Mapped[str] = mapped_column(String(32))
    value: Mapped[float] = mapped_column(Float)
    threshold_type: Mapped[str] = mapped_column(String(16))  # warning | danger
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | acknowledged | resolved
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    category: Mapped[str] = mapped_column(String(16), default="compliance", server_default="compliance")
    anomaly_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    followup_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    followup_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    followup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    site: Mapped["Site"] = relationship()


class SensorHealth(Base):
    __tablename__ = "sensor_health"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    field: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="ok", server_default="ok")  # ok | warning | bad
    anomaly_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # reserved for future ML scorer
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), onupdate=utcnow)

    __table_args__ = (UniqueConstraint("site_id", "field", name="uq_sensor_health_site_field"),)

class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("sensor_devices.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(32))  # calibration | repair | inspection | note
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Calibration record (optional): reference vs measured reading and the applied
    # offset, so a calibration is auditable beyond a free-text note.
    field: Mapped[str | None] = mapped_column(String(16), nullable=True)  # ph/tss/cod/...
    before_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    after_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    offset: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    device: Mapped["SensorDevice"] = relationship()
    performed_by: Mapped["User | None"] = relationship(foreign_keys=[performed_by_user_id])

class LoggerStatus(Base):
    """Latest heartbeat snapshot — exactly one row per site (upserted)."""
    __tablename__ = "logger_status"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), unique=True, index=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    logger_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    uptime_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    op_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    ph_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    tss_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    debit_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cod_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    nh3n_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    consec_fail: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sensor_fail_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    internet_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_send_ok_mm: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_send_ok_klhk: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    buffer_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_sent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpu_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    mem_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="alive", server_default="alive")
    state_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    site: Mapped["Site"] = relationship()


class LoggerEvent(Base):
    """Append-only log of logger state changes. `event_uid` is the idempotency key:
    the logger may re-upload unsynced events after a reconnect.

    Uniqueness is scoped to (site_id, event_uid), NOT event_uid alone: field
    loggers are commonly cloned from one SD-card image, so two sites can emit the
    same uid. A global unique key would make one site's replay silently swallow
    another site's event — losing exactly the audit trail this table exists for.
    Dedup lookups must therefore always filter by site_id too."""
    __tablename__ = "logger_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    event_uid: Mapped[str] = mapped_column(String(64), index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))          # logger clock
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # server clock
    severity: Mapped[str] = mapped_column(String(16), default="info")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    site: Mapped["Site"] = relationship()

    __table_args__ = (
        UniqueConstraint("site_id", "event_uid", name="uq_logger_event_site_uid"),
    )
