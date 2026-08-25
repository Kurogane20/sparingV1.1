"""Add dashboard monitoring configuration and operational rule persistence.

The configuration seed gives every existing site the same monitoring defaults
that new dashboard clients expect, without activating any operational rules.
"""
from alembic import op
import sqlalchemy as sa


revision = "0013_dashboard_timeseries"
down_revision = "0012_maint_cal_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_monitoring_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("cadence_seconds", sa.Integer(), nullable=False),
        sa.Column("stale_after_seconds", sa.Integer(), nullable=False),
        sa.Column("max_chart_points", sa.Integer(), nullable=False),
        sa.Column("max_range_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("site_id", name="uq_site_monitoring_config_site"),
    )
    op.create_index(
        "ix_site_monitoring_configs_site_id", "site_monitoring_configs", ["site_id"]
    )

    op.create_table(
        "operational_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(length=32), nullable=False),
        sa.Column("secondary_field", sa.String(length=32), nullable=True),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("window_seconds", sa.Integer(), nullable=True),
        sa.Column("min_points", sa.Integer(), nullable=True),
        sa.Column("hold_seconds", sa.Integer(), nullable=True),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=True),
        sa.Column("abs_delta", sa.Float(), nullable=True),
        sa.Column("percent_delta", sa.Float(), nullable=True),
        sa.Column("minimum_baseline", sa.Float(), nullable=True),
        sa.Column("trigger_mode", sa.String(length=16), nullable=True),
        sa.Column("no_flow_threshold", sa.Float(), nullable=True),
        sa.Column("low_flow_threshold", sa.Float(), nullable=True),
        sa.Column("recovery_threshold", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "site_id", "field", "rule_type", name="uq_operational_rule_site_field_type"
        ),
    )
    op.create_index("ix_operational_rules_site_id", "operational_rules", ["site_id"])

    with op.batch_alter_table("alert_rules") as batch_op:
        batch_op.add_column(
            sa.Column("reference_label", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(sa.Column("regulation", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("updated_by_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_alert_rules_updated_by_user_id_users",
            "users",
            ["updated_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.execute(
        """
        INSERT INTO site_monitoring_configs
            (site_id, cadence_seconds, stale_after_seconds,
             max_chart_points, max_range_days, created_at, updated_at)
        SELECT id, 120, 5400, 720, 31, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM sites
        """
    )


def downgrade():
    with op.batch_alter_table("alert_rules") as batch_op:
        batch_op.drop_constraint("fk_alert_rules_updated_by_user_id_users", type_="foreignkey")
        batch_op.drop_column("updated_by_user_id")
        batch_op.drop_column("regulation")
        batch_op.drop_column("reference_label")

    op.drop_index("ix_operational_rules_site_id", table_name="operational_rules")
    op.drop_table("operational_rules")
    op.drop_index("ix_site_monitoring_configs_site_id", table_name="site_monitoring_configs")
    op.drop_table("site_monitoring_configs")
