"""Owner-scoped saved-chart lookup for deterministic conversation responses."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import BirthChart, BirthProfile, ChartCalculationRun, ChatSession, User
from app.services.ai.context import build_chart_context
from app.services.ai.chart_facts import chart_facts_from_context
from app.services.ai.contracts import ChartFacts


def load_session_context(db: Session, chat: ChatSession, user: User) -> dict[str, Any]:
    profile = None
    if chat.profile_id is not None:
        profile = db.scalar(select(BirthProfile).where(
            BirthProfile.id == chat.profile_id,
            BirthProfile.owner_id == user.id,
        ))
    profile_data = {"id": str(profile.id), "display_name": profile.display_name} if profile else {}
    calculation = None
    if profile and chat.chart_id is not None:
        chart = db.scalar(
            select(BirthChart).join(BirthProfile, BirthProfile.id == BirthChart.profile_id).where(
                BirthChart.id == chat.chart_id,
                BirthChart.profile_id == profile.id,
                BirthProfile.owner_id == user.id,
                BirthChart.system == chat.astrology_system,
                BirthChart.status == "complete",
            )
        )
        if chart:
            run = db.scalar(
                select(ChartCalculationRun)
                .where(ChartCalculationRun.chart_id == chart.id, ChartCalculationRun.status == "complete")
                .order_by(ChartCalculationRun.created_at.desc())
            )
            if run and run.result:
                calculation = {
                    "chart_id": str(chart.id),
                    "status": run.status,
                    "calculation_system": chart.system,
                    "profile_id": str(chart.profile_id),
                    "division": chart.division,
                    "engine_version": run.engine_version,
                    "ephemeris_version": run.ephemeris_version,
                    "calculated_at": run.created_at.isoformat(),
                    "result": run.result,
                }
    return build_chart_context(profile_data, calculation, chat.astrology_system)


def load_session_chart_facts(db: Session, chat: ChatSession, user: User) -> ChartFacts:
    """Return typed facts through the existing owner-scoped completed-chart lookup."""
    context = load_session_context(db, chat, user)
    return chart_facts_from_context(context, expected_system=chat.astrology_system)
