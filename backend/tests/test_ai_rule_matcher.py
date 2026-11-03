import json

import pytest

from app.services.ai.contracts import (
    AstrologySystem,
    ChartFact,
    ChartFacts,
    InterpretationRule,
    MentionedEntity,
    QuestionClassification,
    RuleProvenance,
    RuleCondition,
    RuleReviewEvent,
    RuleReviewStatus,
    SupportedLanguage,
    UserIntent,
)
from datetime import datetime, timezone
from app.services.ai.knowledge_loader import KnowledgeBaseError, load_knowledge_base
from app.services.ai.rule_matcher import DuplicateRuleID, match_interpretation_rules, validate_rule_conditions


def _fact(subject, predicate, value, *, system="vedic", division="D1", chart_id="chart-1", profile_id="profile-1"):
    return ChartFact(
        subject=subject,
        predicate=predicate,
        value=value,
        system=system,
        division=division,
        source_chart_id=chart_id,
        profile_id=profile_id,
        provenance=f"saved_chart:{chart_id}:{subject}.{predicate}",
    )


def _chart(facts, *, system="vedic", division="D1", chart_id="chart-1", profile_id="profile-1", available=True):
    return ChartFacts(
        chart_id=chart_id,
        profile_id=profile_id,
        system=system,
        division=division,
        available=available,
        facts=tuple(facts),
        calculation_engine_version="fixture-engine/1.0.0",
    )


def _question(*, system="vedic", division="D1", topic="planet", entities=(), intent="chart_question", clarify=False):
    return QuestionClassification(
        intent=intent,
        system=system,
        division=division,
        topic=topic,
        entities=tuple(entities),
        confidence=1.0,
        needs_clarification=clarify,
    )


