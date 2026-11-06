"""Traditional sign-dignity classification over persisted Vedic D1 placements.

The encoded rule-set is deliberately marked provisional: it follows BPHS chapter 3
verses 49-55 as represented by accessible web witnesses, not a verified print
edition. It is a traditional classification, not a scientific strength score.
"""
from __future__ import annotations

import math
from typing import Any

from app.services.ai.source_registry import SourceRegistryError, get_default_source_registry
from app.services.astrology.sweph import RASHIS

DIGNITY_RULESET_ID = "parashari-bphs-ch3-web-witness-provisional-v1"
DIGNITY_RULESET_VERSION = "1.0.0"
SOURCE_ID = "vedic.bphs.vedicpupil.web-ch3"
RELATIONSHIP_SOURCE_ID = "vedic.bphs.parashara-net.web-ch3"
SOURCE_STATUS = "provisional_edition_unverified"
SOURCE_LOCATOR = "Chapter 3, verses 3.49-3.55 (web witnesses; exact print edition not verified)"
CLASSICAL_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")

# BPHS 3.49-50: exaltation sign and the opposite debilitation sign; peak degree.
EXALTATION = {
    "Sun": ("Mesha", 10.0), "Moon": ("Vrishabha", 3.0),
    "Mars": ("Makara", 28.0), "Mercury": ("Kanya", 15.0),
    "Jupiter": ("Karka", 5.0), "Venus": ("Meena", 27.0),
    "Saturn": ("Tula", 20.0),
}
DEBILITATION = {
    planet: (RASHIS[(RASHIS.index(sign) + 6) % 12], degree)
    for planet, (sign, degree) in EXALTATION.items()
}
# BPHS 3.51-54, with ranges represented as [start, end) degrees in the sign.
MOOLATRIKONA = {
    "Sun": ("Simha", 0.0, 20.0), "Moon": ("Vrishabha", 3.0, 30.0),
    "Mars": ("Mesha", 0.0, 12.0), "Mercury": ("Kanya", 15.0, 20.0),
    "Jupiter": ("Dhanu", 0.0, 10.0), "Venus": ("Tula", 0.0, 15.0),
    "Saturn": ("Kumbha", 0.0, 20.0),
}
OWN_SIGNS = {
    "Sun": {"Simha"}, "Moon": {"Karka"}, "Mars": {"Mesha", "Vrischika"},
    "Mercury": {"Mithuna", "Kanya"}, "Jupiter": {"Dhanu", "Meena"},
    "Venus": {"Vrishabha", "Tula"}, "Saturn": {"Makara", "Kumbha"},
}
SIGN_LORD = {
    "Mesha": "Mars", "Vrishabha": "Venus", "Mithuna": "Mercury", "Karka": "Moon",
    "Simha": "Sun", "Kanya": "Mercury", "Tula": "Venus", "Vrischika": "Mars",
    "Dhanu": "Jupiter", "Makara": "Saturn", "Kumbha": "Saturn", "Meena": "Jupiter",
}


class DignityInputError(ValueError):
    """Persisted chart data is incomplete or not a Vedic D1 chart."""


def _natural_relationships() -> dict[str, dict[str, str]]:
    """Derive permanent relations per the stated BPHS 3.55 house rule.

    From each planet's moolatrikona sign, the lords of houses 2, 4, 5, 8, 9,
    and 12, plus the lord of its exaltation sign, are friends; remaining lords
    are enemies; a planet meeting both conditions is neutral. This uses only
    the permanent relationship rule, not temporary chart relationships.
    """
    result: dict[str, dict[str, str]] = {}
    for planet, (base_sign, _, _) in MOOLATRIKONA.items():
        base = RASHIS.index(base_sign)
        friend_lords = {SIGN_LORD[RASHIS[(base + house - 1) % 12]] for house in (2, 4, 5, 8, 9, 12)}
        friend_lords.add(SIGN_LORD[EXALTATION[planet][0]])
        relations = {}
        for other in CLASSICAL_PLANETS:
            if other == planet:
                relations[other] = "self"
                continue
            is_friend = other in friend_lords
            is_enemy = any(SIGN_LORD[RASHIS[(base + house - 1) % 12]] == other for house in (3, 6, 7, 10, 11))
            # An exaltation lord may also own an enemy house; both marks resolve neutral.
            if is_friend and is_enemy:
                relations[other] = "neutral"
            elif is_friend:
                relations[other] = "friend"
            else:
                relations[other] = "enemy"
        result[planet] = relations
    return result


NATURAL_RELATIONSHIPS = _natural_relationships()


