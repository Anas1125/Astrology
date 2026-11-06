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
_ASTRO_TA = ("ஜோதிட", "ஜாதக", "கிரகம்", "ராசி", "பாவம்", "நட்சத்திரம்", "தசை", "லக்னம்", "நவாம்ச", "பொருத்தம்", "பாதம்", "மேற்கத்திய", "வேத", "சூரியன்", "சந்திரன்", "புதன்", "சுக்கிரன்", "செவ்வாய்", "குரு", "சனி", "ராகு", "கேது", "மேஷம்", "ரிஷபம்", "மிதுனம்", "கடகம்", "சிம்மம்", "கன்னி", "துலாம்", "விருச்சிகம்", "தனுசு", "மகரம்", "கும்பம்", "மீனம்", "பார்வை")

_EDUCATION_STARTS_EN = (
    "what is ", "what are ", "what's ", "define ", "explain ", "describe ",
    "difference between ", "what is the difference between ", "tell me about ",
    "list ", "how does ", "how do ", "how many ", "how is it used", "can you explain ",
    "what do ", "what does ", "what about ", "and ",
    "vedic vs western", "western vs vedic", "difference between ",
)
_EDUCATION_MARKERS_TA = (
    "என்றால் என்ன", "என்பது என்ன", "என்ன வேறுபாடு", "வேறுபாடு என்ன", "விளக்குங்கள்",
    "பற்றி சொல்லுங்கள்", "பட்டியலிடுங்கள்", "எவை", "என்னென்ன",
)
_PERSONAL_MARKERS_EN = ("my ", "mine", "myself", "my chart", "my horoscope", "my birth chart", "its house", "its placement", "its sign", "their house", "that placement")
_PERSONAL_MARKERS_TA = ("என்னுடைய", "எனது", "எங்களுடைய", "என் ஜாதக", "என் ராசி", "என் லக்ன", "என் நவாம்ச", "என் நட்சத்திர", "என் கிரக", "என் பாவ", "என் தசை")


def _education_topic(text: str, language: SupportedLanguage) -> str | None:
    """Map explicit educational terminology to a curated general topic ID."""
    if _contains(text, ("how many pada", "how many padas", "number of padas", "பாதங்கள் எத்தனை", "எத்தனை பாதம்", "எத்தனை பாதங்கள்")):
        return "nakshatra_padas" if _contains(text, ("nakshatra", "நட்சத்திர")) else "nakshatra_padas"
    if _contains(text, ("ruling planet", "ruling lord", "lord of this nakshatra", "அதன் அதிபதி", "ஆளும் கிரகம்", "அதிபதி கிரகம்")):
        return "nakshatra_ruling_planet"
    if _contains(text, ("birth chart interpretation", "used in vedic chart", "used in a chart", "used in chart interpretation", "ஜாதக விளக்கத்தில்", "ஜாதகப் பலனில்", "ஜாதகத்தில் எவ்வாறு பயன்படுத்த")):
        return "nakshatra_chart_method"
    # A named Nakshatra is an educational subject when asked about directly.
    # The caller separately rejects personal questions before this can match.
    if any(_english_term(text, name.casefold()) for name in _NAKSHATRAS) or any(name in text for name in _NAKSHATRA_TA):
        return "nakshatra_detail"
    checks: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("vedic_vs_western", ("difference between vedic", "vedic and western", "western and vedic", "vedic vs western", "western vs vedic", "ஜோதிட முறைகளுக்கு இடையிலான வேறுபாடு", "வேத மற்றும் மேற்கத்திய")),
        ("nakshatras", ("nakshatra", "nakshatras", "நட்சத்திரம்", "நட்சத்திரங்கள்")),
        ("vimshottari_dasha", ("vimshottari", "mahadasha", "antardasha", "விம்சோத்தரி", "மகாதசை", "அந்தர்தசை")),
        ("d1_d9", ("d1", "d9", "navamsa", "நவாம்சம்", "ராசி கட்டம்", "வர்க்க ஜாதகம்")),
        ("houses", ("houses", "house", "bhava", "bhavas", "பாவம்", "பாவங்கள்")),
        ("rahu_ketu", ("rahu", "ketu", "lunar nodes", "ராகு", "கேது", "சந்திர முடிச்சுகள்")),
        ("nine_vedic_planets", ("navagraha", "navagrahas", "nine vedic planets", "nine planets in vedic", "நவக்கிரகம்", "நவக்கிரகங்கள்", "நவகிரகங்கள்", "ஒன்பது கிரகங்கள்")),
        ("elements_modalities", ("elements", "modalities", "modality", "cardinal", "fixed signs", "mutable signs", "நான்கு தன்மைகள்", "மூன்று வகைப்பாடுகள்")),
        ("zodiac_signs", ("zodiac signs", "zodiac sign", "twelve signs", "12 signs", "signs of the zodiac", "rashi", "rashis", "zodiac", "ராசிகள்", "ராசி")),
        ("terminology", ("what is astrology", "astrology terms", "astrological terms", "astrology terminology", "vedic astrology", "western astrology", "ஜோதிடம் என்றால்", "ஜோதிட சொற்கள்", "ஜோதிடத்தில் பயன்படுத்தும் சொற்கள்")),
    )
    for topic, terms in checks:
        if _contains(text, terms):
            return topic
    return None


