from alembic import op
import sqlalchemy as sa

revision = '0006_add_anomaly_detection'
down_revision = '0005_add_site_timezone'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('alerts', sa.Column('category', sa.String(16), nullable=False, server_default='compliance'))
    op.add_column('alerts', sa.Column('anomaly_type', sa.String(16), nullable=True))
    op.add_column('alerts', sa.Column('detail', sa.String(255), nullable=True))

    op.create_table(
        'sensor_health',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('field', sa.String(32), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='ok'),
        sa.Column('anomaly_type', sa.String(16), nullable=True),
        sa.Column('reason', sa.String(255), nullable=True),
        sa.Column('last_value', sa.Float(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('site_id', 'field', name='uq_sensor_health_site_field'),
    )
    op.create_index('ix_sensor_health_site_id', 'sensor_health', ['site_id'])


def downgrade():
    op.drop_index('ix_sensor_health_site_id', table_name='sensor_health')
    op.drop_table('sensor_health')
    op.drop_column('alerts', 'detail')
    op.drop_column('alerts', 'anomaly_type')
    op.drop_column('alerts', 'category')
