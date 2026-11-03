"""Add atomic daily AI usage counters and idempotent request state."""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0004_atomic_ai_usage"
down_revision = "0003_ai_chat_chart"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("ai_usage_logs") as batch_op:
        batch_op.add_column(sa.Column("request_key", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("request_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("status", sa.String(length=16), server_default="completed", nullable=False)
        )
        batch_op.create_unique_constraint(
            "uq_ai_usage_user_request_key", ["user_id", "request_key"]
        )
    op.create_table(
        "ai_usage_daily_counters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("period_key", sa.String(length=16), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "period_key", name="uq_ai_daily_counter_user_period"),
    )
    op.create_index("ix_ai_usage_daily_counters_user_id", "ai_usage_daily_counters", ["user_id"])
    bind = op.get_bind()
    existing = bind.execute(sa.text(
        "SELECT user_id, period_key, count(*) AS request_count FROM ai_usage_logs "
        "WHERE feature = 'ai_chat' GROUP BY user_id, period_key"
    )).mappings()
    for row in existing:
        counter_id = uuid4()
        if bind.dialect.name == "sqlite":
            counter_id = counter_id.hex
        bind.execute(
            sa.text("INSERT INTO ai_usage_daily_counters (id, user_id, period_key, request_count, updated_at) "
                    "VALUES (:id, :user_id, :period_key, :request_count, CURRENT_TIMESTAMP)"),
            {"id": counter_id, **row},
        )


def downgrade():
    op.drop_index("ix_ai_usage_daily_counters_user_id", table_name="ai_usage_daily_counters")
    op.drop_table("ai_usage_daily_counters")
    with op.batch_alter_table("ai_usage_logs") as batch_op:
        batch_op.drop_constraint("uq_ai_usage_user_request_key", type_="unique")
        batch_op.drop_column("status")
        batch_op.drop_column("request_hash")
        batch_op.drop_column("request_key")
