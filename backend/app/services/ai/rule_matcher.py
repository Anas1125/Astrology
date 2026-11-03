"""Deterministic, provenance-preserving matcher for reviewed interpretation rules."""
from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from app.services.ai.contracts import (
    AstrologySystem,
    ChartFact,
    ChartFacts,
    InterpretationRule,
    MatchedFactReference,
    MatchedInterpretationRule,
    QuestionClassification,
    RuleConflict,
    RuleMatchResult,
    RuleSkip,
    SupportedLanguage,
    UserIntent,
)

_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Rahu", "Ketu"}
_LORDS = {"Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"}
_PLANET_FIELDS = {
    "longitude", "sign", "house", "retrograde", "nakshatra.name", "nakshatra.lord",
    "nakshatra.pada", "nakshatra.remaining_fraction", "d9.rashi", "d9.rashi_index", "d9.longitude",
}
_ANGLE_FIELDS = {"longitude", "sign", "rashi", "house", "nakshatra", "pada"}
_HOUSE_FIELDS = {"cusp_longitude", "sign", "rashi"}
_DASHA_FIELDS = {"year_convention", "starting_nakshatra", "starting_lord", "birth_balance_days"}
_PERIOD_FIELDS = {"lord", "sub_lord", "start", "end", "nominal_start", "nominal_end"}
_ASPECT_FIELDS = {"aspect", "orb", "motion"}
_PLACEHOLDERS = {"n/a", "na", "none", "unknown", "unsourced", "test", "test only"}


class DuplicateRuleID(ValueError):
    """The supplied rule set contains duplicate identifiers."""


def _subject_and_predicate(field: str) -> tuple[str, str] | None:
    subject, separator, predicate = field.partition(".")
    if not separator or not subject or not predicate:
        return None
    return subject, predicate


def supported_condition_field(field: str) -> bool:
    """Return whether a condition addresses a fact produced by chart_facts.py."""
    parsed = _subject_and_predicate(field)
    if parsed is None:
        return False
    subject, predicate = parsed
    if subject in _PLANETS:
        return predicate in _PLANET_FIELDS
    if subject.casefold() in {"ascendant", "midheaven"}:
        return predicate in _ANGLE_FIELDS
    if re.fullmatch(r"House:(?:[1-9]|1[0-2])", subject):
        return predicate in _HOUSE_FIELDS
    if subject == "Vimshottari":
        return predicate in _DASHA_FIELDS
    if re.fullmatch(rf"Dasha:(?:{'|'.join(sorted(_LORDS))})", subject):
        return predicate in _PERIOD_FIELDS
    if re.fullmatch(rf"Antardasha:(?:{'|'.join(sorted(_LORDS))})/(?:{'|'.join(sorted(_LORDS))})", subject):
        return predicate in _PERIOD_FIELDS
    if re.fullmatch(rf"Aspect:(?:{'|'.join(sorted(_PLANETS))})/(?:{'|'.join(sorted(_PLANETS))})", subject):
        return predicate in _ASPECT_FIELDS
    return False


def _valid_condition_value(field: str, value: Any) -> bool:
    parsed = _subject_and_predicate(field)
    if parsed is None:
        return False
    _, predicate = parsed
    if predicate in {"retrograde"}:
        return isinstance(value, bool)
    if predicate == "house" or predicate == "pada" or predicate.endswith(".pada"):
        maximum = 4 if predicate == "pada" or predicate.endswith(".pada") else 12
        return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= maximum
    if predicate == "d9.rashi_index":
        return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 11
    if predicate in {"longitude", "cusp_longitude", "orb", "nakshatra.remaining_fraction", "birth_balance_days", "d9.longitude"}:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            return False
        if predicate in {"longitude", "cusp_longitude", "d9.longitude"}:
            return 0 <= float(value) <= 360
        if predicate == "nakshatra.remaining_fraction":
            return 0 <= float(value) <= 1
        return value >= 0
    return isinstance(value, str) and bool(value.strip())


def validate_rule_conditions(rule: InterpretationRule) -> None:
    """Reject schema-valid but unsupported or ill-typed fact conditions."""
    for condition in rule.conditions:
        if not supported_condition_field(condition.field):
            raise ValueError(f"Rule {rule.rule_id} uses unsupported condition field {condition.field!r}")
        if not _valid_condition_value(condition.field, condition.equals):
            raise ValueError(f"Rule {rule.rule_id} has an invalid value for condition {condition.field!r}")
        subject, predicate = _subject_and_predicate(condition.field) or ("", "")
        is_vedic_only = predicate.startswith(("nakshatra.", "d9.")) or subject in {"Vimshottari"} or subject.startswith(("Dasha:", "Antardasha:"))
        is_western_only = subject.startswith("Aspect:")
        if rule.system is AstrologySystem.WESTERN and is_vedic_only:
            raise ValueError(f"Rule {rule.rule_id} uses a Vedic-only fact in a Western rule")
        if rule.system is AstrologySystem.VEDIC and is_western_only:
            raise ValueError(f"Rule {rule.rule_id} uses a Western-only fact in a Vedic rule")
        if rule.system is AstrologySystem.VEDIC and predicate.startswith("d9.") and rule.division not in {"D9", None}:
            raise ValueError(f"Rule {rule.rule_id} uses a D9 fact outside D9")
        if rule.system is AstrologySystem.VEDIC and predicate.startswith("nakshatra.") and rule.division == "D9":
            raise ValueError(f"Rule {rule.rule_id} uses a D1 Nakshatra fact in a D9 rule")


