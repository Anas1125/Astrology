"""Typed research backlog; entries are topics, not astrological interpretations."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Literal

from pydantic import Field, ValidationError

from app.services.ai.contracts import AstrologySystem, StrictModel
from app.services.ai.source_registry import SourceRegistry

DEFAULT_RESEARCH_CATALOGUE = Path(__file__).parent / "knowledge" / "research" / "catalogue.v2.json"


class ResearchCatalogueError(ValueError):
    """A research catalogue is malformed or references unknown sources."""


class ResearchTopic(StrictModel):
    topic_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]+$")
    system: AstrologySystem
    label: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    candidate_source_ids: tuple[str, ...] = Field(min_length=1)
    research_questions: tuple[str, ...] = Field(min_length=1)
    status: Literal["research_only"] = "research_only"
    rule_approval: Literal["not_approved"] = "not_approved"


class ResearchCatalogue(StrictModel):
    catalogue_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    topics: tuple[ResearchTopic, ...] = Field(min_length=1)


def validate_research_catalogue(
    catalogue: ResearchCatalogue,
    registry: SourceRegistry,
) -> ResearchCatalogue:
    if not re.fullmatch(r"\d+\.\d+\.\d+", catalogue.catalogue_version):
        raise ResearchCatalogueError("Invalid research catalogue version")
    source_ids = {source.source_id for source in registry.sources}
    seen: set[str] = set()
    for topic in catalogue.topics:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]+", topic.topic_id):
            raise ResearchCatalogueError(f"Invalid topic ID: {topic.topic_id}")
        if topic.topic_id in seen:
            raise ResearchCatalogueError(f"Duplicate topic ID: {topic.topic_id}")
        seen.add(topic.topic_id)
        if topic.status != "research_only" or topic.rule_approval != "not_approved":
            raise ResearchCatalogueError(f"Topic {topic.topic_id} must remain research-only")
        unknown = set(topic.candidate_source_ids) - source_ids
        if unknown:
            raise ResearchCatalogueError(f"Topic {topic.topic_id} references unknown sources: {sorted(unknown)}")
        if not topic.research_questions:
            raise ResearchCatalogueError(f"Topic {topic.topic_id} needs research questions")
    return catalogue


def load_research_catalogue(
    path: str | Path = DEFAULT_RESEARCH_CATALOGUE,
    *,
    registry: SourceRegistry,
) -> ResearchCatalogue:
    source_path = Path(path)
    try:
        catalogue = ResearchCatalogue.model_validate(json.loads(source_path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise ResearchCatalogueError(f"Invalid research catalogue {source_path}: {exc}") from exc
    return validate_research_catalogue(catalogue, registry)
