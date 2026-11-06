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
from app.services.ai.general_knowledge import general_overview
from app.services.ai.response_composer import ENGINE_VERSION, compose_response
from app.services.ai.rule_matcher import match_interpretation_rules
from app.services.ai.source_registry import DEFAULT_SOURCE_REGISTRY

KNOWLEDGE_DIRECTORY = Path(__file__).parent / "knowledge" / "v1"


def _is_tamil_personal_moon_explanation(question: str) -> bool:
    """Recognize common inflected Tamil forms in personal Moon questions."""
    normalized = " ".join(question.casefold().split())
    has_personal_reference = any(
        marker in normalized for marker in ("எனது", "என்னுடைய", "என் ", "எனக்கான")
    )
    has_moon_reference = any(
        marker in normalized for marker in ("சந்திரனை", "சந்திரனின்", "சந்திரனுக்கு", "சந்திரன்")
    )
    has_explanation_request = any(
        marker in normalized for marker in ("விளக்கு", "விளக்க", "விவரி", "பற்றி", "சொல்லு", "கூறு", "எப்படி")
    )
    return has_personal_reference and has_moon_reference and has_explanation_request


def _classify(
    question: str,
    *,
    language: SupportedLanguage,
    selected_system: AstrologySystem,
    chart: ChartFacts,
) -> QuestionClassification:
    # The classifier currently handles the English form "explain my Moon"
    # but misses common Tamil inflections such as "சந்திரனை". Normalize only
    # this narrow personal-chart request; answer language is still detected
    # from the original Tamil message in answer_for_session.
    classifier_question = question
    classifier_language = language.value
    if language.value == "ta" and _is_tamil_personal_moon_explanation(question):
        classifier_question = "explain my Moon"
        classifier_language = "en"

    classification = classify_question(
        classifier_question,
        account_language=classifier_language,
        selected_system=selected_system,
        selected_division=chart.division if chart.available else None,
        chart_available=chart.available,
    )
    return classification

_FOLLOW_UP_MARKERS = (
    "what about", "and what", "what does that", "what does it", "its house", "their house",
    "tell me more", "இதன்", "அதன்", "அது", "மேலும் சொல்லுங்கள்", "அப்படியானால்",
)
_GENERAL_FOLLOW_UP_MARKERS = (
    "what about", "tell me more", "explain more", "and this", "இதன்", "அது", "மேலும் சொல்லுங்கள்", "விரிவாக சொல்லுங்கள்",
)


def _resolve_general_education_follow_up(
    question: str,
    classification: QuestionClassification,
    history: Sequence[ConversationTurn],
    *,
    selected_system: AstrologySystem,
    chart: ChartFacts,
) -> QuestionClassification:
    """Resolve educational follow-ups from prior user-authored subjects only."""
    normalized = question.casefold()
    is_ruling_pronoun = any(marker in normalized for marker in (
        "its ruling planet", "its ruling lord", "what is its", "அதன் அதிபதி", "அதற்கு உரிய கிரகம்",
    ))
    is_follow_up = is_ruling_pronoun or any(marker in normalized for marker in _GENERAL_FOLLOW_UP_MARKERS)
    if not is_follow_up and classification.intent is not UserIntent.GENERAL_EDUCATION:
        return classification

    prior_subject: str | None = None
    prior_general: QuestionClassification | None = None
    for turn in reversed(history):
        if turn.role != "user":
            continue
        candidate = _classify(
            turn.content,
            language=detect_language(turn.content),
            selected_system=selected_system,
            chart=chart,
        )
        if candidate.intent is UserIntent.GENERAL_EDUCATION:
            if prior_general is None:
                prior_general = candidate
            if candidate.education_subject:
                prior_subject = candidate.education_subject
                break

    if classification.intent is UserIntent.GENERAL_EDUCATION:
        if classification.education_subject or not prior_subject:
            return classification
        # Carry a named educational subject into contextual methodology
        # questions, while keeping the response unpersonalized.
        return classification.model_copy(update={"education_subject": prior_subject})

    if not is_ruling_pronoun and prior_general and classification.intent in {
        UserIntent.CLARIFICATION, UserIntent.UNSUPPORTED,
    }:
        return prior_general.model_copy(update={"confidence": min(0.85, prior_general.confidence)})

    if not is_ruling_pronoun or classification.intent not in {
        UserIntent.CLARIFICATION, UserIntent.UNSUPPORTED, UserIntent.MISSING_CHART,
    } or not prior_subject:
        return classification

    return QuestionClassification(
        intent=UserIntent.GENERAL_EDUCATION,
        topic=classification.topic,
        education_topic="nakshatra_ruling_planet",
        education_subject=prior_subject,
        confidence=0.9,
    )


def _resolve_follow_up(
    question: str,
    classification: QuestionClassification,
    history: Sequence[ConversationTurn],
    *,
    selected_system: AstrologySystem,
    chart: ChartFacts,
) -> QuestionClassification:
    """Resolve a narrow follow-up from the last user question only.

    Assistant text is intentionally ignored. Current explicit entities remain
    authoritative; only absent target entities are inherited.
    """
    if not chart.available or not any(marker in question.casefold() for marker in _FOLLOW_UP_MARKERS):
        return classification
    previous = next((turn for turn in reversed(history) if turn.role == "user"), None)
    if previous is None:
        return classification
    prior = _classify(
        previous.content,
        language=detect_language(previous.content),
        selected_system=selected_system,
        chart=chart,
    )
    if prior.intent is not UserIntent.CHART_QUESTION or prior.system is not chart.system:
        return classification
    if classification.system is not None and classification.system is not prior.system:
        return classification

    target_kinds = {"planet", "sign", "house", "nakshatra", "dasha_lord", "aspect"}
    inherited = [entity for entity in prior.entities if entity.kind in target_kinds]
    explicit = [entity for entity in classification.entities if entity.kind in target_kinds]
    if explicit:
        inherited = [entity for entity in inherited if entity.kind not in {item.kind for item in explicit}]
    entities = tuple((*explicit, *inherited))
    if not entities and classification.intent is not UserIntent.CLARIFICATION:
        return classification
    return classification.model_copy(update={
        "intent": UserIntent.CHART_QUESTION,
        "system": classification.system or prior.system,
        "division": classification.division or prior.division or chart.division,
        "topic": classification.topic or prior.topic,
        "entities": entities,
        "needs_clarification": False,
        "clarification_reason": None,
        "confidence": min(classification.confidence, prior.confidence),
    })


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
        # History is not a source of chart facts. Narrow follow-up resolution
        # happens in answer_for_session using the prior user question only.
        del question, history
        knowledge_version, rules = load_knowledge_base(
            self.knowledge_directory,
            source_registry=DEFAULT_SOURCE_REGISTRY,
        )
        matches = None
        education_text = None
        if classification.intent is UserIntent.GENERAL_EDUCATION and classification.education_topic:
            overview = general_overview(
                classification.education_topic, language.value,
                subject=classification.education_subject,
            )
            if overview is not None:
                education_text, knowledge_version = overview
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
            general_education_text=education_text,
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
        classification = _resolve_general_education_follow_up(
            question,
            classification,
            history,
            selected_system=AstrologySystem(chat.astrology_system),
            chart=chart,
        )
        classification = _resolve_follow_up(
            question,
            classification,
            history,
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
