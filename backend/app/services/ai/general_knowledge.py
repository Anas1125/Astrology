"""Versioned, deterministic general astrology education content.

These concise editorial overviews are intentionally not represented as sourced
classical interpretations. The loader requires the explicit unverified status
and rejects citations until a separate source-verification workflow exists.
"""
from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

GENERAL_KNOWLEDGE_PATH = Path(__file__).parent / "knowledge" / "general" / "v1.json"


class GeneralKnowledgeError(ValueError):
    """General educational knowledge is malformed or has false provenance."""


class LocalizedOverview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    en: str = Field(min_length=1, max_length=1000)
    ta: str = Field(min_length=1, max_length=1000)


class GeneralKnowledgeEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    topic_id: str = Field(pattern=r"^[a-z0-9_]+$")
    classification: str = Field(pattern=r"^general_education$")
    editorial_status: str = Field(pattern=r"^editorial_draft$")
    source_verification_status: str = Field(pattern=r"^not_independently_verified$")
    source_references: tuple[str, ...] = ()
    overview: LocalizedOverview


class LocalizedLabel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    en: str = Field(min_length=1, max_length=80)
    ta: str = Field(min_length=1, max_length=80)


class NakshatraSubject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: LocalizedLabel
    ordinal: int = Field(ge=1, le=27)
    ruling_planet: LocalizedLabel


class GeneralKnowledgeDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    knowledge_base_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    entries: tuple[GeneralKnowledgeEntry, ...] = Field(min_length=1)
    nakshatra_subjects: dict[str, NakshatraSubject] = {}


def load_general_knowledge(path: str | Path = GENERAL_KNOWLEDGE_PATH) -> GeneralKnowledgeDocument:
    """Load and strictly validate the bilingual education catalogue."""
    source = Path(path)
    try:
        document = GeneralKnowledgeDocument.model_validate_json(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise GeneralKnowledgeError(f"Cannot read general knowledge file: {source}") from exc
    except (ValueError, ValidationError) as exc:
        raise GeneralKnowledgeError(f"Invalid general knowledge document {source}: {exc}") from exc
    if not re.fullmatch(r"\d+\.\d+\.\d+", document.knowledge_base_version):
        raise GeneralKnowledgeError("Invalid general knowledge version")
    topic_ids = [entry.topic_id for entry in document.entries]
    if len(topic_ids) != len(set(topic_ids)):
        raise GeneralKnowledgeError("Duplicate general knowledge topic ID")
    for entry in document.entries:
        if entry.source_references:
            raise GeneralKnowledgeError(
                f"Unverified general topic {entry.topic_id} cannot claim source references"
            )
        if not entry.overview.en.strip() or not entry.overview.ta.strip():
            raise GeneralKnowledgeError(f"Topic {entry.topic_id} requires English and Tamil content")
    subject_ids = tuple(document.nakshatra_subjects)
    if subject_ids and (
        len(subject_ids) != 27
        or len(set(subject_ids)) != len(subject_ids)
        or {item.ordinal for item in document.nakshatra_subjects.values()} != set(range(1, 28))
    ):
        raise GeneralKnowledgeError("Nakshatra subject catalogue must contain 27 uniquely numbered entries")
    return document


def general_overview(topic_id: str, language: str, subject: str | None = None) -> tuple[str, str] | None:
    """Return (text, version) for a known localized topic, or None."""
    document = load_general_knowledge()
    entry = next((item for item in document.entries if item.topic_id == topic_id), None)
    if entry is None:
        return None
    text = getattr(entry.overview, language)
    if "{" in text:
        item = document.nakshatra_subjects.get(subject or "")
        if item is None:
            return None
        text = text.format(
            name=getattr(item.name, language),
            ordinal=item.ordinal,
            ruler=getattr(item.ruling_planet, language),
        )
    return text, document.knowledge_base_version
