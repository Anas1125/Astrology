from datetime import datetime, timezone

import pytest

from app.services.ai.classifier import classify_question
from app.services.ai.contracts import (
    AstrologySystem,
    ChartFact,
    ChartFacts,
    ConversationTurn,
    QuestionTopic,
    UserIntent,
)
from app.services.ai.engine import _resolve_follow_up


def _chart(system="vedic", division="D1"):
    fact = ChartFact(
        subject="Moon", predicate="sign", value="Vrishabha", system=system, division=division,
        source_chart_id="chart-1", profile_id="profile-1",
        provenance="saved_chart:chart-1:Moon.sign",
    )
    return ChartFacts(
        chart_id="chart-1", profile_id="profile-1", system=system, division=division,
        available=True, facts=(fact,),
    )


@pytest.mark.parametrize(
    ("previous", "followup", "language", "topic"),
    [
        ("Where is my Moon in my Vedic chart?", "What about its house?", "en", QuestionTopic.HOUSE),
        ("என் சந்திரன் வேத ஜாதகத்தில் எங்கே?", "அதன் பாவம் என்ன?", "ta", QuestionTopic.HOUSE),
    ],
)
def test_followup_inherits_only_chart_target_from_previous_user_question(previous, followup, language, topic):
    chart = _chart()
    current = classify_question(followup, account_language=language, selected_system="vedic",
                                selected_division="D1", chart_available=True)
    resolved = _resolve_follow_up(
        followup, current,
        (ConversationTurn(role="user", content=previous,
                          created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),),
        selected_system=AstrologySystem.VEDIC, chart=chart,
    )
    assert resolved.intent is UserIntent.CHART_QUESTION
    assert resolved.topic is topic
    assert [(item.kind, item.name) for item in resolved.entities] == [("planet", "Moon")]
    assert resolved.system is AstrologySystem.VEDIC


def test_followup_does_not_use_assistant_text_as_fact_or_context():
    chart = _chart()
    question = "What about it?"
    current = classify_question(question, selected_system="vedic", selected_division="D1", chart_available=True)
    resolved = _resolve_follow_up(
        question, current,
        (ConversationTurn(role="assistant", content="Moon is in Taurus."),),
        selected_system=AstrologySystem.VEDIC, chart=chart,
    )
    assert resolved.intent is UserIntent.CLARIFICATION
    assert resolved.entities == ()


def test_followup_does_not_cross_chart_systems():
    chart = _chart(system="western", division="W")
    current = classify_question("What about its house?", selected_system="western",
                                selected_division="W", chart_available=True)
    resolved = _resolve_follow_up(
        "What about its house?", current,
        (ConversationTurn(role="user", content="Where is my Moon in my Vedic chart?"),),
        selected_system=AstrologySystem.WESTERN, chart=chart,
    )
    assert resolved.entities == current.entities
    assert resolved.system is current.system
