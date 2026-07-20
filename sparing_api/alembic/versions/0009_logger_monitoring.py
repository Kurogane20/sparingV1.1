from alembic import op
import sqlalchemy as sa

revision = '0009_logger_monitoring'
down_revision = '0008_sensor_data_quality_flag'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'logger_status',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('logger_version', sa.String(32), nullable=True),
        sa.Column('uptime_s', sa.Integer(), nullable=True),
        sa.Column('op_status', sa.SmallInteger(), nullable=True),
        sa.Column('ph_ok', sa.Boolean(), nullable=True),
        sa.Column('tss_ok', sa.Boolean(), nullable=True),
        sa.Column('debit_ok', sa.Boolean(), nullable=True),
        sa.Column('cod_ok', sa.Boolean(), nullable=True),
        sa.Column('nh3n_ok', sa.Boolean(), nullable=True),
        sa.Column('consec_fail', sa.Integer(), nullable=True),
        sa.Column('sensor_fail_since', sa.DateTime(timezone=True), nullable=True),
        sa.Column('internet_ok', sa.Boolean(), nullable=True),
        sa.Column('last_send_ok_mm', sa.Boolean(), nullable=True),
        sa.Column('last_send_ok_klhk', sa.Boolean(), nullable=True),
        sa.Column('buffer_depth', sa.Integer(), nullable=True),
        sa.Column('daily_sent', sa.Integer(), nullable=True),
        sa.Column('cpu_temp', sa.Float(), nullable=True),
        sa.Column('cpu_pct', sa.Float(), nullable=True),
        sa.Column('mem_pct', sa.Float(), nullable=True),
        sa.Column('disk_pct', sa.Float(), nullable=True),
        sa.Column('state', sa.String(16), nullable=False, server_default='alive'),
        sa.Column('state_since', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('site_id', name='uq_logger_status_site'),
    )
    op.create_table(
        'logger_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('event_uid', sa.String(64), nullable=False),
        sa.Column('type', sa.String(32), nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('severity', sa.String(16), nullable=False, server_default='info'),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('event_uid', name='uq_logger_event_uid'),
    )
    op.create_index('ix_logger_events_site_id', 'logger_events', ['site_id'])
    op.create_index('ix_logger_events_type', 'logger_events', ['type'])


def downgrade():
    op.drop_index('ix_logger_events_type', table_name='logger_events')
    op.drop_index('ix_logger_events_site_id', table_name='logger_events')
    op.drop_table('logger_events')
    op.drop_table('logger_status')
