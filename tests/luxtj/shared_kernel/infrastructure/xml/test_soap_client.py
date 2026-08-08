"""Unit tests for XmlSoapClient / CityTravelSoap (no network)."""

from __future__ import annotations

import pytest

from luxtj.contexts.flight.infrastructure.citytravel import CityTravelSoap
from luxtj.shared_kernel.infrastructure.xml import SoapRequest, XmlSoapClient

SAMPLE_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body>
    <AeroSearchResponse xmlns="http://tempuri.org/">
      <AeroSearchResult xmlns:a="http://schemas.datacontract.org/2004/07/SiteCity.Avia.Search"
                        xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
        <Currency xmlns="http://schemas.datacontract.org/2004/07/SiteCity.Common">EUR</Currency>
        <Success xmlns="http://schemas.datacontract.org/2004/07/SiteCity.Common">true</Success>
        <a:ResultCount>1</a:ResultCount>
        <a:SearchGuid>b316ac16-7cdf-4d49-a3a1-15f0d3e1b915</a:SearchGuid>
        <a:FlightData>
          <a:FlightData>
            <a:OfferCode>OFFER1</a:OfferCode>
            <a:TotalPrice>150.25</a:TotalPrice>
          </a:FlightData>
        </a:FlightData>
      </AeroSearchResult>
    </AeroSearchResponse>
  </s:Body>
</s:Envelope>
"""


@pytest.fixture(scope="module")
def wsdl_path():
    path = XmlSoapClient.default_sitecity_wsdl()
    if not path.is_file():
        pytest.skip(f"SiteCity WSDL missing at {path}")
    return path


def test_parse_soap_response_strips_prefixes_and_nests():
    parsed = XmlSoapClient.parse_soap_response(SAMPLE_RESPONSE)
    body = parsed["Body"]
    result = body["AeroSearchResponse"]["AeroSearchResult"]
    assert result["Success"] == "true"
    assert result["Currency"] == "EUR"
    assert result["ResultCount"] == "1"
    assert result["SearchGuid"] == "b316ac16-7cdf-4d49-a3a1-15f0d3e1b915"
    flight = result["FlightData"]["FlightData"]
    assert flight["OfferCode"] == "OFFER1"
    assert flight["TotalPrice"] == "150.25"


def test_parse_empty_and_invalid():
    assert XmlSoapClient.parse_soap_response(None) == {}
    assert XmlSoapClient.parse_soap_response("") == {}
    assert XmlSoapClient.parse_soap_response("not-xml") == {}


def test_build_aero_search_envelope_no_network(wsdl_path):
    XmlSoapClient.clear_client_cache()
    args = {
        "credentials": CityTravelSoap.auth_info(
            api_login="test",
            api_password="test",
            currency="EUR",
        ),
        "aeroSearchParams": {
            "Adults": 1,
            "Childs": 0,
            "Infants": 0,
            "FlightClass": "Econom",
            "SearchFlights": {
                "SearchFlight": [
                    {"Date": "07.06.2018", "IATAFrom": "LED", "IATATo": "BAK"},
                ]
            },
        },
    }
    soap = XmlSoapClient.build_soap_request(
        wsdl_path,
        "AeroSearch",
        args,
        to_address="http://test-api.xml.agency/SiteCity",
    )
    assert isinstance(soap, SoapRequest)
    assert soap.operation == "AeroSearch"
    assert "AeroSearch" in soap.envelope
    assert "LED" in soap.envelope
    assert "BAK" in soap.envelope
    assert "test-api.xml.agency" in soap.envelope
    assert "ISiteAvia/AeroSearch" in soap.soap_action
    assert "soap+xml" in soap.content_type_with_action()


def test_city_travel_soap_wrapper(wsdl_path):
    args = {
        "credentials": CityTravelSoap.auth_info(
            api_login="test",
            api_password="test",
            currency="USD",
            device_id="test",
        ),
        "aeroSearchParams": {
            "Adults": 2,
            "Childs": 0,
            "Infants": 0,
            "FlightClass": "Econom",
            "SearchFlights": {
                "SearchFlight": [
                    {"Date": "15.06.2019", "IATAFrom": "MOW", "IATATo": "LED"},
                ]
            },
        },
    }
    soap = CityTravelSoap.build_request(
        "AeroSearch",
        args,
        endpoint_url="http://test-api.xml.agency/SiteCity",
        wsdl_path=wsdl_path,
    )
    assert "<" in soap.envelope and "AeroSearch" in soap.envelope
    # Round-trip: build XML then parse a sample response via CT wrapper.
    parsed = CityTravelSoap.parse_response(SAMPLE_RESPONSE)
    assert parsed["Body"]["AeroSearchResponse"]["AeroSearchResult"]["Success"] == "true"


def test_auth_info_defaults_language_to_en():
    creds = CityTravelSoap.auth_info(
        api_login="test",
        api_password="test",
        currency="EUR",
    )
    assert creds["Language"] == "EN"
