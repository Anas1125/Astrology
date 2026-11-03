"""Deterministic, provenance-validated assembly of localized astrology responses.

This module formats saved facts and eligible editorial rules only. It does not
calculate charts, infer missing placements, or generate interpretation content.
"""
from __future__ import annotations

import re

from app.services.ai.contracts import (
    AstrologySystem,
    ChartFact,
    ChartFacts,
    IntelligenceResponse,
    IntelligenceResponseMetadata,
    MatchedFactReference,
    MatchedInterpretationRule,
    MatchedRuleReference,
    QuestionClassification,
    QuestionTopic,
    ResponseSection,
    ResponseSectionType,
    ResponseStatus,
    RuleMatchResult,
    SupportedLanguage,
    UserIntent,
)
from app.services.ai.rule_matcher import _validate_chart_facts
from app.services.ai.source_registry import (
    SourceRegistryError,
    get_default_source_registry,
    validate_provenance_source_link,
)

ENGINE_VERSION = "1.0.0"
DEFAULT_KNOWLEDGE_BASE_VERSION = "1.0.0"
MAX_RESPONSE_CHARACTERS = 6000
MAX_RESPONSE_SECTIONS = 24


class InvalidIntelligenceResponse(ValueError):
    """A response cannot be safely emitted with complete provenance."""


_PLANET_TA = {
    "sun": "சூரியன்", "moon": "சந்திரன்", "mercury": "புதன்", "venus": "சுக்கிரன்",
    "mars": "செவ்வாய்", "jupiter": "குரு", "saturn": "சனி", "uranus": "யுரேனஸ்",
    "neptune": "நெப்டியூன்", "pluto": "புளூட்டோ", "rahu": "ராகு", "ketu": "கேது",
}
_SIGN_TA = {
    "aries": "மேஷம்", "mesha": "மேஷம்", "taurus": "ரிஷபம்", "vrishabha": "ரிஷபம்",
    "gemini": "மிதுனம்", "mithuna": "மிதுனம்", "cancer": "கடகம்", "karka": "கடகம்",
    "leo": "சிம்மம்", "simha": "சிம்மம்", "virgo": "கன்னி", "kanya": "கன்னி",
    "libra": "துலாம்", "tula": "துலாம்", "scorpio": "விருச்சிகம்", "vrischika": "விருச்சிகம்",
    "sagittarius": "தனுசு", "dhanu": "தனுசு", "capricorn": "மகரம்", "makara": "மகரம்",
    "aquarius": "கும்பம்", "kumbha": "கும்பம்", "pisces": "மீனம்", "meena": "மீனம்",
}
_NAKSHATRA_TA = {
    "Ashwini": "அசுவினி", "Bharani": "பரணி", "Krittika": "கார்த்திகை", "Rohini": "ரோகிணி",
    "Mrigashira": "மிருகசீரிடம்", "Ardra": "திருவாதிரை", "Punarvasu": "புனர்பூசம்",
    "Pushya": "பூசம்", "Ashlesha": "ஆயில்யம்", "Magha": "மகம்", "Purva Phalguni": "பூரம்",
    "Uttara Phalguni": "உத்திரம்", "Hasta": "ஹஸ்தம்", "Chitra": "சித்திரை", "Swati": "சுவாதி",
    "Vishakha": "விசாகம்", "Anuradha": "அனுஷம்", "Jyeshtha": "கேட்டை", "Mula": "மூலம்",
    "Purva Ashadha": "பூராடம்", "Uttara Ashadha": "உத்திராடம்", "Shravana": "திருவோணம்",
    "Dhanishta": "அவிட்டம்", "Shatabhisha": "சதயம்", "Purva Bhadrapada": "பூரட்டாதி",
    "Uttara Bhadrapada": "உத்திரட்டாதி", "Revati": "ரேவதி",
}
_PREDICATE_LABELS = {
    "longitude": ("ecliptic longitude", "கிராந்திவட்ட நீளம்"), "sign": ("sign", "ராசி"),
    "rashi": ("Rashi", "ராசி"), "house": ("house", "பாவம்"),
    "retrograde": ("retrograde", "வக்கிரம்"), "nakshatra.name": ("Nakshatra", "நட்சத்திரம்"),
    "nakshatra.lord": ("Nakshatra lord", "நட்சத்திர அதிபதி"),
    "nakshatra.pada": ("Pada", "பாதம்"), "nakshatra.remaining_fraction": ("remaining fraction", "மீதமுள்ள பங்கு"),
    "d9.rashi": ("D9 Rashi", "நவாம்ச ராசி"), "d9.rashi_index": ("D9 Rashi index", "நவாம்ச ராசி எண்"),
    "d9.longitude": ("D9 longitude", "நவாம்ச நீளம்"), "cusp_longitude": ("house cusp longitude", "பாவ முனை நீளம்"),
    "nakshatra": ("Nakshatra", "நட்சத்திரம்"), "pada": ("Pada", "பாதம்"),
    "year_convention": ("year convention", "ஆண்டு கணிப்பு முறை"),
    "starting_nakshatra": ("starting Nakshatra", "தொடக்க நட்சத்திரம்"),
    "starting_lord": ("starting Dasha lord", "தொடக்க தசை அதிபதி"),
    "birth_balance_days": ("birth balance in days", "பிறப்பின்போது மீதமுள்ள நாட்கள்"),
    "lord": ("period lord", "கால அதிபதி"), "sub_lord": ("sub-period lord", "உபகால அதிபதி"),
    "start": ("period start", "காலத் தொடக்கம்"), "end": ("period end", "கால முடிவு"),
    "nominal_start": ("nominal period start", "குறிப்பிட்ட காலத் தொடக்கம்"),
    "nominal_end": ("nominal period end", "குறிப்பிட்ட கால முடிவு"),
    "aspect": ("aspect", "கிரகத் தொடர்பு"), "orb": ("orb", "கோண விலகல்"),
    "motion": ("aspect motion", "தொடர்பின் இயக்கம்"),
}
_ASPECT_TA = {
    "conjunction": "சேர்க்கை", "sextile": "அறுபது பாகைத் தொடர்பு", "square": "சதுரத் தொடர்பு",
    "trine": "முக்கோணத் தொடர்பு", "opposition": "எதிர்த் தொடர்பு",
    "applying": "நெருங்கும்", "separating": "விலகும்", "direct": "நேர்ச் சுழற்சி",
    "retrograde": "வக்கிரம்",
}
_UNSAFE_INTERPRETATION = re.compile(
    r"\b(?:guarantee[sd]?|certainly|definitely|will\s+(?:happen|occur|marry|die|succeed)|"
    r"diagnos(?:e|is|ed)|cure[sd]?|treat(?:ment)?|financial\s+advice|legal\s+advice)\b|"
    r"உறுதியாக\s+நடக்கும்|நிச்சயம்\s+நடக்கும்|நோயறிதல்|குணமாக்கும்",
    re.IGNORECASE,
)
_PRIVATE_MARKERS = re.compile(
    r"\b(?:date\s+of\s+birth|birth\s+date|birth\s+time|birthplace|latitude|timezone|"
    r"email|password|access_token)\b|பிறந்த\s+(?:தேதி|நேரம்|இடம்)",
    re.IGNORECASE,
)


