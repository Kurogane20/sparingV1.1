"""Per-field reading quality.

`sensor_data.quality_flag` holds the row's worst flag ("anomaly" < "sensor_error");
`sensor_data.quality_fields` lists the parameters that flag applies to, stored as
",nh3n,tss," so `LIKE '%,ph,%'` is an exact field match on MySQL and SQLite alike.
A flagged row with NULL quality_fields predates per-field flags and keeps the old
meaning: every parameter in the row is flagged.

The parsing helpers stay free of SQLAlchemy so the pure timeseries helpers can
use them; only `field_quality_ok` builds a SQL clause.
"""


def field_flag_token(field: str) -> str:
    return f",{field},"


def parse_quality_fields(raw: str | None) -> frozenset[str] | None:
    if raw is None:
        return None
    return frozenset(part for part in raw.split(",") if part)


def field_is_flagged(quality_flag: str | None, quality_fields: str | None, field: str) -> bool:
    if not quality_flag:
        return False
    fields = parse_quality_fields(quality_fields)
    return fields is None or field in fields


def field_quality_ok(field: str):
    """SQL condition: this row's `field` value is not quality-flagged."""
    from sqlalchemy import and_, not_, or_
    from app.models.models import SensorData
    return or_(
        SensorData.quality_flag.is_(None),
        and_(
            SensorData.quality_fields.isnot(None),
            not_(SensorData.quality_fields.like(f"%{field_flag_token(field)}%")),
        ),
    )
