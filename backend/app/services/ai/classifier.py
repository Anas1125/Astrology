"""Deterministic bilingual intent and chart-question classification."""
from __future__ import annotations

import re
import unicodedata

from app.services.ai.contracts import (
    AstrologySystem,
    MentionedEntity,
    QuestionClassification,
    QuestionTopic,
    SupportedLanguage,
    UserIntent,
)

CLASSIFIER_VERSION = "1.0.0"

_GREETINGS_EN = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "namaste"}
_GREETINGS_TA = {"வணக்கம்", "ஹாய்", "ஹலோ", "நல்வரவு"}
_VAGUE_EN = {"this", "that", "it", "what about it", "tell me more", "explain", "which one"}
_VAGUE_TA = {"இது", "அது", "எதை", "விளக்கவும்", "மேலும் சொல்லுங்கள்"}

_PLANETS = {
    "sun": ("Sun", "சூரியன்", "ஞாயிறு"),
    "moon": ("Moon", "சந்திரன்", "நிலா"),
    "mercury": ("Mercury", "புதன்"),
    "venus": ("Venus", "சுக்கிரன்"),
    "mars": ("Mars", "செவ்வாய்"),
    "jupiter": ("Jupiter", "குரு", "வியாழன்"),
    "saturn": ("Saturn", "சனி"),
    "uranus": ("Uranus", "யுரேனஸ்"),
    "neptune": ("Neptune", "நெப்டியூன்"),
    "pluto": ("Pluto", "புளூட்டோ"),
    "rahu": ("Rahu", "ராகு"),
    "ketu": ("Ketu", "கேது"),
}
_SIGNS = {
    "aries": ("Aries", "மேஷம்"), "taurus": ("Taurus", "ரிஷபம்"),
    "gemini": ("Gemini", "மிதுனம்"), "cancer": ("Cancer", "கடகம்"),
    "leo": ("Leo", "சிம்மம்"), "virgo": ("Virgo", "கன்னி"),
    "libra": ("Libra", "துலாம்"), "scorpio": ("Scorpio", "விருச்சிகம்"),
    "sagittarius": ("Sagittarius", "தனுசு"), "capricorn": ("Capricorn", "மகரம்"),
    "aquarius": ("Aquarius", "கும்பம்"), "pisces": ("Pisces", "மீனம்"),
}
_NAKSHATRAS = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha", "Ardra", "Punarvasu",
    "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
    "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
)
_NAKSHATRA_TA = {
    "அசுவினி": "Ashwini", "பரணி": "Bharani", "கார்த்திகை": "Krittika", "ரோகிணி": "Rohini",
    "மிருகசீரிடம்": "Mrigashirsha", "திருவாதிரை": "Ardra", "புனர்பூசம்": "Punarvasu",
    "பூசம்": "Pushya", "ஆயில்யம்": "Ashlesha", "மகம்": "Magha", "பூரம்": "Purva Phalguni",
    "உத்திரம்": "Uttara Phalguni", "அஸ்தம்": "Hasta", "சித்திரை": "Chitra", "சுவாதி": "Swati",
    "விசாகம்": "Vishakha", "அனுஷம்": "Anuradha", "கேட்டை": "Jyeshtha", "மூலம்": "Mula",
    "பூராடம்": "Purva Ashadha", "உத்திராடம்": "Uttara Ashadha", "திருவோணம்": "Shravana",
    "அவிட்டம்": "Dhanishta", "சதயம்": "Shatabhisha", "பூரட்டாதி": "Purva Bhadrapada",
    "உத்திரட்டாதி": "Uttara Bhadrapada", "ரேவதி": "Revati",
}
_UNSUPPORTED_EN = ("weather", "recipe", "stock price", "investment advice", "diagnose", "diagnosis", "write code", "programming")
_UNSUPPORTED_TA = ("வானிலை", "சமையல்", "பங்கு விலை", "மருத்துவ நோய்", "சட்ட ஆலோசனை")
_ASTRO_EN = ("astrology", "horoscope", "chart", "planet", "sign", "house", "nakshatra", "dasha", "aspect", "vedic", "western", "rashi", "lagna", "navamsa", "d1", "d9", "porutham", "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces")
_ASTRO_TA = ("ஜோதிட", "ஜாதக", "கிரகம்", "ராசி", "பாவம்", "நட்சத்திரம்", "தசை", "லக்னம்", "நவாம்சம்", "பொருத்தம்", "பாதம்", "மேற்கத்திய", "வேத", "சூரியன்", "சந்திரன்", "புதன்", "சுக்கிரன்", "செவ்வாய்", "குரு", "சனி", "ராகு", "கேது", "மேஷம்", "ரிஷபம்", "மிதுனம்", "கடகம்", "சிம்மம்", "கன்னி", "துலாம்", "விருச்சிகம்", "தனுசு", "மகரம்", "கும்பம்", "மீனம்", "பார்வை")


