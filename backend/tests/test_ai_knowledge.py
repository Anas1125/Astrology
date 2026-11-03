import json

import pytest

from app.services.ai.contracts import (
    AstrologySystem,
    ChartFact,
    ChartFacts,
    IntelligenceResponse,
    IntelligenceResponseMetadata,
    MentionedEntity,
    QuestionClassification,
    QuestionTopic,
    ResponseSection,
    ResponseSectionType,
    ResponseStatus,
    SupportedLanguage,
)
from app.services.ai.knowledge_loader import KnowledgeBaseError, load_knowledge_base
from app.services.ai.rule_matcher import match_interpretation_rules

KNOWLEDGE_DIR = "app/services/ai/knowledge/v1"


def _rule(**overrides):
    rule = {
        "rule_id": "test-only.rule.example",
        "rule_version": "1.0.0",
        "knowledge_base_version": "1.0.0",
        "system": "vedic",
        "language": "en",
        "topics": ["planet"],
        "required_entities": [{"kind": "planet", "name": "Moon"}],
        "conditions": [{"field": "Moon.sign", "equals": "Taurus"}],
        "text": "TEST FIXTURE ONLY — not an astrology interpretation.",
        "confidence": "editorial_low",
        "provenance": {
            "source_name": "AstroAI schema fixture",
            "attribution": "AstroAI test authors",
            "reference": "tests/fixtures/knowledge-base",
            "editorial_status": "test_only",
            "classification": "traditional_interpretation",
        },
    }
    rule.update(overrides)
    return rule


def _write_file(tmp_path, document, name="rules.json"):
    path = tmp_path / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_checked_in_test_only_knowledge_fixtures_validate_and_cover_languages():
    version, rules = load_knowledge_base(KNOWLEDGE_DIR)
    assert version == "1.0.0"
    assert len(rules) == 3
    assert {rule.system for rule in rules} == {AstrologySystem.VEDIC, AstrologySystem.WESTERN}
    assert {rule.language for rule in rules} == {SupportedLanguage.EN, SupportedLanguage.TA}
    assert all(rule.provenance.editorial_status == "test_only" for rule in rules)
    assert all("TEST FIXTURE ONLY" in rule.text or "சோதனைக்கான உரை" in rule.text for rule in rules)


def test_loader_supports_yaml(tmp_path):
    yaml_text = '''
knowledge_base_version: 1.0.0
rules:
  - rule_id: test-only.yaml.example
    rule_version: 1.0.0
    knowledge_base_version: 1.0.0
    system: western
    language: en
    topics: [planet]
    required_entities:
      - kind: planet
        name: Sun
    conditions:
      - field: Sun.sign
        equals: Aries
    text: "TEST FIXTURE ONLY — not an astrology interpretation."
    confidence: editorial_low
    provenance:
      source_name: Schema test
      attribution: Test authors
      reference: tests/test_ai_knowledge.py
      editorial_status: test_only
      classification: traditional_interpretation
'''
    path = tmp_path / "rules.yaml"
    path.write_text(yaml_text, encoding="utf-8")
    version, rules = load_knowledge_base(path)
    assert version == "1.0.0"
    assert rules[0].rule_id == "test-only.yaml.example"


@pytest.mark.parametrize(
    ("rule", "match"),
    [
        ({"rule_id": "test-only.missing.version"}, "Invalid rule"),
        (_rule(language="fr"), "Invalid rule"),
        (_rule(rule_version="latest"), "Invalid rule"),
        ({key: value for key, value in _rule().items() if key != "provenance"}, "Invalid rule"),
        (_rule(provenance={"source_name": "", "attribution": "", "reference": "", "editorial_status": "test_only", "classification": "traditional_interpretation"}), "Invalid rule"),
        (_rule(provenance={"source_name": "X", "attribution": "Y", "reference": "unknown", "editorial_status": "approved", "classification": "traditional_interpretation"}), "inadequate source attribution"),
    ],
)
def test_loader_rejects_invalid_rule_fields_language_versions_and_provenance(tmp_path, rule, match):
    _write_file(tmp_path, {"knowledge_base_version": "1.0.0", "rules": [rule]})
    with pytest.raises(KnowledgeBaseError, match=match):
        load_knowledge_base(tmp_path)


