"""Logger diagnosis: refused device requests, logger incidents, send-failure clocks.

device_rejections summarises every refused device request per (uid, source,
reason) so the web can say why a logger's data is not arriving.
logger_incidents records each disruption with its inferred cause; open_key is
unique while an incident is open so it can never be opened (or alarmed) twice.
History is imported by the liveness scan, not here (see logger_incidents.py):
that code is testable on SQLite and copes with the duplicated legacy alarms.
Also indexes logger_events by (site_id, ts) for the per-site event windows.
"""
from alembic import op
import sqlalchemy as sa

revision = '0015_logger_diagnosis'
down_revision = '0014_quality_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('logger_status', sa.Column('mm_fail_since', sa.DateTime(timezone=True), nullable=True))
    op.add_column('logger_status', sa.Column('klhk_fail_since', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'device_rejections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uid', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=True),
        sa.Column('source', sa.String(length=16), nullable=False),
        sa.Column('reason', sa.String(length=32), nullable=False),
        sa.Column('first_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_detail', sa.String(length=255), nullable=True),
        sa.UniqueConstraint('uid', 'source', 'reason', name='uq_device_rejection'),
    )
    op.create_index('ix_device_rejections_site_id', 'device_rejections', ['site_id'])
    op.create_index('ix_device_rejections_last_at', 'device_rejections', ['last_at'])

    op.create_table(
        'logger_incidents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(length=24), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('open_key', sa.String(length=48), nullable=True),
        sa.Column('cause', sa.String(length=24), nullable=True),
        sa.Column('cause_detail', sa.String(length=255), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=True),
        sa.Column('data_expected', sa.Integer(), nullable=True),
        sa.Column('data_recovered', sa.Integer(), nullable=True),
        sa.Column('alert_id', sa.Integer(), sa.ForeignKey('alerts.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_logger_incidents_site_id', 'logger_incidents', ['site_id'])
    op.create_index('ix_logger_incidents_kind', 'logger_incidents', ['kind'])
    op.create_index('ix_logger_incidents_started_at', 'logger_incidents', ['started_at'])
    op.create_index('ix_logger_incidents_open_key', 'logger_incidents', ['open_key'], unique=True)
    op.create_index('ix_logger_events_site_ts', 'logger_events', ['site_id', 'ts'])


def downgrade():
    op.drop_index('ix_logger_events_site_ts', table_name='logger_events')
    op.drop_table('logger_incidents')
    op.drop_table('device_rejections')
    op.drop_column('logger_status', 'klhk_fail_since')
    op.drop_column('logger_status', 'mm_fail_since')
