"""City Travel SOAP boundary — JSON/dict in app code, XML on the wire.

``MultiHttpClient`` must receive **XML** request bodies and will persist XML in
``booking_api_request_responses``. All dict↔XML conversion for City Travel happens
here (via :class:`~luxtj.shared_kernel.infrastructure.xml.XmlSoapClient`), not in
MultiHttp or the blender.

Typical provider flow (Phase 4+)::

    soap = CityTravelSoap.build_request("AeroSearch", {...}, endpoint_url=...)
    handle = HandleDescriptor(
        url=endpoint_url,
        method="POST",
        body=soap.envelope,           # XML
        request_format="soap",
        headers={
            "Content-Type": soap.content_type_with_action(),
            "SOAPAction": f'"{soap.soap_action}"',
        },
        ...
    )
    raw_xml = await multi_http.execute(...)
    data = CityTravelSoap.parse_response(raw_xml)  # dict for format_*
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from luxtj.shared_kernel.infrastructure.xml import SoapRequest, XmlSoapClient


class CityTravelSoap:
    """City Travel–specific wrapper around the shared XmlSoapClient + SiteCity WSDL."""

    DEFAULT_LANGUAGE = "EN"

    @staticmethod
    def wsdl_path() -> Path:
        return XmlSoapClient.default_sitecity_wsdl()

    @classmethod
    def build_request(
        cls,
        operation: str,
        arguments: dict[str, Any],
        *,
        endpoint_url: str | None = None,
        wsdl_path: str | Path | None = None,
    ) -> SoapRequest:
        """Serialize a City Travel operation to a SOAP envelope (no HTTP)."""
        return XmlSoapClient.build_soap_request(
            wsdl_path or cls.wsdl_path(),
            operation,
            arguments,
            to_address=endpoint_url,
        )

    @classmethod
    def parse_response(cls, raw_xml: str | bytes | None) -> dict[str, Any]:
        """Parse a City Travel SOAP/XML response into a plain dict."""
        return XmlSoapClient.parse_soap_response(raw_xml)

    @classmethod
    def auth_info(
        cls,
        *,
        api_login: str,
        api_password: str,
        currency: str,
        device_id: str = "test",
        token_guid: str = "00000000-0000-0000-0000-000000000000",
        language: str | None = None,
    ) -> dict[str, Any]:
        """Credentials dict for SOAP ``credentials`` / ``authInfo`` parameters."""
        return {
            "ApiLogin": api_login,
            "ApiPassword": api_password,
            "Currency": currency,
            "DeviceId": device_id,
            "Language": language or cls.DEFAULT_LANGUAGE,
            "TokenGuid": token_guid,
        }
