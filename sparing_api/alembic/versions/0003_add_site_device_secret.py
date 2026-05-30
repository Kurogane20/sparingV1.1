from alembic import op
import sqlalchemy as sa
import secrets

revision = '0003_add_site_device_secret'
down_revision = '0002_add_alerts'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('sites', sa.Column('device_secret', sa.String(64), nullable=True, unique=True))
    op.add_column('sites', sa.Column('last_ingest_at', sa.DateTime(timezone=True), nullable=True))

    # Backfill device_secret for all existing sites
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM sites WHERE device_secret IS NULL")).fetchall()
    for row in rows:
        secret = secrets.token_hex(32)
        conn.execute(
            sa.text("UPDATE sites SET device_secret = :s WHERE id = :id"),
            {"s": secret, "id": row.id}
        )

def downgrade():
    op.drop_column('sites', 'last_ingest_at')
    op.drop_column('sites', 'device_secret')
