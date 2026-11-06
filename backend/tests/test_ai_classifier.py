import pytest

from app.services.ai.classifier import classify_question, detect_language
from app.services.ai.contracts import AstrologySystem, QuestionTopic, SupportedLanguage, UserIntent


@pytest.mark.parametrize("message", ["Hi!", "Hello", "வணக்கம்", "ஹாய்!"])
def test_greetings_are_detected_in_english_and_tamil(message):
    assert classify_question(message).intent is UserIntent.GREETING


def test_actual_message_language_takes_precedence_over_account_setting():
    assert detect_language("வணக்கம்", "en") is SupportedLanguage.TA
    assert detect_language("Hello there", "ta") is SupportedLanguage.EN


@pytest.mark.parametrize(
    ("question", "system", "division", "topic", "intent"),
    [
        ("In Vedic D1, what does Mars in Aries mean?", AstrologySystem.VEDIC, "D1", QuestionTopic.PLANET, UserIntent.CHART_QUESTION),
        ("Explain my Western natal chart Moon in Taurus", AstrologySystem.WESTERN, "natal", QuestionTopic.PLANET, UserIntent.CHART_QUESTION),
        ("Vedic D9 Navamsa placements", AstrologySystem.VEDIC, "D9", QuestionTopic.OTHER, UserIntent.CHART_QUESTION),
        ("What is my 7th house in Western astrology?", AstrologySystem.WESTERN, "natal", QuestionTopic.HOUSE, UserIntent.CHART_QUESTION),
        ("Vedic Nakshatra and Pada for Moon", AstrologySystem.VEDIC, None, QuestionTopic.PADA, UserIntent.CHART_QUESTION),
        ("Vedic Vimshottari Mahadasha for Venus", AstrologySystem.VEDIC, None, QuestionTopic.DASHA, UserIntent.CHART_QUESTION),
        ("Western square aspect between Mars and Moon", AstrologySystem.WESTERN, "natal", QuestionTopic.ASPECT, UserIntent.CHART_QUESTION),
        ("என் ஜாதகத்தில் சந்திரன் எந்த நட்சத்திரம்?", AstrologySystem.VEDIC, None, QuestionTopic.NAKSHATRA, UserIntent.CHART_QUESTION),
        ("வேத ஜோதிட நவாம்சம் D9 விளக்கவும்", AstrologySystem.VEDIC, "D9", QuestionTopic.OTHER, UserIntent.CHART_QUESTION),
        ("மேற்கத்திய ஜாதகத்தில் செவ்வாய் எந்த பாவம்?", AstrologySystem.WESTERN, "natal", QuestionTopic.HOUSE, UserIntent.CHART_QUESTION),
        ("வேத தசையில் சுக்கிரன் பற்றி சொல்லுங்கள்", AstrologySystem.VEDIC, None, QuestionTopic.DASHA, UserIntent.CHART_QUESTION),
    ],
)
def test_classifies_chart_questions(question, system, division, topic, intent):
    result = classify_question(question)
    assert result.system is system
    assert result.division == division
    assert result.topic is topic
    assert result.intent is intent
    assert not result.needs_clarification


def test_explicit_planet_sign_house_nakshatra_and_dasha_entities_are_returned():
    result = classify_question("Vedic D1: Is Mars in Aries in house 10 during Venus dasha, and what is Ashwini Pada?")
    assert {entity.name for entity in result.entities if entity.kind == "planet"} >= {"Mars"}
    assert {entity.name for entity in result.entities if entity.kind == "sign"} >= {"Aries"}
    assert {entity.name for entity in result.entities if entity.kind == "house"} == {"10"}
    assert {entity.name for entity in result.entities if entity.kind == "nakshatra"} == {"Ashwini"}
    assert {entity.name for entity in result.entities if entity.kind == "dasha_lord"} == {"Venus"}
    assert {entity.name for entity in result.entities if entity.kind == "division"} == {"D1"}


def test_ambiguous_or_conflicting_system_and_division_requires_clarification():
    assert classify_question("Tell me about my chart").needs_clarification
    assert classify_question("Where is my Venus?").intent is UserIntent.CLARIFICATION
    assert classify_question("Where is my Venus?").topic is QuestionTopic.PLANET
    assert classify_question("Compare Vedic and Western chart").clarification_reason == "conflicting_astrology_systems"
    assert classify_question("Vedic D1 and D9 chart").clarification_reason == "conflicting_chart_divisions"
    assert classify_question("Mars?").intent is UserIntent.CLARIFICATION


def test_selected_chart_resolves_system_only_when_chart_is_available():
    selected = classify_question(
        "What is my chart overview?", selected_system="western", selected_division="natal", chart_available=True,
    )
    assert selected.intent is UserIntent.CHART_QUESTION
    assert selected.system is AstrologySystem.WESTERN
    assert selected.division == "natal"
    no_chart = classify_question("What is my chart overview?", selected_system="western", chart_available=False)
    assert no_chart.intent is UserIntent.MISSING_CHART
    assert not no_chart.needs_clarification
    assert no_chart.system is None


@pytest.mark.parametrize(("question", "system", "division"), [
    ("What can you tell me about my birth chart?", None, None),
    ("Tell me about my horoscope.", None, None),
    ("What does my Lagna mean?", AstrologySystem.VEDIC, None),
    ("Explain my Navamsa.", AstrologySystem.VEDIC, "D9"),
    ("என் ஜாதகத்தைப் பற்றி என்ன சொல்ல முடியும்?", None, None),
    ("என் ஜாதகத்தைப் பற்றி சொல்லுங்கள்.", None, None),
    ("என் லக்னம் பற்றி சொல்லுங்கள்.", AstrologySystem.VEDIC, None),
    ("என் நவாம்சத்தை விளக்குங்கள்.", AstrologySystem.VEDIC, "D9"),
])
def test_personal_chart_questions_without_chart_report_missing_chart(question, system, division):
    result = classify_question(question, chart_available=False)
    assert result.intent is UserIntent.MISSING_CHART
    assert not result.needs_clarification
    assert result.system is system
    assert result.division == division


def test_tamil_dasha_lord_is_only_classified_when_tied_to_the_dasha_phrase():
    result = classify_question("வேத தசையில் சுக்கிரன் பற்றி சொல்லுங்கள்")
    assert {item.name for item in result.entities if item.kind == "dasha_lord"} == {"Venus"}


def test_explicit_chart_question_with_unavailable_chart_is_missing_chart():
    result = classify_question("Please explain my Western natal chart", chart_available=False)
    assert result.intent is UserIntent.MISSING_CHART
    assert result.system is AstrologySystem.WESTERN


@pytest.mark.parametrize("question", ["What is today's weather?", "Give me a recipe", "வானிலை எப்படி?"])
def test_non_astrology_requests_are_unsupported(question):
    assert classify_question(question).intent is UserIntent.UNSUPPORTED