def fact_identifier(chart_id: str, fact: ChartFact) -> str:
    return f"fact:{chart_id}:{fact.subject}.{fact.predicate}"


def _localize_value(value: object, language: SupportedLanguage, predicate: str) -> str:
    text = str(value)
    if language is SupportedLanguage.EN:
        return text
    folded = text.casefold()
    if predicate in {"sign", "rashi", "d9.rashi"}:
        return _SIGN_TA.get(folded, text)
    if predicate in {"nakshatra", "nakshatra.name", "starting_nakshatra"}:
        return next((localized for name, localized in _NAKSHATRA_TA.items() if name.casefold() == folded), text)
    if predicate in {"aspect", "motion"}:
        return _ASPECT_TA.get(folded, text)
    if isinstance(value, bool):
        return "ஆம்" if value else "இல்லை"
    return text


def _subject_label(subject: str, language: SupportedLanguage) -> str:
    if subject.startswith("Aspect:"):
        bodies = subject.split(":", 1)[1].split("/")
        if language is SupportedLanguage.EN:
            return "/".join(bodies)
        return " / ".join(_PLANET_TA.get(body.casefold(), body) for body in bodies)
    if language is SupportedLanguage.EN:
        return subject
    if subject.casefold() in _PLANET_TA:
        return _PLANET_TA[subject.casefold()]
    if subject.casefold() in {"ascendant", "midheaven"}:
        return "லக்னம்" if subject.casefold() == "ascendant" else "மத்திய வான்புள்ளி"
    if subject.startswith("House:"):
        return f"{subject.split(':', 1)[1]}ஆம் பாவம்"
    if subject == "Vimshottari":
        return "விம்சோத்தரி தசை"
    if subject.startswith("Dasha:"):
        return f"{_PLANET_TA.get(subject.split(':', 1)[1].casefold(), subject.split(':', 1)[1])} மகாதசை"
    if subject.startswith("Antardasha:"):
        return "அந்தர்தசை"
    return subject


