from alembic import op
import sqlalchemy as sa

revision = '0008_sensor_data_quality_flag'
down_revision = '0007_alert_followup'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sensor_data', sa.Column('quality_flag', sa.String(16), nullable=True))


def downgrade():
    op.drop_column('sensor_data', 'quality_flag')