def _adequate_provenance(rule: InterpretationRule) -> bool:
    provenance = rule.provenance
    values = (provenance.source_name.strip(), provenance.attribution.strip(), provenance.reference.strip())
    return (
        all(value and value.casefold() not in _PLACEHOLDERS for value in values)
        and len(values[0]) >= 3 and len(values[1]) >= 3 and len(values[2]) >= 12
    )


def _rule_question_relevant(rule: InterpretationRule, classification: QuestionClassification) -> bool:
    if not rule.topics or classification.topic not in rule.topics:
        return False
    conditions = rule.conditions
    for entity in rule.required_entities:
        if entity not in classification.entities:
            return False
    # Recognized user mentions constrain the fact subjects and values used by a match.
    for entity in classification.entities:
        name = entity.name.casefold()
        related = False
        for condition in conditions:
            parsed = _subject_and_predicate(condition.field)
            if parsed is None:
                continue
            subject, predicate = parsed
            subject_folded = subject.casefold()
            value = str(condition.equals).casefold()
            if entity.kind == "division":
                related = rule.division is None or rule.division.casefold() == name
            elif entity.kind == "planet":
                related = (
                    subject_folded == name
                    or subject_folded == f"dasha:{name}"
                    or subject_folded.startswith(f"antardasha:{name}/")
                    or subject_folded == "vimshottari" and predicate == "starting_lord" and value == name
                    or (subject_folded.startswith("aspect:") and name in subject_folded.removeprefix("aspect:").split("/"))
                )
            elif entity.kind == "sign":
                related = predicate in {"sign", "rashi", "d9.rashi"} and value == name
            elif entity.kind == "house":
                related = subject_folded == f"house:{name}" or (predicate == "house" and value == name)
            elif entity.kind == "nakshatra":
                related = predicate == "nakshatra.name" and value == name
            elif entity.kind == "dasha_lord":
                related = (
                    subject_folded == f"dasha:{name}"
                    or subject_folded.startswith(f"antardasha:{name}/")
                    or subject_folded == "vimshottari" and predicate == "starting_lord" and value == name
                    or subject_folded.startswith("antardasha:") and predicate == "sub_lord" and value == name
                )
            elif entity.kind == "aspect":
                related = predicate == "aspect" and value == name
            if related:
                break
        if not related:
            return False
    return True


def _chart_rejection(classification: QuestionClassification, chart: ChartFacts | None) -> str | None:
    if classification.intent is not UserIntent.CHART_QUESTION:
        return f"question_intent_{classification.intent.value}"
    if classification.needs_clarification or classification.system is None:
        return "question_system_or_scope_ambiguous"
    if chart is None or not chart.available:
        return "saved_chart_unavailable"
    if chart.system is None or chart.system is not classification.system:
        return "chart_system_mismatch"
    if not chart.chart_id or not chart.profile_id:
        return "chart_identity_missing"
    if classification.division is not None and not _same_division(chart.system, chart.division, classification.division):
        return "chart_division_mismatch"
    return None


def _same_division(system: AstrologySystem, actual: str | None, requested: str | None) -> bool:
    if actual is None or requested is None:
        return actual == requested
    if system is AstrologySystem.WESTERN and {actual.casefold(), requested.casefold()} <= {"w", "natal"}:
        return True
    return actual.casefold() == requested.casefold()


def _validate_chart_facts(chart: ChartFacts) -> str | None:
    seen: dict[tuple[str, str], ChartFact] = {}
    for fact in chart.facts:
        if fact.source_chart_id != chart.chart_id:
            return "fact_chart_provenance_mismatch"
        if fact.profile_id != chart.profile_id:
            return "fact_profile_provenance_mismatch"
        if not fact.provenance.startswith(f"saved_chart:{chart.chart_id}:"):
            return "fact_source_provenance_invalid"
        if fact.system is not chart.system:
            return "fact_system_mismatch"
        if fact.division != chart.division:
            return "fact_division_mismatch"
        field = f"{fact.subject}.{fact.predicate}"
        if not supported_condition_field(field) or not _valid_condition_value(field, fact.value):
            return "unsupported_or_invalid_chart_fact"
        key = (fact.subject, fact.predicate)
        if key in seen:
            return "duplicate_or_conflicting_chart_facts"
        seen[key] = fact
    return None


def _fact_reference(fact: ChartFact, chart: ChartFacts) -> MatchedFactReference:
    # The chart identity is checked before any rule is considered.
    assert chart.chart_id is not None and chart.profile_id is not None and chart.system is not None
    return MatchedFactReference(
        fact_id=f"fact:{chart.chart_id}:{fact.subject}.{fact.predicate}",
        subject=fact.subject,
        predicate=fact.predicate,
        value=fact.value,
        source_chart_id=fact.source_chart_id,
        profile_id=chart.profile_id,
        system=chart.system,
        division=fact.division,
        provenance=fact.provenance,
    )


