"""Explicit human-led lifecycle for versioned interpretation rules.

This module records review transitions; it never approves rules automatically.
The caller must supply the actual reviewer identity, timestamp and note.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.services.ai.contracts import (
    InterpretationRule,
    RuleReviewEvent,
    RuleReviewStatus,
    SupportedLanguage,
)
from app.services.ai.source_registry import (
    SourceRegistry,
    SourceRegistryError,
    validate_rule_source_link,
)


class RuleWorkflowError(ValueError):
    """A proposed rule status transition is invalid or lacks evidence."""


_ALLOWED = {
    RuleReviewStatus.RESEARCH_CANDIDATE: {
        RuleReviewStatus.SOURCE_VERIFIED,
        RuleReviewStatus.REJECTED,
    },
    RuleReviewStatus.SOURCE_VERIFIED: {
        RuleReviewStatus.EDITORIAL_REVIEW_PENDING,
        RuleReviewStatus.REJECTED,
    },
    RuleReviewStatus.EDITORIAL_REVIEW_PENDING: {
        RuleReviewStatus.TRANSLATION_REVIEW_PENDING,
        RuleReviewStatus.REJECTED,
    },
    RuleReviewStatus.TRANSLATION_REVIEW_PENDING: {
        RuleReviewStatus.EDITORIAL_REVIEW_PENDING,
        RuleReviewStatus.APPROVED,
        RuleReviewStatus.REJECTED,
    },
    RuleReviewStatus.APPROVED: {RuleReviewStatus.RETIRED},
    RuleReviewStatus.REJECTED: {RuleReviewStatus.RETIRED},
    RuleReviewStatus.RETIRED: set(),
}


def _identity(value: str | None) -> str:
    """Normalize reviewer identities for independent-review comparisons."""
    return " ".join((value or "").split()).casefold()


def validate_rule_lifecycle(rule: InterpretationRule) -> None:
    """Ensure persisted status and recorded transitions form a valid history."""
    status = RuleReviewStatus.RESEARCH_CANDIDATE
    previous_time: datetime | None = None
    for event in rule.review_events:
        if not event.reviewer.strip() or event.reviewer.strip().casefold() in {"test", "unknown", "system", "auto"}:
            raise RuleWorkflowError("Review events must identify a real reviewer")
        if not event.note.strip():
            raise RuleWorkflowError("Review events need a non-empty note")
        if event.status not in _ALLOWED[status]:
            raise RuleWorkflowError(f"Invalid review transition: {status.value} -> {event.status.value}")
        if previous_time and event.occurred_at < previous_time:
            raise RuleWorkflowError("Rule review event timestamps must be monotonic")
        status = event.status
        previous_time = event.occurred_at
    if status is not rule.review_status:
        raise RuleWorkflowError("Rule review status does not match its recorded review events")
    editorial_is_approved = rule.provenance.editorial_status == "approved"
    events_by_status = {event.status: event for event in rule.review_events}
    provenance = rule.provenance
    if RuleReviewStatus.SOURCE_VERIFIED in events_by_status:
        source_event = events_by_status[RuleReviewStatus.SOURCE_VERIFIED]
        if source_event.reviewer != provenance.source_verifier or source_event.occurred_at != provenance.source_verified_at:
            raise RuleWorkflowError("Source-verification provenance does not match its review event")
    if RuleReviewStatus.EDITORIAL_REVIEW_PENDING in events_by_status:
        if events_by_status[RuleReviewStatus.EDITORIAL_REVIEW_PENDING].reviewer != provenance.editorial_reviewer:
            raise RuleWorkflowError("Editorial reviewer does not match its review event")
    if RuleReviewStatus.TRANSLATION_REVIEW_PENDING in events_by_status:
        if events_by_status[RuleReviewStatus.TRANSLATION_REVIEW_PENDING].reviewer != provenance.translation_reviewer:
            raise RuleWorkflowError("Translation reviewer does not match its review event")
    if editorial_is_approved and rule.review_status not in {RuleReviewStatus.APPROVED, RuleReviewStatus.RETIRED}:
        raise RuleWorkflowError("Editorial approval and lifecycle status must agree")
    if rule.review_status is RuleReviewStatus.APPROVED and not editorial_is_approved:
        raise RuleWorkflowError("Editorial approval and lifecycle status must agree")
    if rule.review_status in {RuleReviewStatus.APPROVED, RuleReviewStatus.RETIRED} and editorial_is_approved:
        if not any(event.status is RuleReviewStatus.SOURCE_VERIFIED for event in rule.review_events):
            raise RuleWorkflowError("Approved rules need a recorded source-verification step")
        if not any(event.status is RuleReviewStatus.EDITORIAL_REVIEW_PENDING for event in rule.review_events):
            raise RuleWorkflowError("Approved rules need a recorded editorial-review step")
        if not any(event.status is RuleReviewStatus.TRANSLATION_REVIEW_PENDING for event in rule.review_events):
            raise RuleWorkflowError("Approved rules need a recorded translation-review step")
        event_by_status = events_by_status
        content_reviewers = {
            _identity(event_by_status[RuleReviewStatus.SOURCE_VERIFIED].reviewer),
            _identity(event_by_status[RuleReviewStatus.EDITORIAL_REVIEW_PENDING].reviewer),
            _identity(event_by_status[RuleReviewStatus.TRANSLATION_REVIEW_PENDING].reviewer),
        }
        if len(content_reviewers) != 3:
            raise RuleWorkflowError("Source, editorial, and translation reviewers must be distinct")
        approval_event = event_by_status[RuleReviewStatus.APPROVED]
        if _identity(approval_event.reviewer) in content_reviewers:
            raise RuleWorkflowError("Approval reviewer must be independent of source and content reviewers")
        if approval_event.occurred_at != provenance.reviewed_at:
            raise RuleWorkflowError("Approval timestamp does not match its review event")


def transition_rule(
    rule: InterpretationRule,
    target: RuleReviewStatus | str,
    *,
    reviewer: str,
    note: str,
    registry: SourceRegistry,
    occurred_at: datetime | None = None,
) -> InterpretationRule:
    """Return a reviewed copy after one explicit, evidence-checked transition."""
    target = RuleReviewStatus(target)
    validate_rule_lifecycle(rule)
    if target not in _ALLOWED[rule.review_status]:
        raise RuleWorkflowError(f"Invalid review transition: {rule.review_status.value} -> {target.value}")
    if not reviewer.strip() or reviewer.strip().casefold() in {"test", "unknown", "system", "auto"}:
        raise RuleWorkflowError("A real reviewer identity is required")
    if not note.strip():
        raise RuleWorkflowError("A review note is required")
    moment = occurred_at or datetime.now(timezone.utc)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise RuleWorkflowError("Review timestamps must include a timezone")
    if rule.review_events and moment < rule.review_events[-1].occurred_at:
        raise RuleWorkflowError("Review event timestamps must be monotonic")
    if target is RuleReviewStatus.SOURCE_VERIFIED:
        source = next((item for item in registry.sources if item.source_id == rule.provenance.source_id), None)
        if source is None:
            raise RuleWorkflowError("Source verification requires a registered source ID")
        if rule.provenance.edition_id != source.edition_id or rule.provenance.edition != source.edition:
            raise RuleWorkflowError("Source verification requires the exact registered edition")
        if rule.system is not source.system:
            raise RuleWorkflowError("Source tradition does not match the rule's astrology system")
        if rule.provenance.supporting_excerpt and not source.copyright.short_excerpt_reuse_allowed:
            raise RuleWorkflowError("The source registry does not permit storing an excerpt")
        try:
            validate_rule_source_link(rule, registry)
        except SourceRegistryError as exc:
            raise RuleWorkflowError(f"Source verification failed: {exc}") from exc
        if not any((rule.provenance.chapter, rule.provenance.verse, rule.provenance.page, rule.provenance.section)):
            raise RuleWorkflowError("Source verification requires an exact passage locator")
        rule = rule.model_copy(update={
            "provenance": rule.provenance.model_copy(update={
                "source_verifier": reviewer.strip(),
                "source_verified_at": moment,
            })
        })
    if target is RuleReviewStatus.EDITORIAL_REVIEW_PENDING:
        if not rule.provenance.editorial_explanation:
            raise RuleWorkflowError("Editorial review requires an editorial explanation")
        rule = rule.model_copy(update={
            "provenance": rule.provenance.model_copy(update={"editorial_reviewer": reviewer.strip()})
        })
    if target is RuleReviewStatus.TRANSLATION_REVIEW_PENDING:
        if set(rule.translations) != {SupportedLanguage.EN, SupportedLanguage.TA}:
            raise RuleWorkflowError("Translation review requires English and Tamil text")
        if any(not text.strip() for text in rule.translations.values()):
            raise RuleWorkflowError("Translation review requires non-empty English and Tamil text")
        rule = rule.model_copy(update={
            "provenance": rule.provenance.model_copy(update={"translation_reviewer": reviewer.strip()})
        })
    if target is RuleReviewStatus.APPROVED:
        if not rule.provenance.editorial_reviewer or not rule.provenance.translation_reviewer:
            raise RuleWorkflowError("Approval requires separate editorial and translation reviewers")
        if _identity(rule.provenance.editorial_reviewer) == _identity(rule.provenance.translation_reviewer):
            raise RuleWorkflowError("Editorial and translation reviews must be recorded separately")
        prior_reviewers = {
            _identity(rule.provenance.editorial_reviewer),
            _identity(rule.provenance.translation_reviewer),
            _identity(rule.provenance.source_verifier),
        }
        if _identity(reviewer) in prior_reviewers:
            raise RuleWorkflowError("Approval must be recorded by a reviewer separate from the source and content reviewers")
        if set(rule.translations) != {SupportedLanguage.EN, SupportedLanguage.TA}:
            raise RuleWorkflowError("Approval requires reviewed English and Tamil text")
        if rule.provenance.source_verifier in {None, "", "test", "unknown", "system", "auto"}:
            raise RuleWorkflowError("Approval requires a recorded source verifier")
        if rule.provenance.source_verified_at is None:
            raise RuleWorkflowError("Approval requires a recorded source verification timestamp")
        try:
            validate_rule_source_link(rule, registry)
        except SourceRegistryError as exc:
            raise RuleWorkflowError(f"Approval provenance is invalid: {exc}") from exc
        rule = rule.model_copy(update={
            "provenance": rule.provenance.model_copy(update={
                "editorial_status": "approved",
                "translation_review_status": "reviewed",
                "reviewed_at": moment,
            })
        })
    event = RuleReviewEvent(status=target, reviewer=reviewer.strip(), occurred_at=moment, note=note.strip())
    updated = rule.model_copy(update={
        "review_status": target,
        "review_events": (*rule.review_events, event),
    })
    validate_rule_lifecycle(updated)
    return updated
