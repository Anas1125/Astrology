"""Adapt the privacy-filtered saved-chart context into validated typed facts."""
from __future__ import annotations

from datetime import datetime
import math
from typing import Any

from app.services.ai.contracts import AstrologySystem, ChartFact, ChartFacts


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _valid_longitude(value: Any) -> bool:
    return _finite_number(value) and 0 <= float(value) <= 360


def _valid_house(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 12


def _valid_pada(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 4


def _valid_text(value: Any) -> bool:
    return isinstance(value, str)


def _clean_scalar(value: Any) -> str | int | float | bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _valid_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return parsed


def chart_facts_from_context(
    context: dict[str, Any],
    *,
    expected_system: AstrologySystem | str | None = None,
    expected_division: str | None = None,
) -> ChartFacts:
    """Convert only persisted calculated values; invalid values are omitted and noted."""
    raw_system = context.get("system")
    try:
        system = AstrologySystem(raw_system)
    except (ValueError, TypeError):
        system = None
    chart_id = str(context["chart_id"]) if context.get("chart_id") is not None else None
    profile_id = str(context["profile_id"]) if context.get("profile_id") is not None else None
    division_value = context.get("division")
    division = str(division_value) if division_value is not None else None
    missing: list[str] = []

    def unavailable(reason: str, found_system: AstrologySystem | None = system) -> ChartFacts:
        return ChartFacts(
            chart_id=chart_id,
            profile_id=profile_id,
            system=found_system,
            division=division,
            available=False,
            missing=tuple(dict.fromkeys([*missing, reason])),
            calculation_engine_version=_clean_scalar(context.get("engine_version")) if isinstance(context.get("engine_version"), str) else None,
            ephemeris_version=_clean_scalar(context.get("ephemeris_version")) if isinstance(context.get("ephemeris_version"), str) else None,
            calculated_at=_valid_datetime(context.get("calculated_at")),
        )

    if system is None:
        return unavailable("unsupported_or_missing_system")
    if expected_system is not None and system != AstrologySystem(expected_system):
        return unavailable("wrong_astrology_system", system)
    if context.get("available") is not True:
        return unavailable("saved_chart_unavailable", system)
    if not chart_id or not profile_id:
        return unavailable("saved_chart_identity_missing", system)
    if not isinstance(division, str) or not division:
        return unavailable("chart_division_missing", system)
    if system is AstrologySystem.VEDIC and division not in {"D1", "D9"}:
        return unavailable("unsupported_vedic_division", system)
    if system is AstrologySystem.WESTERN and division not in {"W", "natal", "NATAL"}:
        return unavailable("unsupported_western_division", system)
    if expected_division is not None and division.casefold() != expected_division.casefold():
        return unavailable("wrong_chart_division", system)
    planets = context.get("planets")
    if not isinstance(planets, list) or not planets:
        return unavailable("planetary_placements_missing", system)

    facts: list[ChartFact] = []

    def add(subject: str, predicate: str, value: Any, source: str, *, validator=None) -> None:
        clean = _clean_scalar(value)
        if clean is None or (validator is not None and not validator(clean)):
            missing.append(f"{subject}.{predicate}")
            return
        facts.append(ChartFact(
            subject=subject,
            predicate=predicate,
            value=clean,
            system=system,
            division=division,
            source_chart_id=chart_id,
            profile_id=profile_id,
            provenance=f"saved_chart:{chart_id}:{source}",
        ))

    valid_planets = 0
    for index, planet in enumerate(planets):
        if not isinstance(planet, dict):
            missing.append(f"planet[{index}]")
            continue
        name = _clean_scalar(planet.get("name"))
        if not isinstance(name, str):
            missing.append(f"planet[{index}].name")
            continue
        valid_planets += 1
        prefix = f"planets[{index}]"
        if "longitude" in planet:
            add(name, "longitude", planet["longitude"], f"{prefix}.longitude", validator=_valid_longitude)
        else:
            missing.append(f"{name}.longitude")
        if "sign" in planet:
            add(name, "sign", planet["sign"], f"{prefix}.sign", validator=lambda value: isinstance(value, str))
        if "house" in planet:
            add(name, "house", planet["house"], f"{prefix}.house", validator=lambda value: isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 12)
        if "retrograde" in planet:
            add(name, "retrograde", planet["retrograde"], f"{prefix}.retrograde", validator=lambda value: isinstance(value, bool))
        else:
            missing.append(f"{name}.retrograde")
        if system is AstrologySystem.VEDIC and division == "D1":
            nakshatra = planet.get("nakshatra")
            if isinstance(nakshatra, dict):
                for key in ("name", "lord"):
                    if key in nakshatra:
                        add(name, f"nakshatra.{key}", nakshatra[key], f"{prefix}.nakshatra.{key}", validator=lambda value: isinstance(value, str))
                if "pada" in nakshatra:
                    add(name, "nakshatra.pada", nakshatra["pada"], f"{prefix}.nakshatra.pada", validator=lambda value: isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 4)
                if "remaining_fraction" in nakshatra:
                    add(name, "nakshatra.remaining_fraction", nakshatra["remaining_fraction"], f"{prefix}.nakshatra.remaining_fraction", validator=lambda value: _finite_number(value) and 0 <= value <= 1)
            else:
                missing.append(f"{name}.nakshatra")
        if system is AstrologySystem.VEDIC and division == "D9":
            d9 = planet.get("d9")
            if isinstance(d9, dict):
                for key in ("rashi", "rashi_index", "longitude"):
                    if key in d9:
                        validator = _valid_longitude if key == "longitude" else None
                        add(name, f"d9.{key}", d9[key], f"{prefix}.d9.{key}", validator=validator)
            else:
                missing.append(f"{name}.d9")

    if valid_planets == 0:
        return unavailable("no_valid_planetary_placements", system)

    for angle in ("ascendant", "midheaven"):
        value = context.get(angle)
        if isinstance(value, dict):
            for key in ("longitude", "sign", "rashi", "house", "nakshatra", "pada"):
                if key not in value:
                    continue
                validator = _valid_longitude if key == "longitude" else None
                if key == "house":
                    validator = _valid_house
                if key == "pada":
                    validator = _valid_pada
                if key in {"sign", "rashi", "nakshatra"}:
                    validator = _valid_text
                add(angle, key, value[key], f"{angle}.{key}", validator=validator)
        else:
            missing.append(angle)

    houses = context.get("houses")
    if isinstance(houses, list):
        for index, house in enumerate(houses):
            if not isinstance(house, dict):
                missing.append(f"house[{index}]")
                continue
            number = house.get("number")
            if not isinstance(number, int) or isinstance(number, bool) or not 1 <= number <= 12:
                missing.append(f"house[{index}].number")
                continue
            subject = f"House:{number}"
            for key in ("cusp_longitude", "sign", "rashi"):
                if key in house:
                    add(subject, key, house[key], f"houses[{index}].{key}", validator=_valid_longitude if key == "cusp_longitude" else lambda item: isinstance(item, str))
    else:
        missing.append("houses")

    if system is AstrologySystem.VEDIC:
        dasha = context.get("vimshottari_dasha")
        if isinstance(dasha, dict):
            for key in ("year_convention", "starting_nakshatra", "starting_lord"):
                if key in dasha:
                    add("Vimshottari", key, dasha[key], f"vimshottari_dasha.{key}", validator=lambda item: isinstance(item, str))
            if "birth_balance_days" in dasha:
                add("Vimshottari", "birth_balance_days", dasha["birth_balance_days"], "vimshottari_dasha.birth_balance_days", validator=lambda item: _finite_number(item) and item >= 0)
            for period_key in ("mahadashas", "antardashas"):
                periods = dasha.get(period_key)
                if not isinstance(periods, list):
                    continue
                for period_index, period in enumerate(periods):
                    if not isinstance(period, dict):
                        missing.append(f"{period_key}[{period_index}]")
                        continue
                    lord = _clean_scalar(period.get("lord"))
                    sub_lord = _clean_scalar(period.get("sub_lord"))

                    valid_lords = {
                        "Ketu", "Venus", "Sun", "Moon", "Mars",
                        "Rahu", "Jupiter", "Saturn", "Mercury",
                    }

                    if not isinstance(lord, str) or lord not in valid_lords:
                        missing.append(f"{period_key}[{period_index}].lord")
                        continue

                    if period_key == "antardashas":
                        if not isinstance(sub_lord, str) or sub_lord not in valid_lords:
                            missing.append(f"{period_key}[{period_index}].sub_lord")
                            continue

                        subject = f"Antardasha:{lord}/{sub_lord}"
                    else:
                        subject = f"Dasha:{lord}"

                    for key in ("lord", "sub_lord", "start", "end", "nominal_start", "nominal_end"):
                        if key in period:
                            add(
                                subject,
                                key,
                                period[key],
                                f"vimshottari_dasha.{period_key}[{period_index}].{key}",
                                validator=lambda item: isinstance(item, str),
                            )
        else:
            missing.append("vimshottari_dasha")

    if system is AstrologySystem.WESTERN:
        aspects = context.get("aspects")
        if isinstance(aspects, list):
            for index, aspect in enumerate(aspects):
                if not isinstance(aspect, dict):
                    missing.append(f"aspect[{index}]")
                    continue
                first, second = aspect.get("planet_a"), aspect.get("planet_b")
                if not isinstance(first, str) or not isinstance(second, str):
                    missing.append(f"aspect[{index}].planets")
                    continue
                subject = f"Aspect:{first}/{second}"
                for key in ("aspect", "orb", "motion"):
                    if key not in aspect:
                        continue
                    validator = (lambda item: isinstance(item, str)) if key in {"aspect", "motion"} else (lambda item: _finite_number(item) and item >= 0)
                    add(subject, key, aspect[key], f"aspects[{index}].{key}", validator=validator)
        else:
            missing.append("aspects")

    engine_version = context.get("engine_version")
    if engine_version is not None and not isinstance(engine_version, str):
        engine_version = None
    return ChartFacts(
        chart_id=chart_id,
        profile_id=profile_id,
        system=system,
        division=division,
        available=True,
        facts=tuple(facts),
        missing=tuple(dict.fromkeys(missing)),
        calculation_engine_version=engine_version,
        ephemeris_version=context.get("ephemeris_version") if isinstance(context.get("ephemeris_version"), str) else None,
        calculated_at=_valid_datetime(context.get("calculated_at")),
    )
