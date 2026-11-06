"""Add an audit trail for independent horoscope content reviews."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid

revision = "0008_horoscope_review_events"
down_revision = "0007_horoscope_review_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "horoscope_review_events",
        sa.Column("id", Uuid(), primary_key=True, nullable=False),
        sa.Column("scope_key", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("reviewer_email", sa.String(length=320), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scope_key", "stage", name="uq_horoscope_review_scope_stage"),
    )
    op.create_index("ix_horoscope_review_events_scope_key", "horoscope_review_events", ["scope_key"])


def downgrade() -> None:
    op.drop_index("ix_horoscope_review_events_scope_key", table_name="horoscope_review_events")
    op.drop_table("horoscope_review_events")
