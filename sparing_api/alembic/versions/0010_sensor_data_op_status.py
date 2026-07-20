from alembic import op
import sqlalchemy as sa

revision = '0010_sensor_data_op_status'
down_revision = '0009_logger_monitoring'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sensor_data', sa.Column('op_status', sa.SmallInteger(), nullable=True))


def downgrade():
    op.drop_column('sensor_data', 'op_status')
