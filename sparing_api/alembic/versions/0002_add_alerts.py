from alembic import op
import sqlalchemy as sa

revision = '0002_add_alerts'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('alert_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('field', sa.String(32), nullable=False),
        sa.Column('warning_min', sa.Float(), nullable=True),
        sa.Column('warning_max', sa.Float(), nullable=True),
        sa.Column('danger_min', sa.Float(), nullable=True),
        sa.Column('danger_max', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('site_id', 'field', name='uq_alert_rule_site_field'),
    )
    op.create_index('ix_alert_rules_site_id', 'alert_rules', ['site_id'])

    op.create_table('alerts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_uid', sa.String(64), nullable=True),
        sa.Column('field', sa.String(32), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('threshold_type', sa.String(16), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='active'),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_alerts_site_status', 'alerts', ['site_id', 'status', 'triggered_at'])

def downgrade():
    op.drop_index('ix_alerts_site_status', table_name='alerts')
    op.drop_table('alerts')
    op.drop_index('ix_alert_rules_site_id', table_name='alert_rules')
    op.drop_table('alert_rules')