def test_loader_rejects_invalid_knowledge_base_version(tmp_path):
    _write_file(tmp_path, {"knowledge_base_version": "next", "rules": []})
    with pytest.raises(KnowledgeBaseError, match="invalid knowledge_base_version"):
        load_knowledge_base(tmp_path)


def test_loader_rejects_duplicate_identifiers_across_files(tmp_path):
    rule = _rule()
    _write_file(tmp_path, {"knowledge_base_version": "1.0.0", "rules": [rule]}, "one.json")
    _write_file(tmp_path, {"knowledge_base_version": "1.0.0", "rules": [rule]}, "two.json")
    with pytest.raises(KnowledgeBaseError, match="Duplicate rule ID"):
        load_knowledge_base(tmp_path)


def test_loader_rejects_rule_and_document_version_mismatch(tmp_path):
    _write_file(tmp_path, {"knowledge_base_version": "1.0.0", "rules": [_rule(knowledge_base_version="1.1.0")]})
    with pytest.raises(KnowledgeBaseError, match="declares knowledge base version"):
        load_knowledge_base(tmp_path)


def test_loader_rejects_malformed_document(tmp_path):
    (tmp_path / "bad.json").write_text("{not valid", encoding="utf-8")
    with pytest.raises(KnowledgeBaseError, match="Invalid structured data"):
        load_knowledge_base(tmp_path)


def test_rule_matching_requires_every_chart_fact_and_respects_system_and_language(tmp_path):
    _, rules = load_knowledge_base(KNOWLEDGE_DIR)
    chart = ChartFacts(
        chart_id="chart-1",
        profile_id="profile-1",
        system=AstrologySystem.VEDIC,
        division="D1",
        available=True,
        facts=(ChartFact(
            subject="Moon", predicate="sign", value="Vrishabha", system=AstrologySystem.VEDIC,
            division="D1", source_chart_id="chart-1", profile_id="profile-1", provenance="saved_chart:chart-1:planets[0].sign",
        ),),
    )
    question = QuestionClassification(
        intent="chart_question", system="vedic", division="D1", topic=QuestionTopic.PLANET,
        entities=(MentionedEntity(kind="planet", name="Moon"),), confidence=1,
    )
    production = match_interpretation_rules(question, chart, rules, language=SupportedLanguage.EN)
    assert production.matches == ()
    assert any(item.reason == "editorial_status_test_only" for item in production.skipped)
    test_matches = match_interpretation_rules(question, chart, rules, language=SupportedLanguage.EN, allow_test_only=True)
    assert [item.rule_id for item in test_matches.matches] == ["test-only.vedic.placement.example"]
    assert test_matches.matches[0].fact_references[0].source_chart_id == "chart-1"
    assert test_matches.matches[0].fact_references[0].profile_id == "profile-1"
    assert match_interpretation_rules(question, chart, rules, language=SupportedLanguage.TA, allow_test_only=True).matches == ()
    unavailable = chart.model_copy(update={"available": False})
    assert not match_interpretation_rules(question, unavailable, rules, language=SupportedLanguage.EN).eligible


@pytest.mark.parametrize("status", list(ResponseStatus))
def test_typed_intelligence_response_supports_all_contract_statuses(status):
    response = IntelligenceResponse(
        status=status,
        answer="No interpretation rule is available.",
        sections=(ResponseSection(
            section_type=ResponseSectionType.LIMITATION,
            text="No interpretation rule is available.",
        ),),
        metadata=IntelligenceResponseMetadata(
            engine_version="1.0.0", knowledge_base_version="1.0.0", language=SupportedLanguage.EN,
        ),
    )
    assert response.status is status


def test_typed_response_rejects_invalid_section_kind_and_version():
    with pytest.raises(ValueError):
        ResponseSection(section_type="invented", text="not valid")
    with pytest.raises(ValueError):
        IntelligenceResponseMetadata(engine_version="dev", knowledge_base_version="1.0.0", language="en")
