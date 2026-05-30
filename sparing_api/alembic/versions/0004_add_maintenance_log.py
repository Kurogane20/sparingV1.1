from alembic import op
import sqlalchemy as sa

revision = '0004_add_maintenance_log'
down_revision = '0003_add_site_device_secret'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('maintenance_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('sensor_devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(32), nullable=False),  # calibration|repair|inspection|note
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('performed_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('performed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('next_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_maintenance_logs_device_id', 'maintenance_logs', ['device_id'])
    op.create_index('ix_maintenance_logs_performed_at', 'maintenance_logs', ['performed_at'])

def downgrade():
    op.drop_index('ix_maintenance_logs_performed_at', table_name='maintenance_logs')
    op.drop_index('ix_maintenance_logs_device_id', table_name='maintenance_logs')
    op.drop_table('maintenance_logs')
