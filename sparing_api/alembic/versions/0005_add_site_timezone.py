from alembic import op
import sqlalchemy as sa

revision = '0005_add_site_timezone'
down_revision = '0004_add_maintenance_log'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('sites',
        sa.Column('timezone', sa.String(64), nullable=False, server_default='Asia/Jakarta')
    )

def downgrade():
    op.drop_column('sites', 'timezone')
