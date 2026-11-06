import json
from urllib.error import URLError

import pytest

from app.services import geocoding
from app.services.geocoding import GeocodingUnavailable, search_places


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def feature(place_id, city, state, country, lat, lon, timezone=None):
    props = {"place_id": place_id, "city": city, "state": state, "country": country, "lat": lat, "lon": lon}
    if timezone is not None:
        props["timezone"] = {"name": timezone}
    return {"type": "Feature", "properties": props}


def test_search_normalizes_ambiguous_results_and_only_accepts_valid_iana_timezone(monkeypatch):
    features = [
        feature("nagercoil-in", "Nagercoil", "Tamil Nadu", "India", 8.1833, 77.4119, "Asia/Kolkata"),
        feature("nagercoil-us", "Nagercoil", "Some State", "United States", 40.2, -75.1, "Not/AZone"),
    ]
    seen = {}
    def fake_urlopen(request, timeout):
        seen.update(url=request.full_url, timeout=timeout)
        return FakeResponse({"features": features})
    monkeypatch.setattr(geocoding, "urlopen", fake_urlopen)

    results = search_places("Nagercoil", api_key="private-key", language="ta", timeout=3.5)

    assert len(results) == 2
    assert [(x["city"], x["region"], x["country"]) for x in results] == [
        ("Nagercoil", "Tamil Nadu", "India"), ("Nagercoil", "Some State", "United States")
    ]
    assert results[0]["timezone"] == "Asia/Kolkata"
    assert results[1]["timezone"] is None
    assert results[0]["latitude"] == pytest.approx(8.1833)
    assert "private-key" in seen["url"]  # Sent only to the provider request, never returned by the service.
    assert seen["timeout"] == 3.5


def test_missing_key_and_provider_errors_fail_clearly(monkeypatch):
    with pytest.raises(GeocodingUnavailable):
        search_places("Paris", api_key=None)
    monkeypatch.setattr(geocoding, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(URLError("offline")))
    with pytest.raises(GeocodingUnavailable, match="request failed"):
        search_places("Paris", api_key="key")


def test_invalid_coordinates_and_missing_location_labels_are_discarded(monkeypatch):
    malformed = [feature("bad", "Bad Place", "Region", "Country", 91, 0, "UTC"),
                 feature("missing", "", "Region", "Country", 0, 0, "Asia/Kolkata")]
    monkeypatch.setattr(geocoding, "urlopen", lambda *_a, **_k: FakeResponse({"features": malformed}))
    assert search_places("Somewhere", api_key="key") == []