def _fact_text(fact: ChartFact, language: SupportedLanguage) -> str:
    label = _PREDICATE_LABELS.get(fact.predicate, (fact.predicate, fact.predicate))[0 if language is SupportedLanguage.EN else 1]
    subject = _subject_label(fact.subject, language)
    value = _localize_value(fact.value, language, fact.predicate)
    if language is SupportedLanguage.EN:
        if fact.predicate == "sign" and fact.subject not in {"ascendant", "midheaven"}:
            return f"{subject} is recorded in {value}."
        if fact.predicate == "retrograde":
            state = "retrograde" if fact.value else "direct"
            return f"{subject} is recorded as {state}."
        if fact.predicate == "house":
            return f"{subject} is recorded in house {value}."
        return f"{subject}: {label} — {value}."
    if fact.predicate == "sign" and fact.subject not in {"ascendant", "midheaven"}:
        return f"{subject} {value} ராசியில் உள்ளது."
    if fact.predicate == "retrograde":
        state = "வக்கிர நிலையில் உள்ளது" if fact.value else "நேர்ச் சுழற்சியில் உள்ளது"
        return f"{subject} {state}."
    if fact.predicate == "house":
        return f"{subject} {value}ஆம் பாவத்தில் உள்ளது."
    return f"{subject}: {label} — {value}."


def _fact_is_relevant(fact: ChartFact, classification: QuestionClassification) -> bool:
    topic = classification.topic
    subject = fact.subject.casefold()
    predicate = fact.predicate.casefold()
    if topic is QuestionTopic.PLANET:
        relevant = subject not in {"vimshottari"} and not subject.startswith(("house:", "aspect:")) and not subject.startswith(("dasha:", "antardasha:"))
    elif topic is QuestionTopic.SIGN:
        relevant = predicate in {"sign", "rashi", "d9.rashi"}
    elif topic is QuestionTopic.HOUSE:
        relevant = predicate == "house" or subject.startswith("house:")
    elif topic in {QuestionTopic.NAKSHATRA, QuestionTopic.PADA}:
        relevant = predicate.startswith("nakshatra.") or predicate in {"nakshatra", "pada"}
    elif topic is QuestionTopic.DASHA:
        relevant = subject == "vimshottari" or subject.startswith(("dasha:", "antardasha:"))
    elif topic is QuestionTopic.ASPECT:
        relevant = subject.startswith("aspect:")
    elif topic is QuestionTopic.GENERAL_OVERVIEW:
        relevant = True
    else:
        relevant = False

    if not relevant:
        return False
    for entity in classification.entities:
        name = entity.name.casefold()
        if entity.kind == "division":
            continue
        if entity.kind == "planet":
            related = subject == name or subject.startswith(f"{name}:") or subject.startswith(f"dasha:{name}") or subject.startswith(f"antardasha:{name}/") or subject == "vimshottari" and predicate == "starting_lord" and str(fact.value).casefold() == name or subject.startswith("aspect:") and name in subject.removeprefix("aspect:").split("/")
            if not related:
                return False
        elif entity.kind == "sign":
            if predicate not in {"sign", "rashi", "d9.rashi"} or str(fact.value).casefold() != name:
                return False
        elif entity.kind == "house":
            if not (subject == f"house:{name}" or predicate == "house" and str(fact.value) == name):
                return False
        elif entity.kind == "nakshatra":
            if predicate != "nakshatra.name" or str(fact.value).casefold() != name:
                return False
        elif entity.kind == "dasha_lord":
            if not (subject == f"dasha:{name}" or subject.startswith(f"antardasha:{name}/") or predicate in {"starting_lord", "lord", "sub_lord"} and str(fact.value).casefold() == name):
                return False
        elif entity.kind == "aspect":
            if predicate != "aspect" or str(fact.value).casefold() != name:
                return False
    return True


