"""Build minimal AI context strictly from an owned, persisted completed calculation."""
from typing import Any


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _planet_facts(planet: dict[str, Any], system: str, division: str) -> dict[str, Any]:
    facts: dict[str, Any] = {"name": planet.get("name")}
    use_division = system == "vedic" and division == "D9"
    source = {**planet, "longitude": planet.get("division_longitude"), "house": planet.get("division_house")} if use_division else planet
    for key in ("longitude", "house", "retrograde"):
        value = source.get(key)
        if value is not None and (key != "longitude" or _number(value)):
            facts[key] = value
    sign = (planet.get("division_rashi") if use_division else planet.get("rashi")) if system == "vedic" else planet.get("sign")
    if isinstance(sign, str):
        facts["sign"] = sign
    if system == "vedic":
        nakshatra = planet.get("nakshatra")
        if isinstance(nakshatra, dict):
            facts["nakshatra"] = {
                key: nakshatra[key]
                for key in ("name", "lord", "pada", "remaining_fraction")
                if nakshatra.get(key) is not None
            }
        d9 = planet.get("d9")
        if isinstance(d9, dict):
            facts["d9"] = {key: d9[key] for key in ("rashi", "rashi_index", "longitude") if d9.get(key) is not None}
    return facts


def build_chart_context(profile: dict[str, Any], calculation: dict[str, Any] | None, system: str) -> dict[str, Any]:
    """Return chart facts only; profile birth details and private snapshots are never copied."""
    profile_id = str(profile.get("id") or profile.get("profile_id") or "")
    if system not in {"vedic", "western"}:
        return {"available": False, "system": system, "notice": "Unsupported astrology system; do not infer chart facts."}
    if (
        calculation is None
        or calculation.get("status") != "complete"
        or calculation.get("calculation_system", calculation.get("system")) != system
        or (calculation.get("profile_id") is not None and str(calculation.get("profile_id")) != profile_id)
        or not isinstance(calculation.get("result"), dict)
    ):
        return {
            "available": False,
            "system": system,
            "notice": "No completed saved chart is available for this profile and system. Do not infer or invent placements.",
        }

    result = calculation["result"]
    if result.get("calculation_system") != system or not isinstance(result.get("planets"), list) or not result["planets"]:
        return {
            "available": False,
            "system": system,
            "notice": "The saved chart does not contain verified planetary placements. Do not infer or invent placements.",
        }
    division = calculation.get("division") or result.get("division", "D1")
    planets = result.get("planets")
    houses = result.get("division_houses") if system == "vedic" and division == "D9" else result.get("houses")
    if system == "vedic" and division == "D9" and any(
        not isinstance(item, dict) or not _number(item.get("division_longitude")) or not isinstance(item.get("division_rashi"), str)
        for item in planets
    ):
        return {"available": False, "system": system, "notice": "The saved chart does not contain verified D9 placements. Do not infer placements."}
    context: dict[str, Any] = {
        "available": True,
        "chart_id": str(calculation.get("chart_id")) if calculation.get("chart_id") is not None else None,
        "profile_id": profile_id,
        "system": system,
        "division": division,
        "calculated_at": calculation.get("calculated_at") or result.get("calculated_at"),
        "engine_version": calculation.get("engine_version"),
        "ephemeris_version": calculation.get("ephemeris_version"),
        "planets": [_planet_facts(item, system, division) for item in planets if isinstance(item, dict)],
        "houses": [
            {key: item[key] for key in ("number", "cusp_longitude", "sign", "rashi") if item.get(key) is not None}
            for item in houses if isinstance(item, dict)
        ] if isinstance(houses, list) else [],
    }
    for angle in ("ascendant", "midheaven"):
        value = result.get(angle)
        if isinstance(value, dict):
            angle_facts = value
            if system == "vedic" and division == "D9" and angle == "ascendant":
                angle_facts = {**value, "longitude": value.get("division_longitude"), "rashi": value.get("division_rashi"), "house": value.get("division_house")}
            context[angle] = {key: angle_facts[key] for key in ("longitude", "sign", "rashi", "house", "nakshatra", "pada") if angle_facts.get(key) is not None}
    if system == "vedic":
        dasha = result.get("vimshottari_dasha")
        if isinstance(dasha, dict):
            context["vimshottari_dasha"] = {
                "year_convention": dasha.get("year_convention"),
                "starting_nakshatra": dasha.get("starting_nakshatra"),
                "starting_lord": dasha.get("starting_lord"),
                "birth_balance_days": dasha.get("birth_balance_days"),
                "mahadashas": dasha.get("mahadashas", []),
                "antardashas": dasha.get("antardashas", []),
            }
    else:
        aspects = result.get("aspects")
        context["aspects"] = [
            {key: item[key] for key in ("planet_a", "planet_b", "aspect", "orb", "motion") if item.get(key) is not None}
            for item in aspects if isinstance(item, dict)
        ] if isinstance(aspects, list) else []
    return context
