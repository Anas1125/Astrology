# Birthplace search

Updated: 2026-11-03

AstroAI's authenticated `GET /api/v1/profiles/location-search` endpoint proxies text autocomplete to Geoapify (`/v1/geocode/autocomplete`). The frontend never receives the provider key. Configure `GEOAPIFY_API_KEY` in the backend environment; without it, the endpoint responds with a clear 503 and the profile form remains manually usable. Queries have a three-character minimum, are debounced in the UI, and are limited per user by the shared database rate limiter. The provider request has a bounded timeout. The query is a city/place name only; birth date/time are not sent.

Selecting a returned suggestion is the only action that populates place-derived country and coordinates. The response timezone is optional and accepted only if Python recognizes it as an IANA `ZoneInfo`. No coordinates/timezone are inferred from typed text. Users can edit every returned value. Typing a changed place clears prior location-derived fields so stale coordinates cannot silently remain attached to a different birthplace.

Geoapify's current published autocomplete documentation states returned fields can be absent, including timezone. Its pricing/usage FAQ states its Free plan may be used for commercial projects within usage, feature, and rate limits, and requires a follow-link attribution to Geoapify plus data-source attribution. The published terms require OpenStreetMap attribution and Geoapify attribution on the Free subscription. AstroAI therefore shows both attributions on the birth profile page, including when displaying previously selected data. The service also states its open-data results may be stored when their attribution is retained. These published terms were reviewed on 2026-11-03; they can change, and this is not legal advice or a determination that a future AstroAI deployment complies. Verify current plan limits, applicable privacy obligations, attribution, and terms before production use.

References:

- [Geoapify Address Autocomplete API documentation](https://apidocs.geoapify.com/docs/geocoding/address-autocomplete/)
- [Geoapify Geocoding API usage FAQ](https://www.geoapify.com/geocoding-api/)
- [Geoapify pricing and usage limits](https://www.geoapify.com/pricing/)
- [Geoapify Terms and Conditions](https://www.geoapify.com/terms-and-conditions/)
- [OpenStreetMap copyright and attribution](https://www.openstreetmap.org/copyright)

## Horoscope catalogue status

The horoscope API now matches an exact astrology system, period, sign, topic, and date range. It serves content only when an English and Tamil pair shares the same reviewed source references and both records have approval, source verification, editorial review, reviewer, and review timestamp. The current catalogue has no records, so requests return the explicit `catalogue_empty` reason; no placeholder or invented prediction is returned. Personalized chart-specific horoscope text remains unavailable until such a separate, explicitly chart-scoped bilingual workflow exists. Schema support for these review dimensions is introduced by Alembic revision `0007_horoscope_review_scope`.
