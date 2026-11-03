"""Associate AI conversations with the persisted chart used as context."""
from alembic import op
import sqlalchemy as sa


revision = "0003_ai_chat_chart"
down_revision = "0002_chart_calc_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("chat_sessions") as batch_op:
        batch_op.add_column(sa.Column("chart_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_chat_sessions_chart_id_birth_charts", "birth_charts", ["chart_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_index("ix_chat_sessions_chart_id", ["chart_id"])


def downgrade():
    with op.batch_alter_table("chat_sessions") as batch_op:
        batch_op.drop_index("ix_chat_sessions_chart_id")
        batch_op.drop_constraint("fk_chat_sessions_chart_id_birth_charts", type_="foreignkey")
        batch_op.drop_column("chart_id")
