from types import SimpleNamespace

from app.services.ai import engine
from app.services.ai.contracts import AstrologySystem, SupportedLanguage


def test_tamil_personal_moon_question_uses_existing_moon_classifier(monkeypatch):
    captured = {}

    def fake_classify_question(question, **kwargs):
        captured["question"] = question
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(engine, "classify_question", fake_classify_question)
    chart = SimpleNamespace(available=False, division=None)

    engine._classify(
        "எனது சந்திரனைப் பற்றி விளக்குங்கள்",
        language=SupportedLanguage("ta"),
        selected_system=AstrologySystem("vedic"),
        chart=chart,
    )

    assert captured["question"] == "explain my Moon"
    assert captured["account_language"] == "en"
    assert captured["selected_system"] is AstrologySystem("vedic")
    assert captured["chart_available"] is False


def test_tamil_general_moon_question_is_not_forced_into_personal_mode(monkeypatch):
    captured = {}

    def fake_classify_question(question, **kwargs):
        captured["question"] = question
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(engine, "classify_question", fake_classify_question)
    chart = SimpleNamespace(available=False, division=None)

    engine._classify(
        "சந்திரன் என்றால் என்ன?",
        language=SupportedLanguage("ta"),
        selected_system=AstrologySystem("vedic"),
        chart=chart,
    )

    assert captured["question"] == "சந்திரன் என்றால் என்ன?"
    assert captured["account_language"] == "ta"
