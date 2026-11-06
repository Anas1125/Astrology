import pytest
from datetime import datetime, timezone

from app.services.ai.classifier import classify_question
from app.services.ai.contracts import (
    ChartFact,
    ChartFacts,
    InterpretationRule,
    MentionedEntity,
    QuestionClassification,
    ResponseSection,
    ResponseSectionType,
    ResponseStatus,
    RuleProvenance,
    RuleReviewEvent,
    RuleReviewStatus,
    SupportedLanguage,
)
from app.services.ai.response_composer import (
    InvalidIntelligenceResponse,
    compose_response,
    fact_identifier,
    validate_intelligence_response,
)
from app.services.ai.knowledge_loader import load_knowledge_base
from app.services.ai.rule_matcher import match_interpretation_rules


def _fact(subject, predicate, value, *, system="vedic", division="D1", chart_id="chart-1", profile_id="profile-1"):
    return ChartFact(
        subject=subject, predicate=predicate, value=value, system=system, division=division,
        source_chart_id=chart_id, profile_id=profile_id,
        provenance=f"saved_chart:{chart_id}:{subject}.{predicate}",
    )


def _chart(facts, *, system="vedic", division="D1", chart_id="chart-1", profile_id="profile-1", available=True):
    return ChartFacts(
        chart_id=chart_id, profile_id=profile_id, system=system, division=division,
        available=available, facts=tuple(facts), calculation_engine_version="astroai-test/1.0.0",
    )


def _question(*, system="vedic", division="D1", topic="planet", entities=(), intent="chart_question"):
    return QuestionClassification(
        intent=intent, system=system, division=division, topic=topic,
        entities=tuple(entities), confidence=1.0,
    )


