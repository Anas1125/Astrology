"""Store immutable birth-input snapshots and deduplication key for chart runs."""
from alembic import op
import sqlalchemy as sa

revision = "0002_chart_calc_snapshots"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("chart_calculation_runs", sa.Column("input_snapshot", sa.JSON(), nullable=True))
    op.add_column("chart_calculation_runs", sa.Column("calculation_key", sa.String(length=64), nullable=True))
    op.create_index("ix_chart_calculation_runs_calculation_key", "chart_calculation_runs", ["calculation_key"], unique=True)


def downgrade():
    op.drop_index("ix_chart_calculation_runs_calculation_key", table_name="chart_calculation_runs")
    op.drop_column("chart_calculation_runs", "calculation_key")
    op.drop_column("chart_calculation_runs", "input_snapshot")
