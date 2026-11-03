# Astrology knowledge research and review workflow

The versioned source registry and topic catalogue are research infrastructure. They are not themselves astrology rules, and a source's presence does not authorize quotation, adaptation, or commercial use.

## Passage-to-rule process

1. **Identify the passage.** Select a named source record and exact edition. Confirm whether the page is the primary text, a translator's rendering, commentary, an editor's note, or a later adaptation.
2. **Verify the source and edition.** Check title page, publication data, translator/editor, volume, and completeness. For variant texts such as BPHS, record the exact edition/recension and its numbering. If a fact is uncertain, leave it unresolved and do not draft a production rule from it.
3. **Record an exact locator.** Capture book/adhyāya/chapter, verse/śloka, printed page, and section where available. Do not infer references from an aggregator or OCR index. Compare the scan or physical text directly.
4. **Write independent English interpretation.** Summarize the passage in original wording, retain the source's conditions, exceptions, and context, and label it as a traditional interpretation rather than a calculated fact or scientific claim. Do not paraphrase commentary as if it were the classical verse.
5. **Produce Tamil.** Create an independently reviewed Tamil rendering of the authored interpretation. Store both languages together; do not auto-translate copyrighted source passages or fill missing text.
6. **Check semantic consistency.** A bilingual reviewer compares both independently authored versions against the same source passage, checks technical terminology, and records reviewer and date.
7. **Review context and exceptions.** Confirm that fact conditions represent the source's actual prerequisites, that conflicting passages are recorded, and that no prediction, guarantee, personal detail, or health/legal/financial advice is added.
8. **Track explicit lifecycle states.** Rules move through `research_candidate` → `source_verified` → `editorial_review_pending` → `translation_review_pending` → `approved`. A reviewer can reject a candidate or a reviewed rule; approved or rejected content can later be retired. Each transition must include a real reviewer, timezone-aware timestamp, and note. Code does not generate approval events.
9. **Approve only after independent review.** Approval additionally requires exact registered edition linkage, source verifier metadata, a source locator, an editorial explanation, English and Tamil text, distinct editorial/translation reviewers, and a recorded approval event. Source verification is not scientific validation. Legal clearance remains a separate gate.

## Rule and source data

The source registry is `backend/app/services/ai/knowledge/sources/registry.v1.json`, validated by `source_registry.py`. The current research catalogue is `backend/app/services/ai/knowledge/research/catalogue.v2.json`, validated by `research_catalogue.py`; v1 is retained as an immutable earlier catalogue. The v2 catalogue has 81 research topics, not 81 rules or verified claims. Knowledge rules remain under `knowledge/v1`; test-only fixture shape remains compatible.

An approved rule must include a valid lifecycle event trail, `provenance.source_id`, source-registry version, exact `edition_id` and registered edition display, an exact locator, source verifier and verification timestamp, editorial explanation, distinct editorial and Tamil translation reviewers, a review timestamp, completed translation review, and both `translations.en` and `translations.ta`. Its source ID, tradition, and edition must resolve to the registry. A supporting excerpt is rejected unless the registry explicitly records reuse permission. Current records do not authorize excerpts, and no substantive rule is approved. The `transition_rule` helper records transitions only when an explicit caller supplies reviewer identity, date, and note; it is not an automatic approval tool.

## Rights handling

Do not bulk-copy books, modern translations, publisher scans, OCR, commentaries, or annotations. The source registry records access separately from copyright/reuse status. A publicly readable digital copy is not a reuse license. Even for an old public-domain work, check the exact edition, added apparatus/illustrations, archive terms, and commercial-use law for target jurisdictions. Route uncertain rights to professional legal review before quote/adaptation or production deployment.