def _localized(language: SupportedLanguage, key: str, **values: object) -> str:
    templates = {
        "en": {
            "greeting": "Hello. Ask about a saved Vedic or Western chart, or choose a chart first.",
            "unsupported": "I can help with supported questions about saved Vedic or Western astrology charts. This request is outside that scope.",
            "general_unavailable": "There is no approved, sourced general astrology explanation for this topic yet. I will not invent one.",
            "clarification": "Please clarify which astrology system, chart division, or chart detail you want to ask about.",
            "missing": "A completed saved chart for this profile and system is not available. No chart facts have been inferred.",
            "no_fact": "The requested detail is not present in the saved chart data.",
            "fact_summary": "I found {count} relevant calculated chart fact(s) in the saved chart.",
            "no_rule": "A sourced traditional interpretation is not currently available for this question.",
            "conflict": "Some matched traditional notes were withheld because they conflict; they are not combined.",
            "safety": "Astrology is a traditional belief system, not scientific certainty. Do not rely on it for medical, legal, or financial decisions.",
        },
        "ta": {
            "greeting": "வணக்கம். சேமிக்கப்பட்ட வேத அல்லது மேற்கத்திய ஜாதகம் குறித்து கேளுங்கள்; அல்லது முதலில் ஒரு ஜாதகத்தைத் தேர்ந்தெடுக்கவும்.",
            "unsupported": "சேமிக்கப்பட்ட வேத அல்லது மேற்கத்திய ஜாதகத் தகவல்கள் தொடர்பான கேள்விகளில் உதவ முடியும். இந்தக் கோரிக்கை அந்த வரம்பிற்கு வெளியே உள்ளது.",
            "general_unavailable": "இந்தத் தலைப்பிற்கான அங்கீகரிக்கப்பட்ட, ஆதாரமுள்ள பொதுவான ஜோதிட விளக்கம் இன்னும் இல்லை. ஊகித்து விளக்கம் வழங்கப்படாது.",
            "clarification": "நீங்கள் கேட்க விரும்பும் ஜோதிட முறை, ஜாதகப் பிரிவு அல்லது விவரத்தைத் தெளிவுபடுத்துங்கள்.",
            "missing": "இந்த சுயவிவரம் மற்றும் முறைக்கான முழுமையான சேமிக்கப்பட்ட ஜாதகம் இல்லை. ஜாதகத் தகவல்கள் ஊகிக்கப்படவில்லை.",
            "no_fact": "கேட்ட விவரம் சேமிக்கப்பட்ட ஜாதகத் தரவில் இல்லை.",
            "fact_summary": "சேமிக்கப்பட்ட ஜாதகத்தில் {count} தொடர்புடைய கணக்கிடப்பட்ட தகவல்(கள்) கிடைத்தன.",
            "no_rule": "இந்தக் கேள்விக்கான ஆதாரமுள்ள பாரம்பரிய விளக்கம் தற்போது கிடைக்கவில்லை.",
            "conflict": "முரண்படும் சில பாரம்பரிய குறிப்புகள் ஒன்றிணைக்கப்படாமல் விலக்கப்பட்டுள்ளன.",
            "safety": "ஜோதிடம் ஒரு பாரம்பரிய நம்பிக்கை முறை; அறிவியல் உறுதி அல்ல. மருத்துவ, சட்ட அல்லது நிதி முடிவுகளுக்கு இதை மட்டும் நம்ப வேண்டாம்.",
        },
    }
    return templates[language.value][key].format(**values)


def _rule_reference(rule: MatchedInterpretationRule) -> MatchedRuleReference:
    return MatchedRuleReference(
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        knowledge_base_version=rule.knowledge_base_version,
        chart_id=rule.chart_id,
        profile_id=rule.profile_id,
        system=rule.system,
        division=rule.division,
        source_name=rule.provenance.source_name,
        attribution=rule.provenance.attribution,
        reference=rule.provenance.reference,
        editorial_status=rule.provenance.editorial_status,
        classification=rule.provenance.classification,
        source_id=rule.provenance.source_id,
        source_registry_version=rule.provenance.source_registry_version,
        edition_id=rule.provenance.edition_id,
        edition=rule.provenance.edition,
        chapter=rule.provenance.chapter,
        verse=rule.provenance.verse,
        page=rule.provenance.page,
        section=rule.provenance.section,
    )


