"""Typed, versioned bibliographic registry for sourced astrology research."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
import re

from pydantic import Field, ValidationError

from app.services.ai.contracts import AstrologySystem, InterpretationRule, StrictModel, SupportedLanguage

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
DEFAULT_SOURCE_REGISTRY = Path(__file__).parent / "knowledge" / "sources" / "registry.v1.json"


class SourceRegistryError(ValueError):
    """A source registry or rule-to-source relationship is invalid."""


class DigitalLocation(StrictModel):
    url: str = Field(min_length=8)
    location_type: str = Field(min_length=1)
    access_status: str = Field(min_length=1)
    completeness: str = Field(min_length=1)
    terms_note: str = Field(min_length=1)


class CopyrightAssessment(StrictModel):
    original_text_status: str = Field(min_length=1)
    translation_status: str = Field(min_length=1)
    digital_edition_terms: str = Field(min_length=1)
    short_excerpt_reuse_allowed: bool
    adaptation_reuse_status: str = Field(min_length=1)
    commercial_reuse_status: str = Field(min_length=1)
    legal_review_required: bool
    notes: tuple[str, ...] = ()


class BibliographicSource(StrictModel):
    source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]+$")
    edition_id: str = Field(min_length=1)
    original_title: str = Field(min_length=1)
    author_or_traditional_attribution: str = Field(min_length=1)
    system: AstrologySystem
    tradition: str = Field(min_length=1)
    historical_period: str = Field(min_length=1)
    historical_period_confidence: str = Field(min_length=1)
    original_language: str = Field(min_length=1)
    edition: str = Field(min_length=1)
    translator_editor: str = Field(min_length=1)
    publication: str = Field(min_length=1)
    publication_date: str = Field(min_length=1)
    accessible_locations: tuple[DigitalLocation, ...] = ()
    copyright: CopyrightAssessment
    reliability_notes: tuple[str, ...] = Field(min_length=1)
    verification_notes: tuple[str, ...] = Field(min_length=1)
    relevant_topics: tuple[str, ...] = Field(min_length=1)
    citation_format: str = Field(min_length=1)


class SourceRegistry(StrictModel):
    registry_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    sources: tuple[BibliographicSource, ...] = Field(min_length=1)


def validate_source_registry(registry: SourceRegistry) -> SourceRegistry:
    if not VERSION_RE.fullmatch(registry.registry_version):
        raise SourceRegistryError("Invalid source registry version")
    seen: set[str] = set()
    for source in registry.sources:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]+", source.source_id):
            raise SourceRegistryError(f"Invalid source ID: {source.source_id}")
        if source.source_id in seen:
            raise SourceRegistryError(f"Duplicate source ID: {source.source_id}")
        seen.add(source.source_id)
        if not source.accessible_locations and not any(
            "no full-text link" in note.casefold() or "no verified digital text" in note.casefold()
            for note in source.verification_notes
        ):
            raise SourceRegistryError(f"Source {source.source_id} must document digital-text availability")
        if source.copyright.short_excerpt_reuse_allowed and source.copyright.legal_review_required:
            raise SourceRegistryError(
                f"Source {source.source_id} cannot permit excerpt reuse while rights remain under legal review"
            )
    return registry


def load_source_registry(path: str | Path = DEFAULT_SOURCE_REGISTRY) -> SourceRegistry:
    source_path = Path(path)
    try:
        raw = json.loads(source_path.read_text(encoding="utf-8"))
        registry = SourceRegistry.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise SourceRegistryError(f"Invalid source registry {source_path}: {exc}") from exc
    return validate_source_registry(registry)


@lru_cache(maxsize=1)
def get_default_source_registry() -> SourceRegistry:
    return load_source_registry()


def validate_provenance_source_link(
    provenance,
    registry: SourceRegistry,
    *,
    rule_id: str = "rule",
    system: AstrologySystem | None = None,
) -> None:
    if provenance.editorial_status != "approved":
        if provenance.source_id is not None and provenance.source_id not in {source.source_id for source in registry.sources}:
            raise SourceRegistryError(f"Rule {rule_id} references an unknown source ID")
        return
    source = next((item for item in registry.sources if item.source_id == provenance.source_id), None)
    if source is None:
        if provenance.source_id is None:
            raise SourceRegistryError(f"Approved rule {rule_id} must reference a registered source ID")
        raise SourceRegistryError(f"Approved rule {rule_id} references an unknown source ID")
    if provenance.edition_id != source.edition_id or provenance.edition != source.edition:
        raise SourceRegistryError(f"Approved rule {rule_id} must identify the registered edition")
    if provenance.source_registry_version != registry.registry_version:
        raise SourceRegistryError(f"Approved rule {rule_id} must identify the source registry version")
    if system is not None and source.system is not system:
        raise SourceRegistryError(f"Approved rule {rule_id} source tradition does not match its astrology system")
    if provenance.supporting_excerpt and not source.copyright.short_excerpt_reuse_allowed:
        raise SourceRegistryError(f"Rule {rule_id} includes an excerpt without verified reuse permission")


def validate_rule_source_link(rule: InterpretationRule, registry: SourceRegistry) -> None:
    validate_provenance_source_link(rule.provenance, registry, rule_id=rule.rule_id, system=rule.system)


def validate_approved_rule_metadata(rule: InterpretationRule) -> None:
    provenance = rule.provenance
    if provenance.editorial_status != "approved":
        return
    if getattr(rule.review_status, "value", rule.review_status) not in {"approved", "retired"}:
        raise SourceRegistryError(f"Approved rule {rule.rule_id} has not completed the review workflow")
    if rule.system is None:
        raise SourceRegistryError(f"Approved rule {rule.rule_id} must name its astrology system")
    valid_divisions = {"D1", "D9"} if rule.system is AstrologySystem.VEDIC else {"W", "natal", "NATAL"}
    if rule.division not in valid_divisions:
        raise SourceRegistryError(f"Approved rule {rule.rule_id} must name its applicable chart division")
    required_steps = {"source_verified", "editorial_review_pending", "translation_review_pending", "approved"}
    recorded_steps = {getattr(event.status, "value", event.status) for event in rule.review_events}
    if not required_steps.issubset(recorded_steps):
        raise SourceRegistryError(f"Approved rule {rule.rule_id} lacks a complete review history")
    if not all((provenance.source_id, provenance.source_registry_version, provenance.edition_id, provenance.edition)):
        raise SourceRegistryError(f"Approved rule {rule.rule_id} needs source and edition identifiers")
    if not any((provenance.chapter, provenance.verse, provenance.page, provenance.section)):
        raise SourceRegistryError(f"Approved rule {rule.rule_id} needs an exact passage locator")
    if not all((provenance.editorial_explanation, provenance.editorial_reviewer, provenance.translation_reviewer)):
        raise SourceRegistryError(f"Approved rule {rule.rule_id} needs editorial and translation review metadata")
    if provenance.reviewed_at is None or provenance.translation_review_status != "reviewed":
        raise SourceRegistryError(f"Approved rule {rule.rule_id} is missing completed review metadata")
    if not provenance.source_verifier or provenance.source_verified_at is None:
        raise SourceRegistryError(f"Approved rule {rule.rule_id} is missing source verification metadata")
    if set(rule.translations) != {SupportedLanguage.EN, SupportedLanguage.TA}:
        raise SourceRegistryError(f"Approved rule {rule.rule_id} must provide English and Tamil text")
    if any(not text.strip() for text in rule.translations.values()):
        raise SourceRegistryError(f"Approved rule {rule.rule_id} has empty localized text")
    if rule.translations.get(rule.language) != rule.text:
        raise SourceRegistryError(f"Approved rule {rule.rule_id} text must match its declared language")
