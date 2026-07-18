from alembic import op
import sqlalchemy as sa

revision = '0007_alert_followup'
down_revision = '0006_add_anomaly_detection'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('alerts', sa.Column('followup_note', sa.Text(), nullable=True))
    op.add_column('alerts', sa.Column('followup_by_user_id', sa.Integer(), nullable=True))
    op.add_column('alerts', sa.Column('followup_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('alerts', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'fk_alerts_followup_user', 'alerts', 'users',
        ['followup_by_user_id'], ['id'], ondelete='SET NULL',
    )


def downgrade():
    op.drop_constraint('fk_alerts_followup_user', 'alerts', type_='foreignkey')
    op.drop_column('alerts', 'resolved_at')
    op.drop_column('alerts', 'followup_at')
    op.drop_column('alerts', 'followup_by_user_id')
    op.drop_column('alerts', 'followup_note')