def _validate_rule_matches(
    result: RuleMatchResult | None,
    chart: ChartFacts | None,
    language: SupportedLanguage,
) -> tuple[MatchedInterpretationRule, ...]:
    if result is None:
        return ()
    if chart is None or not chart.available or not chart.chart_id or not chart.profile_id or not chart.system:
        if result.matches:
            raise InvalidIntelligenceResponse("Rule matches cannot be attached without an available chart")
        return ()
    if result.chart_id != chart.chart_id or result.profile_id != chart.profile_id:
        raise InvalidIntelligenceResponse("Rule-match identity does not match the selected saved chart")
    if not result.eligible:
        raise InvalidIntelligenceResponse("Ineligible rule-match results cannot be emitted")
    facts = {(fact.subject, fact.predicate): fact for fact in chart.facts}
    if len(facts) != len(chart.facts):
        raise InvalidIntelligenceResponse("Chart facts contain duplicate fields")
    rule_ids = [item.rule_id for item in result.matches]
    if len(rule_ids) != len(set(rule_ids)):
        raise InvalidIntelligenceResponse("Duplicate matched rule identifiers")
    conflicted: set[str] = set()
    for conflict in result.conflicts:
        if len(conflict.rule_ids) < 2 or not set(conflict.rule_ids) <= set(rule_ids):
            raise InvalidIntelligenceResponse("Conflict metadata does not correspond to matched rules")
        conflicted.update(conflict.rule_ids)

    valid: list[MatchedInterpretationRule] = []
    for match in sorted(result.matches, key=lambda item: item.rule_id):
        provenance = match.provenance
        if provenance.editorial_status != "approved":
            raise InvalidIntelligenceResponse("Only approved interpretation rules may be composed")
        if provenance.classification != "traditional_interpretation":
            raise InvalidIntelligenceResponse("Matched rule classification is not eligible")
        if not all(value.strip() and value.strip().casefold() not in {"n/a", "na", "none", "unknown", "unsourced", "test", "test only"} and len(value.strip()) >= minimum for value, minimum in (
            (provenance.source_name, 3), (provenance.attribution, 3), (provenance.reference, 12),
        )):
            raise InvalidIntelligenceResponse("Matched interpretation lacks adequate source attribution")
        if not all((provenance.source_id, provenance.source_registry_version, provenance.edition_id, provenance.edition,
                    provenance.editorial_explanation, provenance.editorial_reviewer,
                    provenance.translation_reviewer, provenance.reviewed_at)):
            raise InvalidIntelligenceResponse("Matched interpretation lacks source edition or review metadata")
        if not any((provenance.chapter, provenance.verse, provenance.page, provenance.section)):
            raise InvalidIntelligenceResponse("Matched interpretation lacks an exact source locator")
        if provenance.translation_review_status != "reviewed":
            raise InvalidIntelligenceResponse("Matched interpretation lacks bilingual review")
        try:
            validate_provenance_source_link(
                provenance, get_default_source_registry(), rule_id=match.rule_id, system=match.system,
            )
        except SourceRegistryError as exc:
            raise InvalidIntelligenceResponse(str(exc)) from exc
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]+", match.rule_id) or not re.fullmatch(r"\d+\.\d+\.\d+", match.rule_version):
            raise InvalidIntelligenceResponse("Matched interpretation has an invalid identifier or version")
        if match.language is not language or match.system is not chart.system:
            raise InvalidIntelligenceResponse("Matched rule language or system does not match the response")
        if match.chart_id != chart.chart_id or match.profile_id != chart.profile_id:
            raise InvalidIntelligenceResponse("Matched rule chart/profile provenance mismatch")
        division_matches = match.division is None or chart.division is None or match.division.casefold() == chart.division.casefold()
        if chart.system is AstrologySystem.WESTERN and {str(match.division).casefold(), str(chart.division).casefold()} <= {"w", "natal"}:
            division_matches = True
        if not division_matches:
            raise InvalidIntelligenceResponse("Matched rule chart division provenance mismatch")
        if match.knowledge_base_version == "" or not re.fullmatch(r"\d+\.\d+\.\d+", match.knowledge_base_version):
            raise InvalidIntelligenceResponse("Matched rule has an invalid knowledge-base version")
        if not match.fact_references:
            raise InvalidIntelligenceResponse("Matched rule has no supporting chart facts")
        for reference in match.fact_references:
            fact = facts.get((reference.subject, reference.predicate))
            if (
                fact is None
                or reference.source_chart_id != chart.chart_id
                or reference.profile_id != chart.profile_id
                or reference.system is not chart.system
                or reference.division != chart.division
                or fact.value != reference.value
                or fact.provenance != reference.provenance
                or reference.fact_id != fact_identifier(chart.chart_id, fact)
            ):
                raise InvalidIntelligenceResponse("Matched rule references a missing or foreign chart fact")
        if _UNSAFE_INTERPRETATION.search(match.text):
            raise InvalidIntelligenceResponse("Matched interpretation contains a prohibited guarantee or advice claim")
        if match.rule_id not in conflicted:
            valid.append(match)
    return tuple(valid)