def _rule(rule_id, field, value, *, system="vedic", division="D1", language="en", status="approved", text="A traditional note from a reviewed test source.", conflict_group=None):
    subject, _ = field.split(".", 1)
    entity = (MentionedEntity(kind="planet", name="Moon"),) if subject == "Moon" else ()
    return InterpretationRule(
        rule_id=rule_id, rule_version="1.0.0", knowledge_base_version="1.0.0",
        system=system, division=division, language=language,
        conditions=({"field": field, "equals": value},), topics=("planet",),
        required_entities=entity, conflict_group=conflict_group, text=text,
        confidence="editorial_low",
        provenance=RuleProvenance(
            source_name="Reviewed test source", attribution="AstroAI editorial team",
            reference="https://example.test/reference/source", editorial_status=status,
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
        translations=({"en": text, "ta": "சோதனை உரை மட்டும் — ஜோதிட விளக்கம் அல்ல."} if status == "approved" else {}),
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


def test_english_vedic_d1_answer_contains_chart_facts_and_safety_but_no_unapproved_interpretation():
    chart = _chart([
        _fact("Moon", "sign", "Vrishabha"),
        _fact("Moon", "house", 4),
        _fact("Moon", "nakshatra.name", "Rohini"),
        _fact("Moon", "nakshatra.pada", 2),
        _fact("Mars", "sign", "Mesha"),
    ])
    question = _question(
        topic="general_overview",
        entities=(MentionedEntity(kind="planet", name="Moon"),),
    )
    unreviewed = _rule("test-only.never-output", "Moon.sign", "Vrishabha", status="test_only", text="TEST FIXTURE ONLY — not an astrology interpretation.")
    matches = match_interpretation_rules(question, chart, (unreviewed,), language=SupportedLanguage.EN)
    response = compose_response(question, chart, matches, language="en")
    assert response.status is ResponseStatus.ANSWERED
    assert response.metadata.system.value == "vedic"
    assert response.metadata.division == "D1"
    fact_sections = [section for section in response.sections if section.section_type is ResponseSectionType.CALCULATED_FACT]
    assert len(fact_sections) == 1
    for expected in (
        "Moon is recorded in house 4.", "Moon: Nakshatra — Rohini.",
        "Moon: Pada — 2.", "Moon is recorded in Vrishabha.",
    ):
        assert expected in fact_sections[0].text
    assert len(response.answer_fact_ids) == 4
    assert len(fact_sections[0].fact_references) == 4
    assert "traditional Vedic astrology" in response.answer
    assert "traditional symbolic associations" in response.answer
    assert not response.metadata.matched_rule_ids
    assert all("TEST FIXTURE" not in section.text for section in response.sections)
    assert not any("sourced traditional interpretation" in section.text for section in response.sections)
    assert any("not scientific certainty" in section.text for section in response.sections)


def test_tamil_fact_and_missing_rule_templates_are_localized_without_translating_rule_text():
    chart = _chart([_fact("Moon", "sign", "Vrishabha"), _fact("Moon", "retrograde", True)])
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    response = compose_response(question, chart, None, language="ta")
    texts = [section.text for section in response.sections]
    assert any("சந்திரன் ரிஷபம் ராசியில் உள்ளது." in text for text in texts)
    assert any("சந்திரன் வக்கிர நிலையில் உள்ளது." in text for text in texts)
    assert any("பாரம்பரிய விளக்கம் தற்போது கிடைக்கவில்லை" in text for text in texts)
    assert any("அறிவியல் உறுதி அல்ல" in text for text in texts)
    assert response.metadata.language is SupportedLanguage.TA


def test_vedic_d9_facts_are_scoped_to_d9_and_fact_ids_are_stable():
    fact = _fact("Moon", "d9.rashi", "Karka", division="D9")
    chart = _chart([fact], division="D9")
    question = _question(division="D9", entities=(
        MentionedEntity(kind="planet", name="Moon"), MentionedEntity(kind="division", name="D9"),
    ))
    first = compose_response(question, chart, None, language="en")
    second = compose_response(question, chart, None, language="en")
    section = next(item for item in first.sections if item.section_type is ResponseSectionType.CALCULATED_FACT)
    assert section.fact_ids == (fact_identifier("chart-1", fact),)
    assert first.model_dump() == second.model_dump()
    assert first.metadata.division == "D9"


def test_western_aspect_and_house_facts_are_rendered_with_fact_provenance():
    chart = _chart([
        _fact("Mars", "retrograde", False, system="western", division="W"),
        _fact("Mars", "house", 7, system="western", division="W"),
        _fact("Aspect:Sun/Mars", "aspect", "square", system="western", division="W"),
    ], system="western", division="W")
    question = _question(system="western", division="natal", topic="aspect", entities=(
        MentionedEntity(kind="planet", name="Mars"), MentionedEntity(kind="aspect", name="square"),
    ))
    response = compose_response(question, chart, None, language="en")
    assert response.metadata.division == "W"
    sections = [section for section in response.sections if section.section_type is ResponseSectionType.CALCULATED_FACT]
    assert len(sections) == 1
    assert sections[0].text == "Sun/Mars: aspect — square."
    assert sections[0].fact_references[0].source_chart_id == "chart-1"


def test_vimshottari_period_facts_are_reported_without_claiming_current_status():
    chart = _chart([
        _fact("Vimshottari", "year_convention", "savana_360_day"),
        _fact("Vimshottari", "starting_lord", "Venus"),
        _fact("Dasha:Venus", "start", "2020-01-01"),
    ])
    question = _question(topic="dasha", entities=(MentionedEntity(kind="dasha_lord", name="Venus"),))
    response = compose_response(question, chart, None, language="en")
    texts = [section.text for section in response.sections]
    assert any("starting Dasha lord — Venus" in text for text in texts)
    assert any("period start — 2020-01-01" in text for text in texts)
    assert not any("current" in section.text.casefold() for section in response.sections if section.section_type is ResponseSectionType.CALCULATED_FACT)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What is today's weather?", ResponseStatus.UNSUPPORTED),
        ("Tell me about my chart", ResponseStatus.MISSING_CHART),
        ("What can you tell me about my birth chart?", ResponseStatus.MISSING_CHART),
        ("Please explain my Vedic D1 chart", ResponseStatus.MISSING_CHART),
        ("வணக்கம்", ResponseStatus.NEEDS_CLARIFICATION),
        ("என் ஜாதகத்தில் சந்திரன் எந்த நட்சத்திரம்?", ResponseStatus.MISSING_CHART),
    ],
)
def test_non_chart_or_unavailable_context_statuses_are_localized(question, expected):
    classification = classify_question(question, chart_available=False)
    language = "ta" if any(ord(char) > 127 for char in question) else "en"
    response = compose_response(classification, None, None, language=language)
    assert response.status is expected
    assert response.answer
    assert not response.answer_fact_ids and not response.answer_rule_ids


