# AstroAI deterministic intelligence architecture

## Active chat path

Authenticated chat requests run through `DeterministicAstrologyIntelligence` in `backend/app/services/ai/engine.py`. The engine detects message language, classifies intent and chart topic, retrieves only the conversation owner's completed saved chart facts, loads the versioned knowledge base, matches eligible rules, and composes a validated typed response. No provider, LLM, inference service, API key, or network call is used by this path. Charts are never recalculated during chat.

The chat API in `backend/app/api/ai_routes.py` preserves authentication, conversation ownership, profile/chart checks, database-backed daily quotas, per-user idempotency, message history, and SSE. It validates a complete response before streaming. SSE sends `metadata`, then `delta` sections, then `done` with the persisted assistant message and structured response. The complete structured response is persisted in `chat_messages.response_data`; disconnects before completion leave no assistant response and mark the request retryable under the existing idempotency behavior. Migration `0005_deterministic_ai_responses` adds this nullable JSON field without removing old records.

The frontend renders the persisted answer with distinct calculated-fact, traditional-interpretation, and limitation sections. Interpretive source references are shown when present. Current knowledge files contain only test-only fixtures; those are excluded from production matching. Therefore chart questions can return actual saved facts, but no substantive traditional interpretations are currently available. General definitions without approved sourced knowledge are explicitly declined. English and Tamil response templates are supported.

## Provider code and obsolete configuration

`backend/app/services/ai/provider.py`, its provider tests, and the optional `ai` dependency extra remain as dormant legacy code; chat routes do not import or call them. `AI_PROVIDER`, `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`, timeout, and max-token Settings fields remain only for that dormant module and backward-compatible tests. They have been removed from `.env.example` and are not required for deterministic chat. The former `AI_HISTORY_MESSAGE_LIMIT` setting is no longer used because the deterministic engine does not resolve conversation references from message history.

## Usage and privacy

The daily free-tier limit remains `AI_FREE_DAILY_LIMIT` (default 20) and uses the existing atomic database counter and usage log. Reservations occur before response generation; failed attempts count once, and retrying with the same idempotency key reuses its reservation. Personal chart facts come only from owner-scoped completed chart snapshots. Birth dates, exact birth times, birthplace, coordinates, and input snapshots are excluded from the intelligence fact collection and response.

## Safety and limitations

Astrology is presented as a traditional belief system, not scientific certainty. The UI and composer advise against using it for medical, legal, or financial decisions. The deterministic engine does not answer open-ended questions from general world knowledge and does not infer context from prior turns. It returns localized clarification, missing-chart, unsupported, and unavailable-rule messages instead of inventing chart facts or interpretations. No substantive rules are production-approved pending editorial sourcing and review.
