"""Persist typed deterministic responses alongside readable message text."""
from alembic import op
import sqlalchemy as sa


revision = "0005_deterministic_ai_responses"
down_revision = "0004_atomic_ai_usage"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("chat_messages", sa.Column("response_data", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("chat_messages", "response_data")