def match_interpretation_rules(
    classification: QuestionClassification,
    chart: ChartFacts | None,
    rules: Iterable[InterpretationRule],
    *,
    language: SupportedLanguage,
    allow_test_only: bool = False,
) -> RuleMatchResult:
    """Apply exact rule conditions deterministically and retain complete provenance.

    Production calls must leave ``allow_test_only`` false. The opt-in exists only
    so schema fixtures can exercise the matcher without pretending editorial review.
    """
    language = SupportedLanguage(language)
    ordered_rules = sorted(tuple(rules), key=lambda item: item.rule_id)
    identifiers = [rule.rule_id for rule in ordered_rules]
    if len(set(identifiers)) != len(identifiers):
        duplicate = next(rule_id for rule_id in identifiers if identifiers.count(rule_id) > 1)
        raise DuplicateRuleID(f"Duplicate rule ID in matcher input: {duplicate}")

    rejection = _chart_rejection(classification, chart)
    if rejection:
        return RuleMatchResult(
            chart_id=chart.chart_id if chart else None,
            profile_id=chart.profile_id if chart else None,
            eligible=False,
            rejection_reason=rejection,
        )
    assert chart is not None and chart.chart_id is not None and chart.profile_id is not None and chart.system is not None
    fact_rejection = _validate_chart_facts(chart)
    if fact_rejection:
        return RuleMatchResult(
            chart_id=chart.chart_id, profile_id=chart.profile_id, eligible=False,
            rejection_reason=fact_rejection,
        )

    facts_by_field = {f"{fact.subject}.{fact.predicate}": fact for fact in chart.facts}
    matches: list[MatchedInterpretationRule] = []
    skipped: list[RuleSkip] = []
    for rule in ordered_rules:
        if rule.system is not classification.system or rule.system is not chart.system:
            skipped.append(RuleSkip(rule_id=rule.rule_id, reason="astrology_system_mismatch"))
            continue
        if rule.language is not language:
            skipped.append(RuleSkip(rule_id=rule.rule_id, reason="language_mismatch"))
            continue
        if rule.division is not None and not _same_division(chart.system, chart.division, rule.division):
            skipped.append(RuleSkip(rule_id=rule.rule_id, reason="chart_division_mismatch"))
            continue
        if not _rule_question_relevant(rule, classification):
            skipped.append(RuleSkip(rule_id=rule.rule_id, reason="question_scope_mismatch"))
            continue
        if rule.provenance.editorial_status == "test_only" and allow_test_only:
            pass
        elif rule.provenance.editorial_status != "approved":
            skipped.append(RuleSkip(rule_id=rule.rule_id, reason=f"editorial_status_{rule.provenance.editorial_status}"))
            continue
        if not _adequate_provenance(rule):
            skipped.append(RuleSkip(rule_id=rule.rule_id, reason="inadequate_rule_provenance"))
            continue
        try:
            validate_rule_conditions(rule)
        except ValueError:
            skipped.append(RuleSkip(rule_id=rule.rule_id, reason="unsupported_or_invalid_condition"))
            continue
        required_facts: list[ChartFact] = []
        for condition in rule.conditions:
            fact = facts_by_field.get(condition.field)
            if fact is None or fact.value != condition.equals:
                break
            required_facts.append(fact)
        else:
            references = tuple(
                _fact_reference(fact, chart)
                for fact in sorted(required_facts, key=lambda item: (item.subject, item.predicate, item.provenance))
            )
            matches.append(MatchedInterpretationRule(
                rule_id=rule.rule_id,
                rule_version=rule.rule_version,
                knowledge_base_version=rule.knowledge_base_version,
                system=rule.system,
                division=rule.division or chart.division,
                language=rule.language,
                text=rule.text,
                confidence=rule.confidence,
                provenance=rule.provenance,
                chart_id=chart.chart_id,
                profile_id=chart.profile_id,
                fact_references=references,
            ))
        if len(required_facts) != len(rule.conditions):
            skipped.append(RuleSkip(rule_id=rule.rule_id, reason="required_fact_missing_or_condition_not_satisfied"))

    groups: dict[str, list[str]] = defaultdict(list)
    for rule, match in ((rule, next((item for item in matches if item.rule_id == rule.rule_id), None)) for rule in ordered_rules):
        if rule.conflict_group and match is not None:
            groups[rule.conflict_group].append(rule.rule_id)
    conflicts = tuple(
        RuleConflict(conflict_group=group, rule_ids=tuple(sorted(rule_ids)))
        for group, rule_ids in sorted(groups.items()) if len(rule_ids) > 1
    )
    return RuleMatchResult(
        chart_id=chart.chart_id,
        profile_id=chart.profile_id,
        eligible=True,
        matches=tuple(matches),
        conflicts=conflicts,
        skipped=tuple(skipped),
    )
