import json

import pytest

from app.services.ai.classifier import classify_question
from app.services.ai.contracts import (
    ChartFacts,
    ConversationTurn,
    QuestionClassification,
    ResponseSectionType,
    ResponseStatus,
    SupportedLanguage,
    UserIntent,
)
from app.services.ai.engine import DeterministicAstrologyIntelligence, _resolve_general_education_follow_up
from app.services.ai.general_knowledge import GeneralKnowledgeError, load_general_knowledge


@pytest.mark.parametrize(("question", "topic"), [
    ("What is the difference between Vedic and Western astrology?", "vedic_vs_western"),
    ("What are the 12 zodiac signs?", "zodiac_signs"),
    ("What are the 12 houses?", "houses"),
    ("What are Nakshatras?", "nakshatras"),
    ("Explain the nine Vedic planets", "nine_vedic_planets"),
    ("What are Rahu and Ketu?", "rahu_ketu"),
    ("Explain zodiac elements and modalities", "elements_modalities"),
    ("What are D1 and D9 charts?", "d1_d9"),
    ("What is Vimshottari Dasha?", "vimshottari_dasha"),
    ("What does astrology terminology mean?", "terminology"),
    ("வேத மற்றும் மேற்கத்திய ஜோதிடத்திற்கு என்ன வேறுபாடு?", "vedic_vs_western"),
    ("12 ராசிகள் என்றால் என்ன?", "zodiac_signs"),
    ("பன்னிரண்டு பாவங்கள் என்றால் என்ன?", "houses"),
    ("நட்சத்திரங்கள் என்றால் என்ன?", "nakshatras"),
    ("நவக்கிரகங்கள் எவை?", "nine_vedic_planets"),
    ("ராகு கேது என்றால் என்ன?", "rahu_ketu"),
    ("நவாம்சம் என்றால் என்ன?", "d1_d9"),
    ("விம்சோத்தரி தசை என்றால் என்ன?", "vimshottari_dasha"),
])
def test_educational_classifier_recognizes_curated_topics_without_chart(question, topic):
    result = classify_question(question, chart_available=False)
    assert result.intent is UserIntent.GENERAL_EDUCATION
    assert result.education_topic == topic
    assert result.system is None and result.division is None


@pytest.mark.parametrize(("question", "language"), [
    ("What are the 12 zodiac signs?", SupportedLanguage.EN),
    ("நட்சத்திரங்கள் என்றால் என்ன?", SupportedLanguage.TA),
])
def test_education_engine_answers_without_chart_and_discloses_unverified_content(question, language):
    classification = classify_question(question, chart_available=False)
    response = DeterministicAstrologyIntelligence().answer(
        question, language=language, classification=classification,
        chart=ChartFacts(available=False),
    )
    assert response.status is ResponseStatus.ANSWERED
    assert response.metadata.content_classification == "general_education"
    assert response.metadata.source_verification_status == "not_independently_verified"
    assert response.metadata.system is None and response.metadata.division is None
    assert response.metadata.education_topic == classification.education_topic
    education = next(section for section in response.sections if section.section_type is ResponseSectionType.GENERAL_EDUCATION)
    assert education.text and not education.fact_references and not education.rule_references
    limitation = next(section for section in response.sections if section.section_type is ResponseSectionType.LIMITATION)
    assert "source-verified" in limitation.text if language is SupportedLanguage.EN else "ஆதாரங்கள் தனியாகச் சரிபார்க்கப்படவில்லை" in limitation.text
    assert not response.answer_fact_ids and not response.answer_rule_ids
    assert "Chapter" not in education.text and "அத்தியாயம்" not in education.text


@pytest.mark.parametrize("question", [
    "What is my sign?",
    "What does my Lagna mean?",
    "Explain my Navamsa.",
    "What can you tell me about my birth chart?",
    "என் ராசி என்ன?",
    "என் லக்னம் பற்றி சொல்லுங்கள்.",
    "என் நவாம்சத்தை விளக்குங்கள்.",
])
def test_personal_chart_questions_are_not_reclassified_as_general_education(question):
    result = classify_question(question, chart_available=False)
    assert result.intent is UserIntent.MISSING_CHART
    assert result.education_topic is None


@pytest.mark.parametrize(("question", "followup", "language"), [
    ("What are the 12 zodiac signs?", "Tell me more", SupportedLanguage.EN),
    ("12 ராசிகள் என்றால் என்ன?", "மேலும் சொல்லுங்கள்", SupportedLanguage.TA),
])
def test_general_follow_up_retains_prior_educational_topic_without_chart_facts(question, followup, language):
    chart = ChartFacts(available=False)
    prior = classify_question(question, chart_available=False)
    followup_classification = classify_question(followup, chart_available=False)
    resolved = _resolve_general_education_follow_up(
        followup, followup_classification,
        (ConversationTurn(role="user", content=question),),
        selected_system="vedic", chart=chart,
    )
    assert prior.intent is UserIntent.GENERAL_EDUCATION
    assert resolved.intent is UserIntent.GENERAL_EDUCATION
    assert resolved.education_topic == "zodiac_signs"


