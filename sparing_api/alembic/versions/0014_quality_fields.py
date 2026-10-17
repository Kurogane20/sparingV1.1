"""Per-field quality flags on sensor_data.

quality_fields lists the parameters a row's quality_flag applies to (",nh3n,tss,").
Before this, a flatlined NH3-N sensor flagged the whole row and every other
parameter of that reading (pH, TSS, debit) showed "Kesalahan Sensor".

Backfill (MySQL): legacy sensor_error rows are attributed to the fields the
site's sensor_health currently marks bad — the flatline/implausible sensors that
produced those flags — or ',' (no displayed field) when none is bad. Legacy
'anomaly' rows keep NULL, i.e. the old row-level meaning.
"""
from alembic import op
import sqlalchemy as sa

revision = '0014_quality_fields'
down_revision = '0013_dashboard_timeseries'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sensor_data', sa.Column('quality_fields', sa.String(length=160), nullable=True))
    if op.get_bind().dialect.name != 'mysql':
        return
    op.execute(
        """
        UPDATE sensor_data sd
        SET sd.quality_fields = COALESCE(
            CONCAT(',', (
                SELECT GROUP_CONCAT(h.field ORDER BY h.field SEPARATOR ',')
                FROM sensor_health h
                WHERE h.site_id = sd.site_id AND h.status = 'bad'
            ), ','),
            ','
        )
        WHERE sd.quality_flag = 'sensor_error' AND sd.quality_fields IS NULL
        """
    )


def downgrade():
    op.drop_column('sensor_data', 'quality_fields')
