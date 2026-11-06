"""Add scoped, bilingual and provenance fields to horoscope content."""
from alembic import op
import sqlalchemy as sa


revision = "0007_horoscope_review_scope"
down_revision = "0006_password_reset_rate_limits"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("horoscope_contents") as batch:
        batch.drop_constraint("uq_horoscope_period_sign_lang_date", type_="unique")
        batch.add_column(sa.Column("system", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("category", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("source_references", sa.JSON(), server_default=sa.text("'[]'"), nullable=False))
        batch.add_column(sa.Column("source_verified", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch.add_column(sa.Column("editorial_reviewed", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch.add_column(sa.Column("reviewed_by", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_unique_constraint(
            "uq_horoscope_scope_lang_date",
            ["system", "period", "sign", "category", "language", "starts_on"],
        )


def downgrade():
    with op.batch_alter_table("horoscope_contents") as batch:
        batch.drop_constraint("uq_horoscope_scope_lang_date", type_="unique")
        batch.drop_column("reviewed_at")
        batch.drop_column("reviewed_by")
        batch.drop_column("editorial_reviewed")
        batch.drop_column("source_verified")
        batch.drop_column("source_references")
        batch.drop_column("category")
        batch.drop_column("system")
        batch.create_unique_constraint(
            "uq_horoscope_period_sign_lang_date", ["period", "sign", "language", "starts_on"]
        )
