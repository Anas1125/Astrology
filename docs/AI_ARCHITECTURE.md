# AstroAI deterministic intelligence architecture

## Active chat path

Authenticated chat requests run through `DeterministicAstrologyIntelligence` in `backend/app/services/ai/engine.py`. The engine detects message language, classifies intent and chart topic, retrieves only the conversation owner's completed saved chart facts, loads the versioned knowledge base, matches eligible rules, and composes a validated typed response. No provider, LLM, inference service, API key, or network call is used by this path. Charts are never recalculated during chat.

The chat API in `backend/app/api/ai_routes.py` preserves authentication, conversation ownership, profile/chart checks, database-backed daily quotas, per-user idempotency, message history, and SSE. It validates a complete response before streaming. SSE sends `metadata`, then `delta` sections, then `done` with the persisted assistant message and structured response. The complete structured response is persisted in `chat_messages.response_data`; disconnects before completion leave no assistant response and mark the request retryable under the existing idempotency behavior. Migration `0005_deterministic_ai_responses` adds this nullable JSON field without removing old records.

The frontend renders the persisted answer with distinct calculated-fact, traditional-interpretation, and limitation sections. Calculated facts expose their saved-chart source references; interpretive source references show the registered edition and passage locator. Current knowledge files contain only test-only fixtures; those are excluded from production matching. Therefore chart questions can return actual saved facts, but no substantive traditional interpretations are currently available. General definitions without approved sourced knowledge are explicitly declined. English and Tamil response templates are supported.

## Provider independence

There is no external provider adapter, prompt builder, provider-only dependency extra, API-key setting, or inference-service configuration in the active repository. The AI package uses only the internal deterministic classifier, saved-chart fact adapter, knowledge matcher, and response composer. Chat tests reject outbound socket connections while exercising the API.

## Usage and privacy

The daily technical abuse limit remains `AI_FREE_DAILY_LIMIT` (default 20) and uses the existing atomic database counter and usage log. Reservations occur before response generation; failed attempts count once, and retrying with the same idempotency key reuses its reservation. Personal chart facts come only from owner-scoped completed chart snapshots. Birth dates, exact birth times, birthplace, coordinates, and input snapshots are excluded from the intelligence fact collection and response. Narrow follow-ups may inherit chart entities from the latest user question in the same conversation; assistant output is never used as a source of chart facts.

## Safety and limitations

Astrology is presented as a traditional belief system, not scientific certainty. The UI and composer advise against using it for medical, legal, or financial decisions. The deterministic engine does not answer open-ended questions from general world knowledge. It returns localized clarification, missing-chart, unsupported, and unavailable-rule messages instead of inventing chart facts or interpretations. Narrow follow-ups can reuse entities from the latest user question in the same conversation; assistant text cannot establish chart facts. No substantive rules are production-approved pending editorial sourcing and review.

## Source research and approval

`backend/app/services/ai/knowledge/sources/registry.v1.json` is the bibliographic source registry, validated by `source_registry.py`. It stores edition-level access, completeness, rights notes, citation form, and verification uncertainties. `knowledge/research/catalogue.v2.json` is a typed, research-only catalogue of 81 topics; it contains no interpretation claims. Rule provenance supports source and edition IDs, exact chapter/verse/page/section locators, optional excerpts, citation notes, independent editorial text, English/Tamil translations, and reviewer metadata. `knowledge_workflow.py` enforces explicit research-candidate, source-verification, editorial-review, translation-review, approval, rejection, and retirement transitions.

The loader, matcher, and response composer all retain fail-closed approval checks. Production rules must link to a registered source edition, provide a precise passage locator, bilingual text and review data, and use conditions supported by chart facts. Excerpts are rejected unless that source's registry explicitly permits their reuse. The current registry grants no excerpt reuse; no substantive rule is approved. Bibliographic presence or editorial review is not scientific validation or commercial copyright clearance.