def test_unavailable_chart_keeps_explicit_conversation_system_without_claiming_chart_facts():
    chart = _chart([], system="western", division=None, available=False)
    classification = classify_question("What can you tell me about my birth chart?", chart_available=False)
    response = compose_response(classification, chart, None, language="en")
    assert response.status is ResponseStatus.MISSING_CHART
    assert response.metadata.system.value == "western"
    assert response.metadata.division is None
    assert not response.answer_fact_ids


def test_approved_rule_provenance_and_exact_supporting_fact_are_preserved():
    chart = _chart([_fact("Moon", "sign", "Vrishabha")])
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    rule = _rule("reviewed.vedic.moon", "Moon.sign", "Vrishabha")
    matches = match_interpretation_rules(question, chart, (rule,), language=SupportedLanguage.EN)
    response = compose_response(question, chart, matches, language="en")
    section = next(item for item in response.sections if item.section_type is ResponseSectionType.TRADITIONAL_INTERPRETATION)
    assert section.text == rule.text
    assert section.fact_references[0].fact_id == fact_identifier("chart-1", chart.facts[0])
    source = section.rule_references[0]
    assert (source.rule_id, source.rule_version, source.knowledge_base_version) == (rule.rule_id, "1.0.0", "1.0.0")
    assert (source.source_name, source.attribution, source.reference, source.editorial_status) == (
        rule.provenance.source_name, rule.provenance.attribution, rule.provenance.reference, "approved",
    )
    assert response.answer_rule_ids == (rule.rule_id,)


def test_test_only_rule_match_is_rejected_even_if_injected_by_a_test_opt_in():
    chart = _chart([_fact("Moon", "sign", "Vrishabha")])
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    rule = _rule("test-only.injected", "Moon.sign", "Vrishabha", status="test_only", text="TEST ONLY")
    unsafe_matches = match_interpretation_rules(question, chart, (rule,), language=SupportedLanguage.EN, allow_test_only=True)
    with pytest.raises(InvalidIntelligenceResponse, match="Only approved"):
        compose_response(question, chart, unsafe_matches, language="en")


def test_checked_in_test_only_knowledge_never_appears_in_production_response():
    version, rules = load_knowledge_base("app/services/ai/knowledge/v1")
    chart = _chart([_fact("Moon", "sign", "Vrishabha"), _fact("Moon", "nakshatra.name", "Rohini")])
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    matches = match_interpretation_rules(question, chart, rules, language=SupportedLanguage.EN)
    response = compose_response(question, chart, matches, language="en", knowledge_base_version=version)
    assert not response.metadata.matched_rule_ids
    assert not any(section.section_type is ResponseSectionType.TRADITIONAL_INTERPRETATION for section in response.sections)
    assert all("TEST FIXTURE" not in section.text and "சோதனைக்கான உரை" not in section.text for section in response.sections)


def test_conflicting_approved_rules_are_withheld_and_conflict_is_explicit():
    chart = _chart([_fact("Moon", "sign", "Vrishabha"), _fact("Moon", "house", 4)])
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    rules = (
        _rule("reviewed.conflict.a", "Moon.sign", "Vrishabha", conflict_group="conflicting-notes"),
        _rule("reviewed.conflict.b", "Moon.house", 4, conflict_group="conflicting-notes"),
    )
    matches = match_interpretation_rules(question, chart, rules, language=SupportedLanguage.EN)
    response = compose_response(question, chart, matches, language="en")
    assert not any(section.section_type is ResponseSectionType.TRADITIONAL_INTERPRETATION for section in response.sections)
    assert any("withheld because they conflict" in section.text for section in response.sections)
    assert any("sourced traditional interpretation" in section.text for section in response.sections)