def _rule(
    rule_id,
    field,
    value,
    *,
    system="vedic",
    division="D1",
    topic="planet",
    entity=None,
    status="test_only",
    conflict_group=None,
    reference="tests/test_ai_rule_matcher.py schema fixture",
):
    return InterpretationRule(
        rule_id=rule_id,
        rule_version="1.0.0",
        knowledge_base_version="1.0.0",
        system=system,
        division=division,
        language="en",
        conditions=({"field": field, "equals": value},),
        topics=(topic,),
        required_entities=({"kind": entity[0], "name": entity[1]},) if entity else (),
        conflict_group=conflict_group,
        text="TEST FIXTURE ONLY — not an astrology interpretation.",
        confidence="editorial_low",
        provenance=RuleProvenance(
            source_name="AstroAI test fixture",
            attribution="Test authors",
            reference=reference,
            editorial_status=status,
            classification="traditional_interpretation",
            **({
                "source_id": ("vedic.phaladeepika.sastri.1950-en" if system == "vedic" else "western.christian-astrology.lilly.1647"),
                "source_registry_version": "1.0.0",
                "edition_id": ("phaladeepika-sastri-2e-1950" if system == "vedic" else "christian-astrology-lilly-original-1647"),
                "edition": ("Second edition, revised and enlarged; Sanskrit text with English translation, chapters I–XXVIII."
                            if system == "vedic" else
                            "Original 1647 edition in three books; book III has a separate title page. Wellcome's digitized copy is missing its last leaf."),
                "chapter": "fixture chapter",
                "editorial_explanation": "Test fixture only; no claim is asserted.",
                "editorial_reviewer": "Test reviewer",
                "translation_reviewer": "Test translator reviewer",
                "reviewed_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "translation_review_status": "reviewed",
                "source_verifier": "Fixture source reviewer (test only)",
                "source_verified_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            } if status == "approved" else {}),
        ),
        translations=({"en": "TEST FIXTURE ONLY — not an astrology interpretation.",
                       "ta": "சோதனை உரை மட்டும் — ஜோதிட விளக்கம் அல்ல."} if status == "approved" else {}),
        review_status=RuleReviewStatus.APPROVED if status == "approved" else RuleReviewStatus.RESEARCH_CANDIDATE,
        review_events=(tuple(RuleReviewEvent(
            status=step,
            reviewer={
                RuleReviewStatus.SOURCE_VERIFIED: "Fixture source reviewer (test only)",
                RuleReviewStatus.EDITORIAL_REVIEW_PENDING: "Test reviewer",
                RuleReviewStatus.TRANSLATION_REVIEW_PENDING: "Test translator reviewer",
                RuleReviewStatus.APPROVED: "Fixture approver (test only)",
            }[step],
            occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            note="Test fixture only; no real review occurred.",
        ) for step in (
            RuleReviewStatus.SOURCE_VERIFIED,
            RuleReviewStatus.EDITORIAL_REVIEW_PENDING,
            RuleReviewStatus.TRANSLATION_REVIEW_PENDING,
            RuleReviewStatus.APPROVED,
        )) if status == "approved" else ()),
    )


def _match(question, chart, *rules, allow_test_only=True, language=SupportedLanguage.EN):
    return match_interpretation_rules(question, chart, rules, language=language, allow_test_only=allow_test_only)


def test_matches_valid_vedic_d1_with_exact_chart_and_profile_fact_provenance():
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    chart = _chart([_fact("Moon", "sign", "Vrishabha")])
    rule = _rule("test-only.vedic.d1", "Moon.sign", "Vrishabha", entity=("planet", "Moon"))
    result = _match(question, chart, rule)
    match = result.matches[0]
    assert result.eligible and len(result.matches) == 1
    assert (match.rule_id, match.rule_version, match.knowledge_base_version) == (rule.rule_id, "1.0.0", "1.0.0")
    assert (match.chart_id, match.profile_id, match.system, match.division) == ("chart-1", "profile-1", AstrologySystem.VEDIC, "D1")
    assert len(match.fact_references) == 1
    reference = match.fact_references[0]
    assert (reference.subject, reference.predicate, reference.value) == ("Moon", "sign", "Vrishabha")
    assert reference.provenance == "saved_chart:chart-1:Moon.sign"
    assert match.provenance.editorial_status == "test_only"


def test_matches_vedic_d9_only_for_the_matching_chart_division():
    question = _question(division="D9", entities=(
        MentionedEntity(kind="planet", name="Moon"), MentionedEntity(kind="division", name="D9"),
    ))
    chart = _chart([_fact("Moon", "d9.rashi", "Karka", division="D9")], division="D9")
    rule = _rule("test-only.vedic.d9", "Moon.d9.rashi", "Karka", division="D9", entity=("planet", "Moon"))
    assert len(_match(question, chart, rule).matches) == 1
    wrong_division = _chart([_fact("Moon", "d9.rashi", "Karka")], division="D1")
    result = _match(question, wrong_division, rule)
    assert result.rejection_reason == "chart_division_mismatch"
    assert result.matches == ()


def test_matches_western_condition_when_system_and_natal_division_match():
    question = _question(system="western", division="natal", topic="aspect", entities=(
        MentionedEntity(kind="planet", name="Mars"), MentionedEntity(kind="aspect", name="square"),
    ))
    chart = _chart([_fact("Aspect:Sun/Mars", "aspect", "square", system="western", division="W")], system="western", division="W")
    rule = _rule("test-only.western.aspect", "Aspect:Sun/Mars.aspect", "square", system="western", division="W", topic="aspect")
    result = _match(question, chart, rule)
    assert [item.rule_id for item in result.matches] == [rule.rule_id]
    assert result.matches[0].fact_references[0].source_chart_id == "chart-1"


def test_multi_factor_rule_requires_every_fact_and_retains_every_reference():
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    rule = _rule("test-only.vedic.moon.multi-factor", "Moon.sign", "Vrishabha", entity=("planet", "Moon"))
    rule = rule.model_copy(update={"conditions": tuple(RuleCondition(field=field, equals=value) for field, value in (
        ("Moon.sign", "Vrishabha"), ("Moon.house", 4), ("Moon.retrograde", False),
    ))})
    complete_chart = _chart([
        _fact("Moon", "sign", "Vrishabha"),
        _fact("Moon", "house", 4),
        _fact("Moon", "retrograde", False),
    ])
    matched = _match(question, complete_chart, rule)
    assert len(matched.matches) == 1
    assert {(item.subject, item.predicate) for item in matched.matches[0].fact_references} == {
        ("Moon", "sign"), ("Moon", "house"), ("Moon", "retrograde"),
    }
    partial = _chart([_fact("Moon", "sign", "Vrishabha"), _fact("Moon", "house", 4)])
    rejected = _match(question, partial, rule)
    assert rejected.matches == ()
    assert any(item.reason == "required_fact_missing_or_condition_not_satisfied" for item in rejected.skipped)


@pytest.mark.parametrize(
    ("system", "division", "field"),
    [
        ("vedic", "D1", "Moon.d9.rashi"),
        ("vedic", "D9", "Moon.nakshatra.name"),
        ("vedic", "D9", "Vimshottari.starting_lord"),
        ("vedic", "D1", "Uranus.sign"),
        ("western", "W", "Pluto.house"),
    ],
)
def test_rule_conditions_reject_cross_division_or_unregistered_traditional_systems(system, division, field):
    rule = _rule(
        "test-only.invalid-scope." + field.lower().replace(".", "-"),
        field, "fixture", system=system, division=division,
    )
    with pytest.raises(ValueError):
        validate_rule_conditions(rule)


@pytest.mark.parametrize(
    ("field", "value", "topic", "entity_kind", "entity_name", "system", "division"),
    [
        ("Mars.sign", "Mesha", "sign", "sign", "Mesha", "vedic", "D1"),
        ("Mars.house", 7, "house", "house", "7", "vedic", "D1"),
        ("House:7.sign", "Libra", "house", "house", "7", "western", "W"),
        ("Moon.nakshatra.name", "Rohini", "nakshatra", "nakshatra", "Rohini", "vedic", "D1"),
        ("Moon.nakshatra.pada", 3, "pada", "planet", "Moon", "vedic", "D1"),
        ("Vimshottari.starting_lord", "Venus", "dasha", "dasha_lord", "Venus", "vedic", "D1"),
        ("Vimshottari.year_convention", "savana_360_day", "dasha", "planet", "Moon", "vedic", "D1"),
        ("Dasha:Venus.lord", "Venus", "dasha", "dasha_lord", "Venus", "vedic", "D1"),
        ("Antardasha:Venus/Moon.sub_lord", "Moon", "dasha", "dasha_lord", "Venus", "vedic", "D1"),
        ("Dasha:Venus.start", "2026-01-01", "dasha", "dasha_lord", "Venus", "vedic", "D1"),
        ("Aspect:Sun/Mars.motion", "applying", "aspect", "planet", "Mars", "western", "W"),
        ("Aspect:Sun/Mars.aspect", "square", "aspect", "aspect", "square", "western", "W"),
        ("Mars.retrograde", True, "planet", "planet", "Mars", "vedic", "D1"),
    ],
)
def test_supported_fact_condition_types_match_exact_values(field, value, topic, entity_kind, entity_name, system, division):
    subject, predicate = field.split(".", 1)
    mention = None if field == "Vimshottari.year_convention" else MentionedEntity(kind=entity_kind, name=entity_name)
    question = _question(
        system=system, division="natal" if system == "western" else division, topic=topic,
        entities=(mention,) if mention else (),
    )
    chart = _chart([_fact(subject, predicate, value, system=system, division=division)], system=system, division=division)
    rule = _rule(
        f"test-only.field.{field.lower().replace(':', '.').replace('/', '.').replace('_', '-')}", field, value,
        system=system, division=division, topic=topic,
        entity=(entity_kind, entity_name) if entity_kind not in {"aspect"} and mention else None,
    )
    result = _match(question, chart, rule)
    assert result.matches, result.skipped


def test_missing_or_nonmatching_facts_never_match():
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    rule = _rule("test-only.missing", "Moon.sign", "Taurus", entity=("planet", "Moon"))
    missing = _chart([])
    result = _match(question, missing, rule)
    assert result.matches == ()
    assert result.skipped[0].reason == "required_fact_missing_or_condition_not_satisfied"
    invalid = _chart([_fact("Moon", "sign", "Aries", chart_id="foreign-chart", profile_id="foreign-profile")])
    assert _match(question, invalid, rule).rejection_reason == "fact_chart_provenance_mismatch"


def test_wrong_system_and_wrong_division_are_rejected():
    question = _question(system="vedic", division="D1", entities=(MentionedEntity(kind="planet", name="Moon"),))
    wrong_chart = _chart([_fact("Moon", "sign", "Taurus", system="western", division="W")], system="western", division="W")
    assert _match(question, wrong_chart, _rule("test-only.sys", "Moon.sign", "Taurus", entity=("planet", "Moon"))).rejection_reason == "chart_system_mismatch"
    chart = _chart([_fact("Moon", "sign", "Taurus")])
    wrong_rule = _rule("test-only.div", "Moon.sign", "Taurus", division="D9", entity=("planet", "Moon"))
    assert _match(question, chart, wrong_rule).skipped[0].reason == "chart_division_mismatch"
    foreign_system_rule = _rule("test-only.system", "Moon.sign", "Taurus", system="western", division="W", entity=("planet", "Moon"))
    assert _match(question, chart, foreign_system_rule).skipped[0].reason == "astrology_system_mismatch"


@pytest.mark.parametrize("status", ["draft", "reviewed", "test_only"])
def test_unapproved_rules_are_excluded_from_production_matching(status):
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    chart = _chart([_fact("Moon", "sign", "Taurus")])
    rule = _rule(f"test-only.status.{status}", "Moon.sign", "Taurus", status=status, entity=("planet", "Moon"))
    result = _match(question, chart, rule, allow_test_only=False)
    assert result.matches == ()
    assert result.skipped[0].reason == f"editorial_status_{status}"


def test_approved_rule_with_inadequate_source_is_ineligible_even_if_constructed_directly():
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    chart = _chart([_fact("Moon", "sign", "Taurus")])
    rule = _rule("test-only.bad-source", "Moon.sign", "Taurus", status="approved", reference="unknown", entity=("planet", "Moon"))
    result = _match(question, chart, rule, allow_test_only=False)
    assert result.matches == ()
    assert result.skipped[0].reason == "inadequate_rule_provenance"


def test_duplicate_rule_identifiers_are_an_explicit_error():
    rule = _rule("test-only.duplicate", "Moon.sign", "Taurus")
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    with pytest.raises(DuplicateRuleID, match="Duplicate rule ID"):
        _match(question, _chart([_fact("Moon", "sign", "Taurus")]), rule, rule)


def test_conflicting_matches_are_reported_as_a_group_not_silently_merged():
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    chart = _chart([_fact("Moon", "sign", "Taurus"), _fact("Moon", "house", 2)])
    first = _rule("test-only.conflict.a", "Moon.sign", "Taurus", entity=("planet", "Moon"), conflict_group="test-contradiction")
    second = _rule("test-only.conflict.b", "Moon.house", 2, entity=("planet", "Moon"), conflict_group="test-contradiction")
    result = _match(question, chart, second, first)
    assert [item.rule_id for item in result.matches] == [first.rule_id, second.rule_id]
    assert len(result.conflicts) == 1
    assert result.conflicts[0].rule_ids == (first.rule_id, second.rule_id)


def test_rule_matching_order_and_repeated_results_are_stable():
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    facts = [_fact("Moon", "sign", "Taurus"), _fact("Moon", "house", 2)]
    rules = [
        _rule("test-only.stable.z", "Moon.house", 2, entity=("planet", "Moon")),
        _rule("test-only.stable.a", "Moon.sign", "Taurus", entity=("planet", "Moon")),
    ]
    first = _match(question, _chart(facts), *rules)
    repeated = _match(question, _chart(list(reversed(facts))), *reversed(rules))
    assert first.model_dump() == repeated.model_dump()
    assert [item.rule_id for item in first.matches] == ["test-only.stable.a", "test-only.stable.z"]


def test_facts_from_another_profile_cannot_be_mixed_into_the_chart():
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    chart = _chart([_fact("Moon", "sign", "Taurus", profile_id="another-profile")])
    result = _match(question, chart, _rule("test-only.profile-isolation", "Moon.sign", "Taurus", entity=("planet", "Moon")))
    assert result.rejection_reason == "fact_profile_provenance_mismatch"
    assert result.matches == ()


def test_invalid_typed_chart_fact_is_rejected_before_any_rule_match():
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    invalid = _chart([_fact("Moon", "retrograde", "false")])
    rule = _rule("test-only.invalid-value", "Moon.retrograde", False, entity=("planet", "Moon"))
    result = _match(question, invalid, rule)
    assert result.rejection_reason == "unsupported_or_invalid_chart_fact"
    assert result.matches == ()


@pytest.mark.parametrize("field", ["test_fixture", "Moon.birthplace", "House:13.sign", "Aspect:Sun/Pluto.degree"])
def test_loader_rejects_conditions_not_supported_by_typed_chart_facts(tmp_path, field):
    rule = {
        "rule_id": "test-only.unsupported-field",
        "rule_version": "1.0.0",
        "knowledge_base_version": "1.0.0",
        "system": "vedic",
        "division": "D1",
        "language": "en",
        "topics": ["planet"],
        "conditions": [{"field": field, "equals": "x"}],
        "text": "TEST FIXTURE ONLY — not an astrology interpretation.",
        "confidence": "editorial_low",
        "provenance": {
            "source_name": "Schema fixture", "attribution": "Test authors",
            "reference": "tests/test_ai_rule_matcher.py", "editorial_status": "test_only",
            "classification": "traditional_interpretation",
        },
    }
    path = tmp_path / "rules.json"
    path.write_text(json.dumps({"knowledge_base_version": "1.0.0", "rules": [rule]}), encoding="utf-8")
    with pytest.raises(KnowledgeBaseError, match="unsupported condition field"):
        load_knowledge_base(path)


def test_question_ambiguity_and_unavailable_chart_produce_no_matches():
    chart = _chart([_fact("Moon", "sign", "Taurus")])
    rule = _rule("test-only.ambiguous", "Moon.sign", "Taurus", entity=("planet", "Moon"))
    for question in (
        _question(clarify=True, intent=UserIntent.CLARIFICATION),
        _question(intent=UserIntent.MISSING_CHART),
    ):
        result = _match(question, chart, rule)
        assert not result.eligible
        assert result.matches == ()