def _validate_chart(chart_result: dict[str, Any], *, chart_id: str, profile_id: str) -> list[dict[str, Any]]:
    if chart_result.get("calculation_system") != "vedic" or chart_result.get("division") != "D1":
        raise DignityInputError("Planetary dignity requires a completed Vedic D1 chart")
    raw_planets = chart_result.get("planets")
    if not isinstance(raw_planets, list):
        raise DignityInputError("Saved chart has no valid planetary placements")
    selected: dict[str, dict[str, Any]] = {}
    for entry in raw_planets:
        if not isinstance(entry, dict) or entry.get("name") not in CLASSICAL_PLANETS:
            continue
        name = entry["name"]
        if name in selected:
            raise DignityInputError(f"Saved chart contains duplicate {name} placements")
        raw_longitude = entry.get("longitude")
        if isinstance(raw_longitude, bool) or not isinstance(raw_longitude, (int, float)):
            raise DignityInputError(f"Saved chart has an invalid {name} longitude")
        try:
            longitude = float(raw_longitude)
        except (TypeError, ValueError) as exc:
            raise DignityInputError(f"Saved chart has an invalid {name} longitude") from exc
        if not math.isfinite(longitude) or not 0.0 <= longitude < 360.0:
            raise DignityInputError(f"Saved chart has an invalid {name} longitude")
        sign_index = int(longitude // 30.0)
        sign = RASHIS[sign_index]
        degree = longitude - sign_index * 30.0
        if entry.get("rashi") not in (None, sign) or entry.get("rashi_index") not in (None, sign_index):
            raise DignityInputError(f"Saved chart's {name} sign conflicts with its longitude")
        selected[name] = {"longitude": longitude, "sign": sign, "degree": degree}
    missing = [name for name in CLASSICAL_PLANETS if name not in selected]
    if missing:
        raise DignityInputError("Saved chart is missing required classical planets: " + ", ".join(missing))
    return [{"name": name, **selected[name]} for name in CLASSICAL_PLANETS]


def analyze_vedic_d1_dignity(chart_result: dict[str, Any], *, chart_id: str, profile_id: str) -> dict[str, Any]:
    """Classify the seven classical planets from a persisted D1 result only."""
    if not chart_id or not profile_id:
        raise DignityInputError("Chart and profile provenance are required")
    placements = _validate_chart(chart_result, chart_id=chart_id, profile_id=profile_id)
    try:
        registry = get_default_source_registry()
        source_records = {source.source_id: source for source in registry.sources}
        source_references = []
        for source_id in (SOURCE_ID, RELATIONSHIP_SOURCE_ID):
            source = source_records.get(source_id)
            if source is None:
                raise SourceRegistryError(f"Required dignity source {source_id} is not registered")
            source_references.append({
                "source_id": source.source_id,
                "edition_id": source.edition_id,
                "title": source.original_title,
                "edition": source.edition,
                "url": source.accessible_locations[0].url if source.accessible_locations else None,
                "verification_status": SOURCE_STATUS,
                "commercial_reuse_status": source.copyright.commercial_reuse_status,
            })
    except SourceRegistryError as exc:
        raise DignityInputError("The configured dignity source records are invalid") from exc
    output = []
    for placement in placements:
        planet, sign, degree = placement["name"], placement["sign"], placement["degree"]
        exalt_sign, peak = EXALTATION[planet]
        debilitated_sign, debil_peak = DEBILITATION[planet]
        mt_sign, mt_start, mt_end = MOOLATRIKONA[planet]
        relationship = NATURAL_RELATIONSHIPS[planet][SIGN_LORD[sign]]
        exalted_zone = sign == exalt_sign and not (sign == mt_sign and degree >= mt_start)
        if exalted_zone:
            dignity = "exalted"
        elif sign == debilitated_sign:
            dignity = "debilitated"
        elif sign == mt_sign and mt_start <= degree < mt_end:
            dignity = "moolatrikona"
        elif sign in OWN_SIGNS[planet]:
            dignity = "own_sign"
        else:
            dignity = f"{relationship}_sign"
        output.append({
            "planet": planet, "sidereal_longitude": placement["longitude"],
            "rashi": sign, "degree_in_rashi": degree, "sign_lord": SIGN_LORD[sign],
            "relationship_to_sign_lord": relationship, "dignity": dignity,
            "is_exalted_sign": sign == exalt_sign, "is_in_exaltation_range": exalted_zone,
            "is_debilitated_sign": sign == debilitated_sign,
            "exaltation_reference": {"sign": exalt_sign, "deep_degree": peak},
            "debilitation_reference": {"sign": debilitated_sign, "deep_degree": debil_peak},
            "is_at_deep_exaltation_degree": sign == exalt_sign and math.isclose(degree, peak, abs_tol=1e-9),
            "is_at_deep_debilitation_degree": sign == debilitated_sign and math.isclose(degree, debil_peak, abs_tol=1e-9),
            "is_moolatrikona": sign == mt_sign and mt_start <= degree < mt_end,
            "moolatrikona_range": {"sign": mt_sign, "start_degrees": mt_start, "end_degrees_exclusive": mt_end},
            "source_rule_set": DIGNITY_RULESET_ID,
            "source_id": SOURCE_ID,
            "source_ids": [SOURCE_ID, RELATIONSHIP_SOURCE_ID],
            "source_locator": SOURCE_LOCATOR,
        })
    return {
        "status": "provisional",
        "chart_id": chart_id,
        "profile_id": profile_id,
        "astrology_system": "vedic",
        "division": "D1",
        "zodiac": "sidereal",
        "ayanamsa": (chart_result.get("configuration") or {}).get("ayanamsa", "lahiri")
        if isinstance(chart_result.get("configuration") or {}, dict) else "lahiri",
        "ruleset_id": DIGNITY_RULESET_ID,
        "ruleset_version": DIGNITY_RULESET_VERSION,
        "source_id": SOURCE_ID,
        "source_ids": [SOURCE_ID, RELATIONSHIP_SOURCE_ID],
        "source_references": source_references,
        "source_status": SOURCE_STATUS,
        "source_locator": SOURCE_LOCATOR,
        "methodology_note": "Provisional traditional Parashari sign dignities from BPHS chapter 3 web witnesses. Exact print edition and translation are not verified. Not a scientific measurement. Rahu and Ketu are not assigned dignity classifications.",
        "shadbala": {"status": "unavailable", "reason": "No edition-verified complete Shadbala method is configured."},
        "planets": output,
        "excluded_planets": ["Rahu", "Ketu"],
    }
