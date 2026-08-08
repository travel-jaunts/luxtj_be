"""City Travel Phase 5 — live Search (SOAP build + format/group/cache; no network)."""

from __future__ import annotations

import os

import pytest

from luxtj.contexts.flight.domain.common import FlightCommon
from luxtj.contexts.flight.infrastructure.citytravel.normalize import itinerary_fingerprint
from luxtj.contexts.flight.infrastructure.citytravel.provider import CityTravelFlightProvider
from luxtj.contexts.flight.infrastructure.token_cache import cache_get
from luxtj.shared_kernel.infrastructure.xml import XmlSoapClient

SEARCH_XML = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body>
    <AeroSearchResponse xmlns="http://tempuri.org/">
      <AeroSearchResult xmlns:a="http://schemas.datacontract.org/2004/07/SiteCity.Avia.Search"
                        xmlns:b="http://schemas.datacontract.org/2004/07/SiteCity.Avia.Common"
                        xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
        <Currency xmlns="http://schemas.datacontract.org/2004/07/SiteCity.Common">EUR</Currency>
        <Success xmlns="http://schemas.datacontract.org/2004/07/SiteCity.Common">true</Success>
        <a:ResultCount>3</a:ResultCount>
        <a:SearchGuid>b316ac16-7cdf-4d49-a3a1-15f0d3e1b915</a:SearchGuid>
        <a:FlightData>
          <a:FlightData>
            <a:OfferCode>OFFER-CHEAP</a:OfferCode>
            <a:TotalPrice>180.00</a:TotalPrice>
            <a:AdultPrice>180.00</a:AdultPrice>
            <a:Offers>
              <b:OfferInfo>
                <b:Rph>1</b:Rph>
                <b:ValidatingAirline>J2</b:ValidatingAirline>
                <b:Segments>
                  <b:OfferSegment>
                    <b:Departure><b:Date>07.06.2026 23:10</b:Date><b:Iata>LED</b:Iata></b:Departure>
                    <b:Arrival><b:Date>08.06.2026 03:45</b:Date><b:Iata>GYD</b:Iata></b:Arrival>
                    <b:FlightNum>J2-9020</b:FlightNum>
                    <b:FlightClass>Econom</b:FlightClass>
                    <b:FlightMinutes>215</b:FlightMinutes>
                    <b:MarketingAirline>J2</b:MarketingAirline>
                    <b:OperatingAirline>J2</b:OperatingAirline>
                    <b:Baggage><b:Count>0</b:Count><b:BaggageType>Pieces</b:BaggageType></b:Baggage>
                  </b:OfferSegment>
                </b:Segments>
              </b:OfferInfo>
            </a:Offers>
          </a:FlightData>
          <a:FlightData>
            <a:OfferCode>OFFER-FLEX</a:OfferCode>
            <a:TotalPrice>310.00</a:TotalPrice>
            <a:AdultPrice>310.00</a:AdultPrice>
            <a:Offers>
              <b:OfferInfo>
                <b:Rph>1</b:Rph>
                <b:ValidatingAirline>J2</b:ValidatingAirline>
                <b:Segments>
                  <b:OfferSegment>
                    <b:Departure><b:Date>07.06.2026 23:10</b:Date><b:Iata>LED</b:Iata></b:Departure>
                    <b:Arrival><b:Date>08.06.2026 03:45</b:Date><b:Iata>GYD</b:Iata></b:Arrival>
                    <b:FlightNum>J2-9020</b:FlightNum>
                    <b:FlightClass>Econom</b:FlightClass>
                    <b:FlightMinutes>215</b:FlightMinutes>
                    <b:MarketingAirline>J2</b:MarketingAirline>
                    <b:OperatingAirline>J2</b:OperatingAirline>
                    <b:Baggage><b:Count>2</b:Count><b:BaggageType>Pieces</b:BaggageType></b:Baggage>
                  </b:OfferSegment>
                </b:Segments>
              </b:OfferInfo>
            </a:Offers>
          </a:FlightData>
          <a:FlightData>
            <a:OfferCode>OFFER-OTHER</a:OfferCode>
            <a:TotalPrice>195.00</a:TotalPrice>
            <a:AdultPrice>195.00</a:AdultPrice>
            <a:Offers>
              <b:OfferInfo>
                <b:Rph>1</b:Rph>
                <b:ValidatingAirline>SU</b:ValidatingAirline>
                <b:Segments>
                  <b:OfferSegment>
                    <b:Departure><b:Date>07.06.2026 10:00</b:Date><b:Iata>LED</b:Iata></b:Departure>
                    <b:Arrival><b:Date>07.06.2026 14:30</b:Date><b:Iata>GYD</b:Iata></b:Arrival>
                    <b:FlightNum>SU-1850</b:FlightNum>
                    <b:FlightClass>Econom</b:FlightClass>
                    <b:FlightMinutes>270</b:FlightMinutes>
                    <b:MarketingAirline>SU</b:MarketingAirline>
                    <b:OperatingAirline>SU</b:OperatingAirline>
                    <b:Baggage><b:Count>1</b:Count><b:BaggageType>Pieces</b:BaggageType></b:Baggage>
                  </b:OfferSegment>
                </b:Segments>
              </b:OfferInfo>
            </a:Offers>
          </a:FlightData>
        </a:FlightData>
      </AeroSearchResult>
    </AeroSearchResponse>
  </s:Body>