def test_wrong_profile_or_chart_match_provenance_fails_closed():
    chart = _chart([_fact("Moon", "sign", "Vrishabha")])
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    rule = _rule("reviewed.owner", "Moon.sign", "Vrishabha")
    matches = match_interpretation_rules(question, chart, (rule,), language=SupportedLanguage.EN)
    foreign = matches.model_copy(update={"profile_id": "profile-2"})
    with pytest.raises(InvalidIntelligenceResponse, match="another chart or profile"):
        compose_response(question, chart, foreign, language="en")


def test_invalid_chart_fact_and_wrong_system_or_division_fail_closed():
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    wrong_division = _chart([_fact("Moon", "d9.rashi", "Karka")], division="D1")
    with pytest.raises(InvalidIntelligenceResponse, match="D1 chart contains a D9-only fact"):
        compose_response(question, wrong_division, None, language="en")
    wrong_system_question = _question(system="western", division="natal")
    with pytest.raises(InvalidIntelligenceResponse, match="systems do not match"):
        compose_response(wrong_system_question, _chart([_fact("Moon", "sign", "Vrishabha")]), None, language="en")


def test_response_validation_rejects_missing_fact_ids_private_data_and_oversized_text():
    chart = _chart([_fact("Moon", "sign", "Vrishabha")])
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    response = compose_response(question, chart, None, language="en")
    damaged = response.model_copy(update={
        "sections": (ResponseSection(section_type="calculated_fact", text="Moon is in Taurus.", fact_ids=("fact:missing",)),),
    })
    with pytest.raises(InvalidIntelligenceResponse, match="fact IDs"):
        validate_intelligence_response(damaged, chart=chart)
    private = response.model_copy(update={"answer": "Your birth date is private."})
    with pytest.raises(InvalidIntelligenceResponse, match="private birth"):
        validate_intelligence_response(private, chart=chart)
    with pytest.raises(InvalidIntelligenceResponse, match="character limit"):
        validate_intelligence_response(response, chart=chart, max_characters=10)


def test_repeated_composition_is_byte_for_byte_stable():
    chart = _chart([_fact("Moon", "sign", "Vrishabha"), _fact("Moon", "retrograde", False)])
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    first = compose_response(question, chart, None, language="en")
    repeated = compose_response(question, chart, None, language="en")
    assert first.model_dump_json() == repeated.model_dump_json()


def test_matched_result_with_malformed_rule_fact_reference_is_rejected():
    chart = _chart([_fact("Moon", "sign", "Vrishabha")])
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    rule = _rule("reviewed.invalid-reference", "Moon.sign", "Vrishabha")
    matches = match_interpretation_rules(question, chart, (rule,), language=SupportedLanguage.EN)
    matched = matches.matches[0]
    broken_reference = matched.fact_references[0].model_copy(update={"value": "Mesha"})
    broken_match = matched.model_copy(update={"fact_references": (broken_reference,)})
    broken_result = matches.model_copy(update={"matches": (broken_match,)})
    with pytest.raises(InvalidIntelligenceResponse, match="missing or foreign chart fact"):
        compose_response(question, chart, broken_result, language="en")


def test_rule_with_unsafe_guarantee_or_unattributed_source_is_rejected():
    chart = _chart([_fact("Moon", "sign", "Vrishabha")])
    question = _question(entities=(MentionedEntity(kind="planet", name="Moon"),))
    rule = _rule("reviewed.unsafe", "Moon.sign", "Vrishabha", text="This placement will certainly guarantee success.")
    matches = match_interpretation_rules(question, chart, (rule,), language=SupportedLanguage.EN)
    with pytest.raises(InvalidIntelligenceResponse, match="prohibited guarantee"):
        compose_response(question, chart, matches, language="en")
