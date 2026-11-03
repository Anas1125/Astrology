from datetime import datetime, timezone

import pytest

from app.services.ai.contracts import (
    MentionedEntity,
    RuleReviewStatus,
    SupportedLanguage,
)
from app.services.ai.knowledge_workflow import RuleWorkflowError, transition_rule, validate_rule_lifecycle
from app.services.ai.rule_matcher import match_interpretation_rules
from app.services.ai.source_registry import get_default_source_registry
from test_ai_sources import _approved_rule
from test_ai_rule_matcher import _chart, _fact, _question


def _candidate():
    approved = _approved_rule()
    source = next(item for item in get_default_source_registry().sources if item.source_id == approved.provenance.source_id)
    provenance = approved.provenance.model_copy(update={
        "edition": source.edition,
        "editorial_status": "draft",
        "editorial_reviewer": None,
        "translation_reviewer": None,
        "reviewed_at": None,
        "translation_review_status": "unreviewed",
        "source_verifier": None,
        "source_verified_at": None,
    })
    return approved.model_copy(update={
        "provenance": provenance,
        "review_status": RuleReviewStatus.RESEARCH_CANDIDATE,
        "review_events": (),
    })


def test_human_review_workflow_requires_ordered_distinct_reviews_and_evidence():
    registry = get_default_source_registry()
    rule = _candidate()
    at = datetime(2026, 11, 3, tzinfo=timezone.utc)

    source_verified = transition_rule(
        rule, RuleReviewStatus.SOURCE_VERIFIED, reviewer="Source Reviewer A",
        note="Compared locator against registered edition.", registry=registry, occurred_at=at,
    )
    editorial = transition_rule(
        source_verified, RuleReviewStatus.EDITORIAL_REVIEW_PENDING,
        reviewer="Editor B", note="Editorial review completed.", registry=registry, occurred_at=at,
    )
    translated = transition_rule(
        editorial, RuleReviewStatus.TRANSLATION_REVIEW_PENDING,
        reviewer="Tamil Reviewer C", note="Tamil/English meaning checked.", registry=registry, occurred_at=at,
    )
    approved = transition_rule(
        translated, RuleReviewStatus.APPROVED, reviewer="Approver D",
        note="Approved after source and language review.", registry=registry, occurred_at=at,
    )

    assert approved.review_status is RuleReviewStatus.APPROVED
    assert approved.provenance.editorial_status == "approved"
    assert [event.status for event in approved.review_events] == [
        RuleReviewStatus.SOURCE_VERIFIED,
        RuleReviewStatus.EDITORIAL_REVIEW_PENDING,
        RuleReviewStatus.TRANSLATION_REVIEW_PENDING,
        RuleReviewStatus.APPROVED,
    ]
    validate_rule_lifecycle(approved)

    retired = transition_rule(
        approved, RuleReviewStatus.RETIRED, reviewer="Knowledge Maintainer E",
        note="Retired after review cycle.", registry=registry, occurred_at=at,
    )
    validate_rule_lifecycle(retired)
    assert retired.review_status is RuleReviewStatus.RETIRED


@pytest.mark.parametrize("target", [RuleReviewStatus.APPROVED, RuleReviewStatus.TRANSLATION_REVIEW_PENDING])
def test_cannot_skip_required_review_steps(target):
    with pytest.raises(RuleWorkflowError, match="Invalid review transition"):
        transition_rule(
            _candidate(), target, reviewer="Reviewer A", note="Not enough review.",
            registry=get_default_source_registry(),
        )


def test_cannot_approve_without_source_and_language_reviews():
    registry = get_default_source_registry()
    at = datetime(2026, 11, 3, tzinfo=timezone.utc)
    candidate = _candidate()
    source = transition_rule(candidate, "source_verified", reviewer="Source Reviewer A", note="Verified.", registry=registry, occurred_at=at)
    editorial = transition_rule(source, "editorial_review_pending", reviewer="Editor B", note="Reviewed.", registry=registry, occurred_at=at)
    with pytest.raises(RuleWorkflowError, match="Invalid review transition"):
        transition_rule(editorial, "approved", reviewer="Approver D", note="Approve.", registry=registry, occurred_at=at)


def test_reviewer_independence_is_case_and_whitespace_insensitive():
    registry = get_default_source_registry()
    at = datetime(2026, 11, 3, tzinfo=timezone.utc)
    source = transition_rule(
        _candidate(), "source_verified", reviewer="Source Reviewer A", note="Verified.",
        registry=registry, occurred_at=at,
    )
    editorial = transition_rule(
        source, "editorial_review_pending", reviewer="Editor B", note="Reviewed.",
        registry=registry, occurred_at=at,
    )
    translation = transition_rule(
        editorial, "translation_review_pending", reviewer="Tamil Reviewer C", note="Checked.",
        registry=registry, occurred_at=at,
    )
    with pytest.raises(RuleWorkflowError, match="separate from the source and content reviewers"):
        transition_rule(
            translation, "approved", reviewer=" source  reviewer a ", note="Approve.",
            registry=registry, occurred_at=at,
        )


def test_workflow_rejects_fake_reviewer_and_incorrect_source_edition():
    with pytest.raises(RuleWorkflowError, match="real reviewer"):
        transition_rule(_candidate(), "source_verified", reviewer="system", note="Verified", registry=get_default_source_registry())
    candidate = _candidate().model_copy(update={
        "provenance": _candidate().provenance.model_copy(update={"edition_id": "wrong-edition"})
    })
    with pytest.raises(RuleWorkflowError, match="exact registered edition"):
        transition_rule(candidate, "source_verified", reviewer="Source Reviewer", note="Checked", registry=get_default_source_registry())


def test_research_candidate_never_matches_in_production_even_with_matching_facts():
    rule = _candidate()
    chart = _chart([_fact("Moon", "sign", "Taurus", system="western", division="W")], system="western", division="W")
    question = _question(system="western", division="natal", topic="planet",
                         entities=(MentionedEntity(kind="planet", name="Moon"),))
    result = match_interpretation_rules(question, chart, (rule,), language=SupportedLanguage.EN, allow_test_only=False)
    assert result.matches == ()
    assert any(skip.reason == "editorial_status_draft" for skip in result.skipped)


def test_review_history_does_not_allow_editing_final_approved_state_without_event():
    approved = _candidate().model_copy(update={
        "review_status": RuleReviewStatus.APPROVED,
        "provenance": _candidate().provenance.model_copy(update={"editorial_status": "approved"}),
    })
    with pytest.raises(RuleWorkflowError):
        validate_rule_lifecycle(approved)
