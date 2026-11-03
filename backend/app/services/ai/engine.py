"""Provider-independent orchestration for deterministic astrology responses."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Sequence

from sqlalchemy.orm import Session

from app.models.entities import ChatSession, User
from app.services.ai.classifier import CLASSIFIER_VERSION, classify_question, detect_language
from app.services.ai.contracts import (
    AstrologyIntelligence,
    AstrologySystem,
    ChartFacts,
    ConversationTurn,
    IntelligenceResponse,
    QuestionClassification,
    SupportedLanguage,
    UserIntent,
)
from app.services.ai.knowledge_loader import load_knowledge_base
from app.services.ai.response_composer import ENGINE_VERSION, compose_response
from app.services.ai.rule_matcher import match_interpretation_rules

KNOWLEDGE_DIRECTORY = Path(__file__).parent / "knowledge" / "v1"


def _general_concept_question(question: str) -> bool:
    """Recognize explicit definition prompts that need general-source rules."""
    text = question.strip().casefold()
    if any(marker in text for marker in ("my ", "mine", "என்", "என்னுடைய", "எனது")):
        return False
    english_starts = ("what is ", "what are ", "define ", "explain the concept of ", "meaning of ")
    tamil_patterns = ("என்றால் என்ன", "என்பது என்ன", "என்றால் எது")
    return text.startswith(english_starts) or any(pattern in text for pattern in tamil_patterns)


def _classify(
    question: str,
    *,
    language: SupportedLanguage,
    selected_system: AstrologySystem,
    chart: ChartFacts,
) -> QuestionClassification:
    classification = classify_question(
        question,
        account_language=language.value,
        selected_system=selected_system,
        selected_division=chart.division if chart.available else None,
        chart_available=chart.available,
    )
    if _general_concept_question(question) and classification.intent in {
        UserIntent.CHART_QUESTION,
        UserIntent.MISSING_CHART,
    }:
        return classification.model_copy(update={
            "intent": UserIntent.UNSUPPORTED,
            "system": None,
            "division": None,
            "clarification_reason": "general_knowledge_not_approved",
            "needs_clarification": False,
        })
    return classification


class DeterministicAstrologyIntelligence(AstrologyIntelligence):
    """Load reviewed rules, match saved facts and return a validated response."""

    def __init__(self, knowledge_directory: str | Path = KNOWLEDGE_DIRECTORY):
        self.knowledge_directory = Path(knowledge_directory)

    def answer(
        self,
        question: str,
        *,
        language: SupportedLanguage,
        classification: QuestionClassification,
        chart: ChartFacts | None,
        history: Sequence[ConversationTurn] = (),
    ) -> IntelligenceResponse:
        # History remains available and persisted, but is not used to infer facts
        # or resolve ambiguous references in this version.
        del question, history
        knowledge_version, rules = load_knowledge_base(self.knowledge_directory)
        matches = None
        if classification.intent is UserIntent.CHART_QUESTION and chart is not None and chart.available:
            matches = match_interpretation_rules(
                classification, chart, rules, language=language, allow_test_only=False,
            )
        return compose_response(
            classification,
            chart,
            matches,
            language=language,
            knowledge_base_version=knowledge_version,
            engine_version=ENGINE_VERSION,
        )

    def answer_for_session(
        self,
        db: Session,
        chat: ChatSession,
        user: User,
        question: str,
        *,
        history: Sequence[ConversationTurn] = (),
    ) -> IntelligenceResponse:
        """Retrieve only this user's completed saved chart before answering."""
        from app.services.ai.chat import load_session_chart_facts

        chart = load_session_chart_facts(db, chat, user)
        language = detect_language(question, chat.language)
        classification = _classify(
            question,
            language=language,
            selected_system=AstrologySystem(chat.astrology_system),
            chart=chart,
        )
        return self.answer(
            question,
            language=language,
            classification=classification,
            chart=chart,
            history=history,
        )


@lru_cache(maxsize=1)
def get_intelligence_engine() -> DeterministicAstrologyIntelligence:
    return DeterministicAstrologyIntelligence()


def engine_version() -> str:
    return f"deterministic-ai/{ENGINE_VERSION};classifier/{CLASSIFIER_VERSION}"
