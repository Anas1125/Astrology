"""Typed provider-independent contracts for deterministic astrology intelligence.

These types describe facts, editorial rules, and response structure. They do not
define or imply any astrology interpretation.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol, Sequence

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AstrologySystem(StrEnum):
    VEDIC = "vedic"
    WESTERN = "western"


class SupportedLanguage(StrEnum):
    EN = "en"
    TA = "ta"


class UserIntent(StrEnum):
    GREETING = "greeting"
    CHART_QUESTION = "chart_question"
    CLARIFICATION = "clarification"
    UNSUPPORTED = "unsupported"
    MISSING_CHART = "missing_chart"


class QuestionTopic(StrEnum):
    GENERAL_OVERVIEW = "general_overview"
    PLANET = "planet"
    SIGN = "sign"
    HOUSE = "house"
    NAKSHATRA = "nakshatra"
    PADA = "pada"
    DASHA = "dasha"
    ASPECT = "aspect"
    OTHER = "other"


class MentionedEntity(StrictModel):
    kind: str = Field(pattern=r"^(planet|sign|house|nakshatra|dasha_lord|division|aspect)$")
    name: str


class QuestionClassification(StrictModel):
    intent: UserIntent
    system: AstrologySystem | None = None
    division: str | None = None
    topic: QuestionTopic | None = None
    entities: tuple[MentionedEntity, ...] = ()
    confidence: float = Field(ge=0.0, le=1.0)
    needs_clarification: bool = False
    clarification_reason: str | None = None


class ChartFact(StrictModel):
    """A value already present in a saved calculation; never a calculated result."""

    subject: str
    predicate: str
    value: StrictStr | StrictInt | StrictFloat | StrictBool
    system: AstrologySystem | None = None
    division: str | None = None
    source_chart_id: str
    profile_id: str | None = None
    provenance: str


class ChartFacts(StrictModel):
    chart_id: str | None = None
    profile_id: str | None = None
    system: AstrologySystem | None = None
    division: str | None = None
    available: bool
    facts: tuple[ChartFact, ...] = ()
    missing: tuple[str, ...] = ()
    calculation_engine_version: str | None = None
    ephemeris_version: str | None = None
    calculated_at: datetime | None = None


class ConversationTurn(StrictModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str = Field(min_length=1)
    created_at: datetime | None = None


class RuleCondition(StrictModel):
    """Explicit equality match against one or more required saved fact fields."""

    field: str = Field(min_length=1, max_length=120)
    equals: StrictStr | StrictInt | StrictFloat | StrictBool


class RuleProvenance(StrictModel):
    source_name: str = Field(min_length=1)
    attribution: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    editorial_status: str = Field(pattern=r"^(test_only|draft|reviewed|approved)$")
    classification: str = Field(pattern=r"^traditional_interpretation$")


class InterpretationRule(StrictModel):
    rule_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]+$")
    rule_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    knowledge_base_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    system: AstrologySystem | None = None
    division: str | None = None
    language: SupportedLanguage
    conditions: tuple[RuleCondition, ...] = Field(min_length=1)
    topics: tuple[QuestionTopic, ...] = Field(min_length=1)
    required_entities: tuple[MentionedEntity, ...] = ()
    conflict_group: str | None = None
    text: str = Field(min_length=1)
    confidence: str = Field(pattern=r"^(editorial_low|editorial_medium|editorial_high)$")
    provenance: RuleProvenance


class MatchedInterpretationRule(StrictModel):
    rule_id: str
    rule_version: str
    knowledge_base_version: str
    system: AstrologySystem
    division: str | None = None
    language: SupportedLanguage
    text: str
    confidence: str
    provenance: RuleProvenance
    chart_id: str
    profile_id: str
    fact_references: tuple[MatchedFactReference, ...]


class MatchedFactReference(StrictModel):
    fact_id: str = Field(min_length=1, max_length=512)
    subject: str
    predicate: str
    value: StrictStr | StrictInt | StrictFloat | StrictBool
    source_chart_id: str
    profile_id: str
    system: AstrologySystem
    division: str | None = None
    provenance: str


class RuleSkip(StrictModel):
    rule_id: str
    reason: str


class RuleConflict(StrictModel):
    conflict_group: str
    rule_ids: tuple[str, ...]


class RuleMatchResult(StrictModel):
    chart_id: str | None = None
    profile_id: str | None = None
    eligible: bool
    rejection_reason: str | None = None
    matches: tuple[MatchedInterpretationRule, ...] = ()
    conflicts: tuple[RuleConflict, ...] = ()
    skipped: tuple[RuleSkip, ...] = ()


class ResponseSectionType(StrEnum):
    CALCULATED_FACT = "calculated_fact"
    TRADITIONAL_INTERPRETATION = "traditional_interpretation"
    LIMITATION = "limitation"


class MatchedRuleReference(StrictModel):
    rule_id: str
    rule_version: str
    knowledge_base_version: str
    chart_id: str
    profile_id: str
    system: AstrologySystem
    division: str | None = None
    source_name: str
    attribution: str
    reference: str
    editorial_status: str = Field(pattern=r"^approved$")
    classification: str = Field(pattern=r"^traditional_interpretation$")


class ResponseSection(StrictModel):
    section_type: ResponseSectionType
    text: str = Field(min_length=1)
    fact_ids: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    fact_references: tuple[MatchedFactReference, ...] = ()
    rule_references: tuple[MatchedRuleReference, ...] = ()


class ResponseStatus(StrEnum):
    ANSWERED = "answered"
    MISSING_CHART = "missing_chart"
    UNSUPPORTED = "unsupported"
    NEEDS_CLARIFICATION = "needs_clarification"


class IntelligenceResponseMetadata(StrictModel):
    engine_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    knowledge_base_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    system: AstrologySystem | None = None
    language: SupportedLanguage
    matched_rule_ids: tuple[str, ...] = ()
    division: str | None = None


class IntelligenceResponse(StrictModel):
    status: ResponseStatus
    answer: str = Field(min_length=1, max_length=1000)
    answer_fact_ids: tuple[str, ...] = ()
    answer_rule_ids: tuple[str, ...] = ()
    sections: tuple[ResponseSection, ...] = ()
    metadata: IntelligenceResponseMetadata


class AstrologyIntelligence(Protocol):
    """Synchronous deterministic interface; implementations may be adapted for SSE."""

    def answer(
        self,
        question: str,
        *,
        language: SupportedLanguage,
        classification: QuestionClassification,
        chart: ChartFacts | None,
        history: Sequence[ConversationTurn] = (),
    ) -> IntelligenceResponse: ...
