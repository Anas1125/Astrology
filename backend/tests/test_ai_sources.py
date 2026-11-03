import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.services.ai.contracts import (
    AstrologySystem,
    ChartFact,
    ChartFacts,
    InterpretationRule,
    MentionedEntity,
    QuestionClassification,
    RuleProvenance,
    RuleReviewEvent,
    RuleReviewStatus,
    SupportedLanguage,
)
from app.services.ai.knowledge_loader import KnowledgeBaseError, load_knowledge_base
from app.services.ai.research_catalogue import (
    ResearchCatalogueError,
    load_research_catalogue,
    validate_research_catalogue,
)
from app.services.ai.rule_matcher import match_interpretation_rules
from app.services.ai.source_registry import (
    DEFAULT_SOURCE_REGISTRY,
    SourceRegistry,
    SourceRegistryError,
    load_source_registry,
    validate_rule_source_link,
    validate_source_registry,
)


def _approved_rule(*, translations=None, **provenance_overrides):
    provenance = {
        "source_name": "William Lilly, Christian Astrology",
        "attribution": "William Lilly",
        "reference": "Book I, chapter fixture, printed page fixture",
        "editorial_status": "approved",
        "classification": "traditional_interpretation",
        "source_id": "western.christian-astrology.lilly.1647",
        "source_registry_version": "1.0.0",
        "edition_id": "christian-astrology-lilly-original-1647",
        "edition": "Original 1647 edition in three books; book III has a separate title page. Wellcome's digitized copy is missing its last leaf.",
        "chapter": "fixture chapter locator",
        "citation_note": "Test-only locator; not a source claim.",
        "editorial_explanation": "TEST RULE ONLY; no substantive claim.",
        "editorial_reviewer": "Test editorial reviewer",
        "translation_reviewer": "Test Tamil reviewer",
        "reviewed_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "translation_review_status": "reviewed",
        "source_verifier": "Fixture source reviewer (test only)",
        "source_verified_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    provenance.update(provenance_overrides)
    return InterpretationRule(
        rule_id="reviewed.fixture.moon-sign",
        rule_version="1.0.0",
        knowledge_base_version="1.0.0",
        system="western",
        division="W",
        language="en",
        topics=("planet",),
        required_entities=(MentionedEntity(kind="planet", name="Moon"),),
        conditions=({"field": "Moon.sign", "equals": "Taurus"},),
        text="TEST FIXTURE ONLY — no interpretation claim.",
        translations=(
            {"en": "TEST FIXTURE ONLY — no interpretation claim.", "ta": "சோதனை உரை மட்டும்."}
            if translations is None else translations
        ),
        confidence="editorial_low",
        provenance=RuleProvenance(**provenance),
        review_status=RuleReviewStatus.APPROVED,
        review_events=tuple(RuleReviewEvent(
            status=step,
            reviewer={
                RuleReviewStatus.SOURCE_VERIFIED: "Fixture source reviewer (test only)",
                RuleReviewStatus.EDITORIAL_REVIEW_PENDING: "Test editorial reviewer",
                RuleReviewStatus.TRANSLATION_REVIEW_PENDING: "Test Tamil reviewer",
                RuleReviewStatus.APPROVED: "Fixture approver (test only)",
            }[step],
            occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            note="Test fixture only; no real review occurred.",
        ) for step in (
            RuleReviewStatus.SOURCE_VERIFIED,
            RuleReviewStatus.EDITORIAL_REVIEW_PENDING,
            RuleReviewStatus.TRANSLATION_REVIEW_PENDING,
            RuleReviewStatus.APPROVED,
        )),
    )


def test_checked_in_source_registry_has_unique_complete_source_records():
    registry = load_source_registry()
    assert registry.registry_version == "1.0.0"
    assert len(registry.sources) == 5
    assert len({source.source_id for source in registry.sources}) == 5
    assert {source.system for source in registry.sources} == {AstrologySystem.VEDIC, AstrologySystem.WESTERN}
    for source in registry.sources:
        assert source.original_title and source.author_or_traditional_attribution
        assert source.edition_id and source.edition and source.translator_editor
        assert source.publication and source.publication_date and source.citation_format
        assert source.reliability_notes and source.verification_notes and source.relevant_topics


def test_source_registry_rejects_duplicate_ids_and_missing_bibliographic_fields():
    registry = load_source_registry()
    duplicate = registry.model_copy(update={"sources": (registry.sources[0], registry.sources[0])})
    with pytest.raises(SourceRegistryError, match="Duplicate source ID"):
        validate_source_registry(duplicate)
    raw = registry.model_dump(mode="json")
    del raw["sources"][0]["publication"]
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(raw)
    raw = registry.model_dump(mode="json")
    raw["sources"][0]["publication"] = ""
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(raw)
    raw = registry.model_dump(mode="json")
    raw["registry_version"] = "unversioned"
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(raw)


def test_unverified_dates_access_and_rights_are_explicit_in_registry():
    registry = load_source_registry()
    bphs = next(item for item in registry.sources if item.source_id.startswith("vedic.bphs."))
    phaladeepika = next(item for item in registry.sources if item.source_id.startswith("vedic.phaladeepika."))
    saravali = next(item for item in registry.sources if item.source_id.startswith("vedic.saravali."))
    lilly = next(item for item in registry.sources if item.source_id.startswith("western.christian-astrology."))
    assert bphs.historical_period_confidence == "uncertain_textual_history"
    assert any("not verified" in note.casefold() or "not established" in note.casefold()
               or "no stable" in note.casefold() for note in bphs.verification_notes)
    assert phaladeepika.copyright.legal_review_required
    assert not phaladeepika.copyright.short_excerpt_reuse_allowed
    assert not saravali.accessible_locations or all(
        location.completeness == "catalog_only" for location in saravali.accessible_locations
    )
    assert lilly.accessible_locations[0].completeness.endswith("last_leaf_wanting")
    assert lilly.copyright.legal_review_required


def test_approved_rule_must_link_to_registered_source_and_exact_edition():
    registry = load_source_registry()
    rule = _approved_rule()
    validate_rule_source_link(rule, registry)
    unknown = rule.model_copy(update={
        "provenance": rule.provenance.model_copy(update={"source_id": "western.unknown"})
    })
    with pytest.raises(SourceRegistryError, match="unknown source ID"):
        validate_rule_source_link(unknown, registry)
    wrong_edition = rule.model_copy(update={
        "provenance": rule.provenance.model_copy(update={"edition_id": "other-edition"})
    })
    with pytest.raises(SourceRegistryError, match="registered edition"):
        validate_rule_source_link(wrong_edition, registry)
    wrong_system = rule.model_copy(update={"system": "vedic"})
    with pytest.raises(SourceRegistryError, match="tradition does not match"):
        validate_rule_source_link(wrong_system, registry)
    wrong_registry_version = rule.model_copy(update={
        "provenance": rule.provenance.model_copy(update={"source_registry_version": "2.0.0"})
    })
    with pytest.raises(SourceRegistryError, match="source registry version"):
        validate_rule_source_link(wrong_registry_version, registry)


def test_excerpt_is_blocked_without_explicit_reuse_permission():
    registry = load_source_registry()
    excerpt_rule = _approved_rule(supporting_excerpt="Short test excerpt.")
    with pytest.raises(SourceRegistryError, match="without verified reuse permission"):
        validate_rule_source_link(excerpt_rule, registry)


@pytest.mark.parametrize(
    "changes",
    [
        {"translations": {"en": "English only"}},
        {"translation_review_status": "unreviewed"},
        {"editorial_reviewer": None},
        {"reviewed_at": None},
    ],
)
def test_approved_rule_requires_bilingual_content_and_review_metadata(changes):
    rule = _approved_rule()
    if "translations" in changes:
        invalid = rule.model_copy(update={"translations": changes["translations"]})
        with pytest.raises(SourceRegistryError, match="English and Tamil"):
            from app.services.ai.source_registry import validate_approved_rule_metadata
            validate_approved_rule_metadata(invalid)
    else:
        invalid = rule.model_copy(update={
            "provenance": rule.provenance.model_copy(update=changes)
        })
        from app.services.ai.source_registry import validate_approved_rule_metadata
        with pytest.raises(SourceRegistryError):
            validate_approved_rule_metadata(invalid)


def test_knowledge_loader_remains_backward_compatible_with_test_only_fixtures():
    version, rules = load_knowledge_base("app/services/ai/knowledge/v1")
    assert version == "1.0.0" and len(rules) == 3
    assert all(rule.provenance.editorial_status == "test_only" for rule in rules)


def test_knowledge_loader_validates_rule_source_link_when_registry_is_supplied(tmp_path):
    rule = _approved_rule()
    document = {"knowledge_base_version": "1.0.0", "rules": [rule.model_dump(mode="json")]}
    knowledge_file = tmp_path / "rules.json"
    knowledge_file.write_text(json.dumps(document), encoding="utf-8")
    _, rules = load_knowledge_base(knowledge_file, source_registry=DEFAULT_SOURCE_REGISTRY)
    assert rules[0].provenance.source_id == "western.christian-astrology.lilly.1647"
    raw = json.loads(knowledge_file.read_text(encoding="utf-8"))
    raw["rules"][0]["provenance"]["source_id"] = "western.not-registered"
    knowledge_file.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(KnowledgeBaseError, match="unknown source ID"):
        load_knowledge_base(knowledge_file, source_registry=DEFAULT_SOURCE_REGISTRY)


def test_matcher_excludes_approved_rule_without_source_review_and_bilingual_metadata():
    chart = ChartFacts(
        chart_id="chart-1", profile_id="profile-1", system="western", division="W", available=True,
        facts=(ChartFact(subject="Moon", predicate="sign", value="Taurus", system="western", division="W",
                         source_chart_id="chart-1", profile_id="profile-1", provenance="saved_chart:chart-1:Moon.sign"),),
    )
    question = QuestionClassification(
        intent="chart_question", system="western", division="W", topic="planet", confidence=1,
        entities=(MentionedEntity(kind="planet", name="Moon"),),
    )
    incomplete = _approved_rule(translations={})
    result = match_interpretation_rules(question, chart, (incomplete,), language=SupportedLanguage.EN)
    assert result.matches == ()
    assert result.skipped[0].reason == "inadequate_rule_provenance"


def test_matcher_selects_reviewed_tamil_text_from_a_bilingual_registered_rule():
    chart = ChartFacts(
        chart_id="chart-1", profile_id="profile-1", system="western", division="W", available=True,
        facts=(ChartFact(subject="Moon", predicate="sign", value="Taurus", system="western", division="W",
                         source_chart_id="chart-1", profile_id="profile-1", provenance="saved_chart:chart-1:Moon.sign"),),
    )
    question = QuestionClassification(
        intent="chart_question", system="western", division="W", topic="planet", confidence=1,
        entities=(MentionedEntity(kind="planet", name="Moon"),),
    )
    rule = _approved_rule()
    result = match_interpretation_rules(question, chart, (rule,), language=SupportedLanguage.TA)
    assert len(result.matches) == 1
    assert result.matches[0].language is SupportedLanguage.TA
    assert result.matches[0].text == rule.translations[SupportedLanguage.TA]


def test_research_catalogue_is_research_only_and_references_registered_sources():
    registry = load_source_registry()
    catalogue = load_research_catalogue(registry=registry)
    assert len(catalogue.topics) == 81
    topic_ids = {topic.topic_id for topic in catalogue.topics}
    assert "vedic.graha.rahu-significations" in topic_ids
    assert "vedic.rashi.pisces" in topic_ids
    assert "vedic.bhava.12" in topic_ids
    assert "vedic.d1-d9" in topic_ids
    assert "western.traditional-planet.saturn" in topic_ids
    assert "western.aspect.opposition" in topic_ids
    assert all(item.status == "research_only" and item.rule_approval == "not_approved" for item in catalogue.topics)
    tampered = catalogue.model_copy(update={"topics": (catalogue.topics[0].model_copy(update={"rule_approval": "approved"}),)})
    with pytest.raises(ResearchCatalogueError, match="research-only"):
        validate_research_catalogue(tampered, registry)
    unknown = catalogue.model_copy(update={
        "topics": (catalogue.topics[0].model_copy(update={"candidate_source_ids": ("unknown.source",)}),)
    })
    with pytest.raises(ResearchCatalogueError, match="unknown sources"):
        validate_research_catalogue(unknown, registry)