def _is_education_request(text: str, language: SupportedLanguage) -> bool:
    if _contains(text, _PERSONAL_MARKERS_TA if language is SupportedLanguage.TA else _PERSONAL_MARKERS_EN):
        return False
    if language is SupportedLanguage.TA:
        return any(marker in text for marker in _EDUCATION_MARKERS_TA) or _contains(text, ("எத்தனை பாதம்", "எத்தனை பாதங்கள்", "அதன் அதிபதி", "ஜாதக விளக்கத்தில்", "ஜாதகத்தில் எவ்வாறு"))
    return text.startswith(_EDUCATION_STARTS_EN)


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

    education_topic = _education_topic(normalized, language)
    explicit_education_subject = _mentions(normalized, language)
    has_nakshatra_subject = any(entity.kind == "nakshatra" for entity in explicit_education_subject)
    if education_topic == "nakshatra_ruling_planet" and not has_nakshatra_subject and _contains(
        normalized, ("its", "their", "அதன்", "அதற்கு"),
    ):
        return QuestionClassification(
            intent=UserIntent.CLARIFICATION,
            confidence=0.75,
            needs_clarification=True,
            clarification_reason="referent_unclear",
        )
    if education_topic and (
        _is_education_request(normalized, language)
        or language is SupportedLanguage.TA and normalized.startswith(("இதன்", "அதைப் பற்றி", "மேலும் ", "அதன்"))
    ):
        entities = explicit_education_subject
        named_nakshatra = next((entity.name for entity in entities if entity.kind == "nakshatra"), None)
        return QuestionClassification(
            intent=UserIntent.GENERAL_EDUCATION,
            topic=QuestionTopic.HOUSE if education_topic == "houses" else QuestionTopic.GENERAL_OVERVIEW,
            education_topic=education_topic,
            education_subject=named_nakshatra,
            confidence=0.95,
        )

    # A bare pronoun cannot identify a chart fact. Leave it available for a
    # context resolver, which may bind it to a prior general-education subject.
    if _contains(normalized, ("its ruling planet", "its ruling lord", "what is its", "அதன் அதிபதி", "அதற்கு உரிய கிரகம்")):
        return QuestionClassification(
            intent=UserIntent.CLARIFICATION,
            confidence=0.75,
            needs_clarification=True,
            clarification_reason="referent_unclear",
        )

    is_astrology = _contains(normalized, _ASTRO_TA if language is SupportedLanguage.TA else _ASTRO_EN)
    if not is_astrology:
        vague = normalized.strip(" !?.。؟") in (_VAGUE_TA if language is SupportedLanguage.TA else _VAGUE_EN)
        if vague:
            return QuestionClassification(intent=UserIntent.CLARIFICATION, confidence=0.9, needs_clarification=True, clarification_reason="referent_unclear")
        return QuestionClassification(intent=UserIntent.UNSUPPORTED, confidence=0.82)

    has_vedic = _contains(normalized, ("vedic", "jyotish", "rashi", "lagna", "nakshatra", "dasha", "navamsa", "d1", "d9", "ஜோதிட", "ராசி", "நட்சத்திரம்", "தசை", "லக்னம்", "நவாம்ச", "பாதம்", "வேத"))
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

    explicit_d1 = _contains(normalized, ("d1", "rasi chart", "ராசி கட்டம்"))
    explicit_d9 = _contains(normalized, ("d9", "navamsa", "நவாம்ச"))
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
    elif (
        _contains(normalized, ("placement", "placements", "position", "positions", "நிலை"))
        and any(entity.kind == "planet" for entity in _mentions(normalized, language))
    ):
        topic = QuestionTopic.GENERAL_OVERVIEW
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
            entities=entities, confidence=0.96,
            # A broad personal chart request can be answered with the missing
            # chart state even when no system/division can yet be selected.
            # Only a real conflict or invalid explicit value needs clarification.
            needs_clarification=ambiguity not in {None, "astrology_system_not_specified"},
            clarification_reason=(ambiguity if ambiguity not in {None, "astrology_system_not_specified"} else None),
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