def detect_language(question: str, account_language: str | None = None) -> SupportedLanguage:
    """Prefer the language present in the message; account setting is only a fallback."""
    if any("\u0b80" <= char <= "\u0bff" for char in question):
        return SupportedLanguage.TA
    if any(char.isalpha() for char in question):
        return SupportedLanguage.EN
    if account_language in {"en", "ta"}:
        return SupportedLanguage(account_language)
    return SupportedLanguage.EN


def _contains(text: str, terms: tuple[str, ...] | list[str]) -> bool:
    return any(term in text for term in terms)


def _english_term(text: str, term: str) -> bool:
    return re.search(rf"(?<![\w]){re.escape(term.casefold())}(?![\w])", text) is not None


def _mentions(text: str, language: SupportedLanguage) -> tuple[MentionedEntity, ...]:
    found: list[MentionedEntity] = []

    def add(kind: str, name: str) -> None:
        entity = MentionedEntity(kind=kind, name=name)
        if entity not in found:
            found.append(entity)

    for canonical, names in _PLANETS.items():
        if any((name.casefold() in text if any(ord(c) > 127 for c in name) else _english_term(text, name)) for name in names):
            add("planet", canonical.title())
    for canonical, names in _SIGNS.items():
        if any((name.casefold() in text if any(ord(c) > 127 for c in name) else _english_term(text, name)) for name in names):
            add("sign", canonical.title())
    for nakshatra in _NAKSHATRAS:
        if _english_term(text, nakshatra):
            add("nakshatra", nakshatra)
    for tamil, canonical in _NAKSHATRA_TA.items():
        if tamil in text:
            add("nakshatra", canonical)
    for match in re.finditer(r"\b(?:house|பாவம்)\s*(?:number\s*)?(\d{1,2})(?:st|nd|rd|th)?\b", text, flags=re.IGNORECASE):
        house = int(match.group(1))
        if 1 <= house <= 12:
            add("house", str(house))
    for match in re.finditer(r"\b(?:house|பாவம்)\s*(?:number\s*)?(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)\b", text, flags=re.IGNORECASE):
        ordinals = ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth")
        add("house", str(ordinals.index(match.group(1).casefold()) + 1))
    if _contains(text, ("d1", "d9", "navamsa", "நவாம்சம்", "ராசி")):
        division = "D9" if _contains(text, ("d9", "navamsa", "நவாம்சம்")) else "D1"
        add("division", division)
    for canonical, aliases in {"conjunction": ("conjunction",), "sextile": ("sextile",), "square": ("square",), "trine": ("trine",), "opposition": ("opposition",)}.items():
        if any(_english_term(text, alias) for alias in aliases):
            add("aspect", canonical)
    dasha_lords = "Ketu|Venus|Sun|Moon|Mars|Rahu|Jupiter|Saturn|Mercury"
    for match in re.finditer(rf"\b({dasha_lords})\s+(?:(?:maha|antar)\s*)?dasha\b|\b(?:maha|antar)dasha\s+(?:of\s+)?({dasha_lords})\b", text, re.IGNORECASE):
        add("dasha_lord", (match.group(1) or match.group(2)).title())
    if language is SupportedLanguage.TA:
        for tamil, lord in {"கேது": "Ketu", "சுக்கிரன்": "Venus", "சூரியன்": "Sun", "சந்திரன்": "Moon", "செவ்வாய்": "Mars", "ராகு": "Rahu", "குரு": "Jupiter", "சனி": "Saturn", "புதன்": "Mercury"}.items():
            if (
                re.search(rf"{re.escape(tamil)}\s+(?:மகா)?தசை", text)
                or re.search(rf"(?:மகா)?தசை(?:யில்|க்கு|யை|யின்)?\s+(?:அதிபதி\s+)?{re.escape(tamil)}", text)
            ):
                add("dasha_lord", lord)
    return tuple(found)


