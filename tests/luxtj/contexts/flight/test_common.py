"""Unit tests for FlightCommon (Phase 3 skeleton)."""

from __future__ import annotations

from luxtj.contexts.flight.domain.common import FlightCommon


def test_encode_decode_result_token() -> None:
    encoded = FlightCommon.encode_result_token("citytravel", "opaque-group-1")
    decoded = FlightCommon.decode_result_token(encoded)
    assert decoded is not None
    assert decoded["booking_source"] == "citytravel"
    assert decoded["token"] == "opaque-group-1"
    assert "time" in decoded


def test_normalize_search_request_oneway() -> None:
    clean, err = FlightCommon.normalize_search_request(
        {
            "JourneyType": "OneWay",
            "AdultCount": 1,
            "ChildCount": 0,
            "InfantCount": 0,
            "CabinClass": "Economy",
            "Segments": [
                {
                    "Origin": "del",
                    "Destination": "bom",
                    "DepartureDate": "2026-09-01T00:00:00",
                }
            ],
        }
    )
    assert err is None
    assert clean is not None
    assert clean["trip_type"] == "oneway"
    assert clean["from"] == "DEL"
    assert clean["to"] == "BOM"
    assert clean["depature"] == "2026-09-01"
    assert clean["adult_config"] == 1


def test_normalize_search_request_return_requires_return_date() -> None:
    clean, err = FlightCommon.normalize_search_request(
        {
            "trip_type": "return",
            "adults": 1,
            "from": "DEL",
            "to": "BOM",
            "departure": "2026-09-01",
        }
    )
    assert clean is None
    assert err is not None
    assert "return" in err.lower()


def test_normalize_cabin_and_trip() -> None:
    assert FlightCommon.normalize_cabin_class("premium_economy") == "PremiumEconomy"
    assert FlightCommon.normalize_trip_type("roundtrip") == "return"
