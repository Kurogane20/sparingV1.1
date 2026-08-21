"""Add calibration record fields to maintenance_logs (#15).

Additive, all nullable — safe to apply on production with no data backfill.
"""
from alembic import op
import sqlalchemy as sa

revision = '0012_maint_cal_fields'
down_revision = '0011_sensor_data_unique_site_ts'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('maintenance_logs', sa.Column('field', sa.String(length=16), nullable=True))
    op.add_column('maintenance_logs', sa.Column('before_value', sa.Float(), nullable=True))
    op.add_column('maintenance_logs', sa.Column('after_value', sa.Float(), nullable=True))
    op.add_column('maintenance_logs', sa.Column('offset', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('maintenance_logs', 'offset')
    op.drop_column('maintenance_logs', 'after_value')
    op.drop_column('maintenance_logs', 'before_value')
    op.drop_column('maintenance_logs', 'field')