def validate_intelligence_response(
    response: IntelligenceResponse,
    *,
    chart: ChartFacts | None,
    max_characters: int = MAX_RESPONSE_CHARACTERS,
    max_sections: int = MAX_RESPONSE_SECTIONS,
) -> IntelligenceResponse:
    """Fail closed on unsupported references, private data, or unbounded output."""
    all_text = [response.answer, *(section.text for section in response.sections)]
    if not 0 < len(response.answer) <= 1000 or len(response.sections) > max_sections:
        raise InvalidIntelligenceResponse("Response exceeds section or answer bounds")
    if sum(len(text) for text in all_text) > max_characters:
        raise InvalidIntelligenceResponse("Response exceeds configured character limit")
    if any(_PRIVATE_MARKERS.search(text) for text in all_text):
        raise InvalidIntelligenceResponse("Response contains a private birth or account detail")
    if len(set(response.answer_fact_ids)) != len(response.answer_fact_ids) or len(set(response.answer_rule_ids)) != len(response.answer_rule_ids):
        raise InvalidIntelligenceResponse("Answer provenance contains duplicate references")
    fact_sources: dict[str, MatchedFactReference] = {}
    rule_sources: dict[str, MatchedRuleReference] = {}
    for section in response.sections:
        if set(section.fact_ids) != {source.fact_id for source in section.fact_references}:
            raise InvalidIntelligenceResponse("Section fact IDs do not match its fact provenance")
        if set(section.rule_ids) != {source.rule_id for source in section.rule_references}:
            raise InvalidIntelligenceResponse("Section rule IDs do not match its rule provenance")
        if section.section_type is ResponseSectionType.CALCULATED_FACT:
            if not section.fact_references or section.rule_references:
                raise InvalidIntelligenceResponse("Calculated fact section has invalid provenance")
        if section.section_type is ResponseSectionType.TRADITIONAL_INTERPRETATION:
            if not section.rule_references or not section.fact_references:
                raise InvalidIntelligenceResponse("Interpretation section has invalid provenance")
            if any(source.editorial_status != "approved" or not source.source_name or not source.attribution or not source.reference for source in section.rule_references):
                raise InvalidIntelligenceResponse("Interpretation source attribution is incomplete")
        for source in section.fact_references:
            fact_sources[source.fact_id] = source
        for source in section.rule_references:
            if source.editorial_status != "approved" or source.classification != "traditional_interpretation":
                raise InvalidIntelligenceResponse("Response contains an ineligible rule source")
            if chart is None or (
                source.chart_id != chart.chart_id
                or source.profile_id != chart.profile_id
                or source.system is not chart.system
            ):
                raise InvalidIntelligenceResponse("Response rule belongs to another chart or profile")
            if not source.source_name.strip() or not source.attribution.strip() or len(source.reference.strip()) < 12:
                raise InvalidIntelligenceResponse("Response rule source attribution is incomplete")
            if not all((source.source_id, source.source_registry_version, source.edition_id, source.edition)) or not any(
                (source.chapter, source.verse, source.page, source.section)
            ):
                raise InvalidIntelligenceResponse("Response rule source locator is incomplete")
            try:
                registry_source = next(
                    (item for item in get_default_source_registry().sources if item.source_id == source.source_id), None
                )
            except SourceRegistryError as exc:
                raise InvalidIntelligenceResponse("Source registry is invalid") from exc
            if (registry_source is None or registry_source.edition_id != source.edition_id
                    or registry_source.edition != source.edition
                    or registry_source.system is not source.system
                    or get_default_source_registry().registry_version != source.source_registry_version):
                raise InvalidIntelligenceResponse("Response rule source is not registered for this edition")
            rule_sources[source.rule_id] = source
    if not set(response.answer_fact_ids) <= fact_sources.keys() or not set(response.answer_rule_ids) <= rule_sources.keys():
        raise InvalidIntelligenceResponse("Answer summary cites facts or rules absent from response sections")
    if response.answer_rule_ids and not any(section.section_type is ResponseSectionType.TRADITIONAL_INTERPRETATION for section in response.sections):
        raise InvalidIntelligenceResponse("Answer cites an interpretation without an interpretation section")
    emitted_rule_ids = tuple(sorted(rule_sources))
    if tuple(sorted(response.metadata.matched_rule_ids)) != emitted_rule_ids:
        raise InvalidIntelligenceResponse("Response metadata rule IDs do not match emitted interpretations")
    if any(source.knowledge_base_version != response.metadata.knowledge_base_version for source in rule_sources.values()):
        raise InvalidIntelligenceResponse("Response rule knowledge-base version does not match metadata")
    if response.metadata.system is not None and chart is not None and chart.system is not response.metadata.system:
        raise InvalidIntelligenceResponse("Response system does not match its chart")
    if chart is not None:
        actual_facts = {fact_identifier(chart.chart_id or "", fact): fact for fact in chart.facts}
        for fact_id, reference in fact_sources.items():
            fact = actual_facts.get(fact_id)
            if fact is None or (fact.subject, fact.predicate, fact.value, fact.provenance) != (
                reference.subject, reference.predicate, reference.value, reference.provenance,
            ):
                raise InvalidIntelligenceResponse("Response contains an invalid chart fact reference")
            if reference.source_chart_id != chart.chart_id or reference.profile_id != chart.profile_id:
                raise InvalidIntelligenceResponse("Response fact belongs to another chart or profile")
            if reference.system is not chart.system or reference.division != chart.division:
                raise InvalidIntelligenceResponse("Response fact system or division does not match the chart")
    if response.status is ResponseStatus.ANSWERED and not any(
        section.section_type is ResponseSectionType.LIMITATION and _is_safety_limitation(section.text)
        for section in response.sections
    ) and response.metadata.system is not None:
        raise InvalidIntelligenceResponse("Astrology response is missing its safety limitation")
    return response