def test_general_catalogue_has_bilingual_unverified_entries_and_no_citations():
    document = load_general_knowledge()
    expected = {
        "vedic_vs_western", "zodiac_signs", "houses", "nine_vedic_planets", "nakshatras",
        "rahu_ketu", "elements_modalities", "d1_d9", "vimshottari_dasha", "terminology",
        "nakshatra_padas", "nakshatra_detail", "nakshatra_ruling_planet", "nakshatra_chart_method",
    }
    assert {entry.topic_id for entry in document.entries} == expected
    assert all(entry.editorial_status == "editorial_draft" for entry in document.entries)
    assert all(entry.source_verification_status == "not_independently_verified" for entry in document.entries)
    assert all(not entry.source_references and entry.overview.en and entry.overview.ta for entry in document.entries)
    assert len(document.nakshatra_subjects) == 27
    assert document.nakshatra_subjects["Ashwini"].ruling_planet.en == "Ketu"


def test_unverified_general_catalogue_rejects_fabricated_source_references(tmp_path):
    document = json.loads(load_general_knowledge().model_dump_json())
    document["entries"][0]["source_references"] = ["Brihat Parashara Hora Shastra, chapter 1"]
    source = tmp_path / "general.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(GeneralKnowledgeError, match="cannot claim source references"):
        load_general_knowledge(source)


def test_catalogue_rejects_missing_tamil_content(tmp_path):
    document = json.loads(load_general_knowledge().model_dump_json())
    del document["entries"][0]["overview"]["ta"]
    source = tmp_path / "general.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(GeneralKnowledgeError, match="Invalid general knowledge document"):
        load_general_knowledge(source)


@pytest.mark.parametrize(("question", "topic", "subject"), [
    ("How many Padas does each Nakshatra have?", "nakshatra_padas", None),
    ("Can you explain Ashwini Nakshatra in detail?", "nakshatra_detail", "Ashwini"),
    ("How is it used in Vedic birth chart interpretation?", "nakshatra_chart_method", None),
    ("ஒவ்வொரு நட்சத்திரத்திற்கும் எத்தனை பாதங்கள்?", "nakshatra_padas", None),
    ("அசுவினி நட்சத்திரம் பற்றி விரிவாக விளக்குங்கள்", "nakshatra_detail", "Ashwini"),
    ("வேத ஜாதக விளக்கத்தில் இது எவ்வாறு பயன்படுத்தப்படுகிறது?", "nakshatra_chart_method", None),
])
def test_nakshatra_education_classifies_without_requesting_personal_chart(question, topic, subject):
    result = classify_question(question, chart_available=False)
    assert result.intent is UserIntent.GENERAL_EDUCATION
    assert result.education_topic == topic
    assert result.education_subject == subject


def test_context_resolves_ruling_planet_pronoun_from_prior_ashwini_question():
    question = "What is its ruling planet?"
    result = classify_question(question, chart_available=False)
    assert result.intent is UserIntent.CLARIFICATION
    resolved = _resolve_general_education_follow_up(
        question, result,
        (ConversationTurn(role="user", content="Can you explain Ashwini Nakshatra in detail?"),),
        selected_system="vedic", chart=ChartFacts(available=False),
    )
    assert resolved.intent is UserIntent.GENERAL_EDUCATION
    assert resolved.education_topic == "nakshatra_ruling_planet"
    assert resolved.education_subject == "Ashwini"


@pytest.mark.parametrize(("topic", "subject", "expected"), [
    ("nakshatra_padas", None, "four Padas"),
    ("nakshatra_detail", "Ashwini", "Nakshatra number 1"),
    ("nakshatra_ruling_planet", "Ashwini", "assigned to Ketu"),
    ("nakshatra_chart_method", None, "not your chart"),
])
def test_specific_nakshatra_education_uses_curated_catalogue_entries(topic, subject, expected):
    classification = QuestionClassification(
        intent=UserIntent.GENERAL_EDUCATION, education_topic=topic,
        education_subject=subject, confidence=0.95,
    )
    response = DeterministicAstrologyIntelligence().answer(
        "educational question", language=SupportedLanguage.EN,
        classification=classification, chart=ChartFacts(available=False),
    )
    assert response.status is ResponseStatus.ANSWERED
    text = next(section.text for section in response.sections if section.section_type is ResponseSectionType.GENERAL_EDUCATION)
    assert expected in text
    assert response.metadata.content_classification == "general_education"
    assert not response.answer_fact_ids and not response.answer_rule_ids


def test_unresolved_ruling_pronoun_does_not_trigger_chart_fact_or_guess():
    question = "What is its ruling planet?"
    response = DeterministicAstrologyIntelligence().answer(
        question, language=SupportedLanguage.EN,
        classification=classify_question(question, chart_available=False),
        chart=ChartFacts(available=False),
    )
    assert response.status is ResponseStatus.NEEDS_CLARIFICATION
    assert not response.answer_fact_ids and not response.answer_rule_ids
