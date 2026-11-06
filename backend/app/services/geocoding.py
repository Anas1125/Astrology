"""Geoapify-backed birthplace autocomplete. Provider results are never inferred locally."""
from __future__ import annotations

from hashlib import sha256
import json
import math
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ENDPOINT = "https://api.geoapify.com/v1/geocode/autocomplete"
ATTRIBUTION = "Geoapify · © OpenStreetMap contributors"


class GeocodingUnavailable(Exception):
    """Provider is unconfigured or did not return a usable response."""


def _optional_timezone(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return value


def _suggestion(feature: dict) -> dict | None:
    props = feature.get("properties")
    if not isinstance(props, dict):
        return None
    try:
        latitude, longitude = float(props["lat"]), float(props["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(latitude) or not -90 <= latitude <= 90 or not math.isfinite(longitude) or not -180 <= longitude <= 180:
        return None
    city = next((props.get(key) for key in ("city", "town", "village", "municipality", "name") if isinstance(props.get(key), str) and props[key].strip()), None)
    country = props.get("country") if isinstance(props.get("country"), str) else ""
    if not city or not country:
        return None
    region = next((props.get(key) for key in ("state", "county", "region") if isinstance(props.get(key), str) and props[key].strip()), None)
    timezone_value = props.get("timezone")
    timezone_name = timezone_value.get("name") if isinstance(timezone_value, dict) else None
    place_id = props.get("place_id")
    if not isinstance(place_id, str) or not place_id:
        place_id = sha256(f"{city}|{region}|{country}|{latitude:.6f}|{longitude:.6f}".encode()).hexdigest()[:24]
    return {
        "id": place_id,
        "city": city.strip(),
        "region": region.strip() if region else None,
        "country": country.strip(),
        "latitude": latitude,
        "longitude": longitude,
        "timezone": _optional_timezone(timezone_name),
        "attribution": ATTRIBUTION,
    }


def search_places(query: str, *, api_key: str | None, language: str = "en", timeout: float = 5.0) -> list[dict]:
    if not api_key:
        raise GeocodingUnavailable("Birthplace search is not configured")
    params = urlencode({"text": query, "format": "geojson", "limit": 8, "lang": language, "apiKey": api_key})
    request = Request(f"{ENDPOINT}?{params}", headers={"Accept": "application/json", "User-Agent": "AstroAI/0.1 birthplace autocomplete"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GeocodingUnavailable("Birthplace provider request failed") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        raise GeocodingUnavailable("Birthplace provider returned an invalid response")
    output = []
    seen = set()
    for feature in payload["features"]:
        if not isinstance(feature, dict):
            continue
        item = _suggestion(feature)
        if item and item["id"] not in seen:
            output.append(item)
            seen.add(item["id"])
    return output
