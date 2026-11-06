"""Add secure password reset, session revocation, and abuse limit buckets."""
from alembic import op
import sqlalchemy as sa


revision = "0006_password_reset_rate_limits"
down_revision = "0005_deterministic_ai_responses"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("auth_version", sa.Integer(), server_default="0", nullable=False))

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_user_created", "password_reset_tokens", ["user_id", "created_at"])

    op.create_table(
        "security_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_audit_events_user_id", "security_audit_events", ["user_id"])
    op.create_index("ix_security_audit_user_created", "security_audit_events", ["user_id", "created_at"])

    op.create_table(
        "security_rate_limit_buckets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash", "window_start", name="uq_security_rate_limit_key_window"),
    )
    op.create_index("ix_security_rate_limit_window", "security_rate_limit_buckets", ["window_start"])


def downgrade():
    op.drop_index("ix_security_rate_limit_window", table_name="security_rate_limit_buckets")
    op.drop_table("security_rate_limit_buckets")
    op.drop_index("ix_security_audit_user_created", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_user_id", table_name="security_audit_events")
    op.drop_table("security_audit_events")
    op.drop_index("ix_password_reset_user_created", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("auth_version")
