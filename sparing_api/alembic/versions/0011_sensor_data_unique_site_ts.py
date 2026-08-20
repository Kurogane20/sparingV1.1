"""Enforce one reading per (site_id, ts) on sensor_data.

Replaces the plain index ix_sensor_data_site_ts_desc with a UNIQUE constraint
uq_sensor_data_site_ts so a device re-sending the same burst can no longer create
duplicate rows (which corrupt completeness/averages/exceedance).

IMPORTANT — run the dedup script FIRST on any database that may already contain
duplicates, otherwise creating the unique constraint fails:

    python -m app.scripts.dedup_sensor_data          # dry-run (reports only)
    python -m app.scripts.dedup_sensor_data --apply  # delete duplicate copies

Only after the dry-run reports 0 remaining duplicates should this migration be
applied.
"""
from alembic import op

revision = '0011_sensor_data_unique_site_ts'
down_revision = '0010_sensor_data_op_status'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the redundant plain index — the unique constraint below provides the
    # same (site_id, ts) index for range scans.
    op.drop_index('ix_sensor_data_site_ts_desc', table_name='sensor_data')
    op.create_unique_constraint('uq_sensor_data_site_ts', 'sensor_data', ['site_id', 'ts'])


def downgrade():
    op.drop_constraint('uq_sensor_data_site_ts', 'sensor_data', type_='unique')
    op.create_index('ix_sensor_data_site_ts_desc', 'sensor_data', ['site_id', 'ts'])