def classify_question(
    question: str,
    *,
    account_language: str | None = None,
    selected_system: AstrologySystem | str | None = None,
    selected_division: str | None = None,
    chart_available: bool | None = None,
) -> QuestionClassification:
    """Classify only explicit lexical evidence and chart context supplied by caller."""
    normalized = unicodedata.normalize("NFKC", question or "").strip().casefold()
    language = detect_language(normalized, account_language)
    if not normalized:
        return QuestionClassification(intent=UserIntent.CLARIFICATION, confidence=1.0, needs_clarification=True, clarification_reason="empty_question")

    greeting_set = _GREETINGS_TA if language is SupportedLanguage.TA else _GREETINGS_EN
    if normalized.strip(" !?.。؟") in greeting_set:
        return QuestionClassification(intent=UserIntent.GREETING, confidence=1.0)

    if _contains(normalized, _UNSUPPORTED_TA if language is SupportedLanguage.TA else _UNSUPPORTED_EN):
        return QuestionClassification(intent=UserIntent.UNSUPPORTED, confidence=0.98)

    is_astrology = _contains(normalized, _ASTRO_TA if language is SupportedLanguage.TA else _ASTRO_EN)
    if not is_astrology:
        vague = normalized.strip(" !?.。؟") in (_VAGUE_TA if language is SupportedLanguage.TA else _VAGUE_EN)
        if vague:
            return QuestionClassification(intent=UserIntent.CLARIFICATION, confidence=0.9, needs_clarification=True, clarification_reason="referent_unclear")
        return QuestionClassification(intent=UserIntent.UNSUPPORTED, confidence=0.82)

    has_vedic = _contains(normalized, ("vedic", "jyotish", "rashi", "lagna", "nakshatra", "dasha", "navamsa", "d1", "d9", "ஜோதிட", "ராசி", "நட்சத்திரம்", "தசை", "லக்னம்", "நவாம்சம்", "பாதம்", "வேத"))
    has_western = _contains(normalized, ("western", "tropical", "natal chart", "aspect", "midheaven", "மேற்கத்திய"))
    system: AstrologySystem | None = None
    ambiguity: str | None = None
    if has_vedic and has_western:
        ambiguity = "conflicting_astrology_systems"
    elif has_vedic:
        system = AstrologySystem.VEDIC
    elif has_western:
        system = AstrologySystem.WESTERN
    elif chart_available is True and selected_system is not None:
        system = AstrologySystem(selected_system)
    else:
        ambiguity = "astrology_system_not_specified"

    explicit_d1 = _contains(normalized, ("d1", "rasi chart", "birth chart", "ராசி கட்டம்"))
    explicit_d9 = _contains(normalized, ("d9", "navamsa", "நவாம்சம்"))
    division: str | None = None
    if explicit_d1 and explicit_d9:
        ambiguity = "conflicting_chart_divisions"
    elif explicit_d9:
        division = "D9"
        system = system or AstrologySystem.VEDIC
    elif explicit_d1:
        division = "D1"
        system = system or AstrologySystem.VEDIC
    elif system is AstrologySystem.WESTERN:
        division = "natal"
    elif chart_available is True and selected_division:
        division = selected_division

    if _contains(normalized, ("nakshatra", "நட்சத்திரம்")):
        topic = QuestionTopic.PADA if _contains(normalized, ("pada", "பாதம்")) else QuestionTopic.NAKSHATRA
    elif _contains(normalized, ("dasha", "mahadasha", "antardasha", "தசை", "புத்தி")):
        topic = QuestionTopic.DASHA
    elif _contains(normalized, ("aspect", "conjunction", "sextile", "square", "trine", "opposition", "பார்வை")):
        topic = QuestionTopic.ASPECT
    elif _english_term(normalized, "house") or "பாவம்" in normalized:
        topic = QuestionTopic.HOUSE
    elif any(entity.kind == "planet" for entity in _mentions(normalized, language)):
        topic = QuestionTopic.PLANET
    elif any(entity.kind == "sign" for entity in _mentions(normalized, language)):
        topic = QuestionTopic.SIGN
    elif _contains(normalized, ("overview", "whole chart", "என் ஜாதகம்", "முழு ஜாதகம்")):
        topic = QuestionTopic.GENERAL_OVERVIEW
    else:
        topic = QuestionTopic.OTHER

    entities = _mentions(normalized, language)
    match = re.search(r"\b(?:house|பாவம்)\s*(?:number\s*)?(\d{1,2})(?:st|nd|rd|th)?\b", normalized)
    if match and not 1 <= int(match.group(1)) <= 12:
        ambiguity = "house_number_out_of_range"
    if chart_available is False:
        return QuestionClassification(
            intent=UserIntent.MISSING_CHART, system=system, division=division, topic=topic,
            entities=entities, confidence=0.96, needs_clarification=ambiguity is not None,
            clarification_reason=ambiguity,
        )
    if ambiguity:
        return QuestionClassification(
            intent=UserIntent.CLARIFICATION, system=system, division=division, topic=topic,
            entities=entities, confidence=0.65, needs_clarification=True, clarification_reason=ambiguity,
        )
    return QuestionClassification(
        intent=UserIntent.CHART_QUESTION, system=system, division=division, topic=topic,
        entities=entities, confidence=0.9,
    )