</s:Envelope>
"""


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> CityTravelFlightProvider:
    os.environ.setdefault("LTJBE_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setattr(
        "luxtj.contexts.currency.domain.admin_currency.AdminCurrency.rate_to_admin_or_one",
        staticmethod(lambda _from: 1.0),
    )
    monkeypatch.setattr(
        "luxtj.contexts.currency.domain.admin_currency.AdminCurrency.code",
        staticmethod(lambda: "USD"),
    )
    return CityTravelFlightProvider(
        {
            "currency": "EUR",
            "configs": {
                "ApiLogin": "test",
                "ApiPassword": "test",
                "DeviceId": "test",
                "TokenGuid": "00000000-0000-0000-0000-000000000000",
                "EndPointUrl": "http://test-api.xml.agency/SiteCity",
            },
        },
        booking_api_id="test-api",
    )


def test_get_search_request_builds_soap_xml(provider: CityTravelFlightProvider) -> None:
    wsdl = XmlSoapClient.default_sitecity_wsdl()
    if not wsdl.is_file():
        pytest.skip(f"SiteCity WSDL missing at {wsdl}")

    handles = provider.get_search_request(
        {
            "trip_type": "oneway",
            "cabin_class": "Economy",
            "adult_config": 1,
            "child_config": 0,
            "infant_config": 0,
            "from": "LED",
            "to": "GYD",
            "depature": "2026-06-07",
        }
    )
    assert len(handles) == 1
    handle = handles[0]
    assert handle.url.endswith("SiteCity")
    assert handle.request_format == "soap"
    assert "AeroSearch" in handle.body
    assert "LED" in handle.body
    assert "GYD" in handle.body
    assert "EUR" in handle.body
    assert handle.booking_api_id == "test-api"
    assert "SOAPAction" in (handle.headers or {})


def test_get_search_request_requires_credentials() -> None:
    os.environ.setdefault("LTJBE_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    p = CityTravelFlightProvider({"currency": "EUR", "configs": {}})
    assert p.get_search_request({"from": "LED", "to": "GYD", "depature": "2026-06-07"}) == []


@pytest.mark.asyncio
async def test_format_search_groups_cheapest_and_caches(
    provider: CityTravelFlightProvider,
) -> None:
    formatted = await provider.format_search_response(
        SEARCH_XML,
        {
            "trip_type": "oneway",
            "cabin_class": "Economy",
            "adult_config": 1,
            "child_config": 0,
            "infant_config": 0,
            "from": "LED",
            "to": "GYD",
            "depature": "2026-06-07",
        },
    )
    assert formatted["status"] is True
    flights = formatted["data"]
    assert len(flights) == 2  # J2 group + SU group

    j2 = next(f for f in flights if (f.get("Attr") or {}).get("AirlineRemark") == "J2")
    assert float(j2["Price"]["TotalDisplayFare"]) == 180.0
    assert j2["Price"]["Currency"] == "USD"
    assert j2["Price"]["supplier_currency"] == "EUR"

    decoded = FlightCommon.decode_result_token(j2["ResultToken"])
    assert decoded is not None
    assert str(decoded["token"]).startswith("citytravel_group_")
    group = cache_get(str(decoded["token"]))
    assert isinstance(group, dict)
    assert len(group["upsellRows"]) == 2
    fares = [float(r["Price"]["TotalDisplayFare"]) for r in group["upsellRows"]]
    assert fares == [180.0, 310.0]
    offer_tok = FlightCommon.decode_result_token(group["upsellRows"][0]["ResultToken"])
    assert offer_tok is not None
    assert str(offer_tok["token"]).startswith("citytravel_offer_")


def test_itinerary_fingerprint_ignores_offer_code() -> None:
    a = {
        "OfferCode": "A",
        "Offers": {
            "OfferInfo": [
                {
                    "Rph": "1",
                    "Segments": {
                        "OfferSegment": [
                            {
                                "Departure": {"Date": "07.06.2026 23:10", "Iata": "LED"},
                                "Arrival": {"Date": "08.06.2026 03:45", "Iata": "GYD"},
                                "FlightNum": "J2-9020",
                            }
                        ]
                    },
                }
            ]
        },
    }
    b = {**a, "OfferCode": "B", "TotalPrice": "999"}
    assert itinerary_fingerprint(a) == itinerary_fingerprint(b)
    assert itinerary_fingerprint(a)


@pytest.mark.asyncio
async def test_other_spi_still_not_implemented(provider: CityTravelFlightProvider) -> None:
    upsell = await provider.get_upsell("citytravel_group_x")
    assert upsell["status"] is False
    assert "not implemented yet" in upsell["message"]