def _is_safety_limitation(text: str) -> bool:
    return "scientific certainty" in text.casefold() or "அறிவியல் உறுதி அல்ல" in text


def compose_response(
    classification: QuestionClassification,
    chart: ChartFacts | None,
    rule_matches: RuleMatchResult | None,
    *,
    language: SupportedLanguage | str,
    knowledge_base_version: str = DEFAULT_KNOWLEDGE_BASE_VERSION,
    engine_version: str = ENGINE_VERSION,
) -> IntelligenceResponse:
    """Compose an answer using fixed localized templates, saved facts and approved rules."""
    language = SupportedLanguage(language)
    if not re.fullmatch(r"\d+\.\d+\.\d+", knowledge_base_version):
        raise InvalidIntelligenceResponse("Invalid knowledge-base version")
    if not re.fullmatch(r"\d+\.\d+\.\d+", engine_version):
        raise InvalidIntelligenceResponse("Invalid intelligence engine version")
    system = chart.system if chart and chart.available and chart.system else classification.system
    division = chart.division if chart and chart.available and chart.division else classification.division
    sections: list[ResponseSection] = []
    status: ResponseStatus
    answer_fact_ids: tuple[str, ...] = ()
    answer_rule_ids: tuple[str, ...] = ()

    if classification.intent in {UserIntent.UNSUPPORTED}:
        status = ResponseStatus.UNSUPPORTED
        answer = _localized(
            language,
            "general_unavailable" if classification.clarification_reason == "general_knowledge_not_approved" else "unsupported",
        )
        sections.append(ResponseSection(section_type=ResponseSectionType.LIMITATION, text=answer))
    elif classification.intent in {UserIntent.CLARIFICATION, UserIntent.GREETING} or classification.needs_clarification:
        status = ResponseStatus.NEEDS_CLARIFICATION
        answer = _localized(language, "greeting" if classification.intent is UserIntent.GREETING else "clarification")
        sections.append(ResponseSection(section_type=ResponseSectionType.LIMITATION, text=answer))
    elif classification.intent is UserIntent.MISSING_CHART or chart is None or not chart.available:
        status = ResponseStatus.MISSING_CHART
        answer = _localized(language, "missing")
        sections.append(ResponseSection(section_type=ResponseSectionType.LIMITATION, text=answer))
    elif classification.intent is not UserIntent.CHART_QUESTION:
        status = ResponseStatus.UNSUPPORTED
        answer = _localized(language, "unsupported")
        sections.append(ResponseSection(section_type=ResponseSectionType.LIMITATION, text=answer))
    else:
        if chart.system is None or not chart.chart_id or not chart.profile_id:
            raise InvalidIntelligenceResponse("Available chart lacks identity or system")
        if classification.system is not None and classification.system is not chart.system:
            raise InvalidIntelligenceResponse("Question and chart systems do not match")
        requested_division = classification.division
        division_matches = requested_division is None or chart.division is None or requested_division.casefold() == chart.division.casefold()
        if chart.system is AstrologySystem.WESTERN and {str(requested_division).casefold(), str(chart.division).casefold()} <= {"w", "natal"}:
            division_matches = True
        if not division_matches:
            raise InvalidIntelligenceResponse("Question and chart divisions do not match")
        rejection = _validate_chart_facts(chart)
        if rejection:
            raise InvalidIntelligenceResponse(f"Chart facts failed validation: {rejection}")
        for fact in chart.facts:
            if chart.system is AstrologySystem.WESTERN and (
                fact.predicate.startswith(("nakshatra.", "d9."))
                or fact.subject == "Vimshottari"
                or fact.subject.startswith(("Dasha:", "Antardasha:"))
            ):
                raise InvalidIntelligenceResponse("Chart contains a Vedic-only fact in a Western chart")
            if chart.system is AstrologySystem.VEDIC and fact.subject.startswith("Aspect:"):
                raise InvalidIntelligenceResponse("Chart contains a Western aspect fact in a Vedic chart")
            if chart.system is AstrologySystem.VEDIC and chart.division == "D1" and fact.predicate.startswith("d9."):
                raise InvalidIntelligenceResponse("D1 chart contains a D9-only fact")
            if chart.system is AstrologySystem.VEDIC and chart.division == "D9" and fact.predicate.startswith("nakshatra."):
                raise InvalidIntelligenceResponse("D9 chart contains a D1-only Nakshatra fact")
        if rule_matches and (rule_matches.chart_id != chart.chart_id or rule_matches.profile_id != chart.profile_id):
            raise InvalidIntelligenceResponse("Rule matches belong to another chart or profile")
        approved_matches = _validate_rule_matches(rule_matches, chart, language)
        relevant_facts = tuple(sorted(
            (fact for fact in chart.facts if _fact_is_relevant(fact, classification)),
            key=lambda fact: (fact.subject, fact.predicate, fact_identifier(chart.chart_id or "", fact)),
        ))
        fact_refs_by_key: dict[tuple[str, str], MatchedFactReference] = {}
        for fact in relevant_facts:
            reference = MatchedFactReference(
                fact_id=fact_identifier(chart.chart_id, fact),
                subject=fact.subject,
                predicate=fact.predicate,
                value=fact.value,
                source_chart_id=chart.chart_id,
                profile_id=chart.profile_id,
                system=chart.system,
                division=fact.division,
                provenance=fact.provenance,
            )
            fact_refs_by_key[(fact.subject, fact.predicate)] = reference
            sections.append(ResponseSection(
                section_type=ResponseSectionType.CALCULATED_FACT,
                text=_fact_text(fact, language),
                fact_ids=(reference.fact_id,),
                fact_references=(reference,),
            ))
        answer_fact_ids = tuple(ref.fact_id for ref in fact_refs_by_key.values())
        if relevant_facts:
            answer = _localized(language, "fact_summary", count=len(relevant_facts))
        else:
            answer = _localized(language, "no_fact")
            sections.append(ResponseSection(section_type=ResponseSectionType.LIMITATION, text=answer))

        for match in approved_matches:
            if match.rule_id in {rule_id for conflict in (rule_matches.conflicts if rule_matches else ()) for rule_id in conflict.rule_ids}:
                continue
            # The original, reviewed text is copied verbatim and never synthesized or translated.
            if match.language is not language:
                raise InvalidIntelligenceResponse("Interpretation localization does not match response language")
            references = tuple(sorted(match.fact_references, key=lambda ref: ref.fact_id))
            rule_ref = _rule_reference(match)
            sections.append(ResponseSection(
                section_type=ResponseSectionType.TRADITIONAL_INTERPRETATION,
                text=match.text,
                fact_ids=tuple(ref.fact_id for ref in references),
                rule_ids=(match.rule_id,),
                fact_references=references,
                rule_references=(rule_ref,),
            ))
        included_rule_ids = tuple(
            sorted(section.rule_ids[0] for section in sections if section.section_type is ResponseSectionType.TRADITIONAL_INTERPRETATION)
        )
        answer_rule_ids = included_rule_ids
        matched_conflicts = bool(rule_matches and rule_matches.conflicts)
        if not included_rule_ids:
            sections.append(ResponseSection(
                section_type=ResponseSectionType.LIMITATION,
                text=_localized(language, "no_rule"),
            ))
        if matched_conflicts:
            sections.append(ResponseSection(
                section_type=ResponseSectionType.LIMITATION,
                text=_localized(language, "conflict"),
            ))
        sections.append(ResponseSection(
            section_type=ResponseSectionType.LIMITATION,
            text=_localized(language, "safety"),
        ))
        status = ResponseStatus.ANSWERED

    response = IntelligenceResponse(
        status=status,
        answer=answer,
        answer_fact_ids=answer_fact_ids,
        answer_rule_ids=answer_rule_ids,
        sections=tuple(sections),
        metadata=IntelligenceResponseMetadata(
            engine_version=engine_version,
            knowledge_base_version=knowledge_base_version,
            system=system,
            division=division,
            language=language,
            matched_rule_ids=answer_rule_ids,
        ),
    )
    return validate_intelligence_response(response, chart=chart)
