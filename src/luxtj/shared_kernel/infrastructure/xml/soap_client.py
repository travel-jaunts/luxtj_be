"""SOAP / XML helpers — port of ``TeenvaXmlClient``.

App code works with dict/JSON. This module builds SOAP envelopes from a WSDL
**without** calling the network, and parses SOAP/XML responses into dicts.

Booking providers (e.g. City Travel) own the conversion boundary:

- dict → XML envelope → ``HandleDescriptor.body`` for ``MultiHttpClient``
- MultiHttp audit stores the **XML** request/response
- XML response → dict inside the provider before domain formatting

Do **not** put JSON↔XML conversion inside ``MultiHttpClient``.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lxml import etree
from zeep import Client, Settings
from zeep.transports import Transport

_PREFIX_RE = re.compile(r"(</?)([A-Za-z][A-Za-z0-9_.-]*):([^>]*>)")
_CLIENT_LOCK = threading.Lock()
_CLIENT_CACHE: dict[str, Client] = {}


@dataclass(frozen=True, slots=True)
class SoapRequest:
    """Serialized SOAP call ready for MultiHttp (XML body + SOAP headers)."""

    operation: str
    envelope: str
    soap_action: str
    content_type: str = 'application/soap+xml; charset=utf-8'

    def content_type_with_action(self) -> str:
        action = self.soap_action.strip().strip('"')
        if not action:
            return self.content_type
        return f'{self.content_type}; action="{action}"'


class XmlSoapClient:
    """WSDL-backed SOAP envelope builder + XML→dict parser."""

    @staticmethod
    def default_sitecity_wsdl() -> Path:
        """Packaged City Travel WSDL under ``luxtj_be/assets/wsdl/SiteCity.xml``."""
        # .../src/luxtj/shared_kernel/infrastructure/xml/soap_client.py → luxtj_be/
        here = Path(__file__).resolve()
        root = here.parents[5]  # luxtj_be
        return root / "assets" / "wsdl" / "SiteCity.xml"

    @classmethod
    def get_client(cls, wsdl_path: str | Path) -> Client:
        path = Path(wsdl_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"WSDL not found: {path}")
        key = str(path)
        with _CLIENT_LOCK:
            cached = _CLIENT_CACHE.get(key)
            if cached is not None:
                return cached
            settings = Settings(strict=False, xml_huge_tree=True)
            # Transport is unused for create_message; keep a short timeout as safety.
            client = Client(
                str(path),
                settings=settings,
                transport=Transport(timeout=5),
            )
            _CLIENT_CACHE[key] = client
            return client

    @classmethod
    def clear_client_cache(cls) -> None:
        with _CLIENT_LOCK:
            _CLIENT_CACHE.clear()

    @classmethod
    def build_soap_request(
        cls,
        wsdl_path: str | Path,
        operation: str,
        arguments: dict[str, Any] | None = None,
        *,
        to_address: str | None = None,
        service_name: str | None = None,
        port_name: str | None = None,
    ) -> SoapRequest:
        """Build a SOAP 1.2 envelope for ``operation`` from plain dict arguments (no HTTP)."""
        client = cls.get_client(wsdl_path)
        service = cls._resolve_service(client, service_name=service_name, port_name=port_name)
        args = arguments or {}
        node = client.create_message(service, operation, **args)
        if to_address:
            cls._rewrite_wsa_to(node, to_address)
        envelope = etree.tostring(node, encoding="unicode")
        soap_action = cls._soap_action_for(service, operation)
        return SoapRequest(
            operation=operation,
            envelope=envelope,
            soap_action=soap_action,
            content_type="application/soap+xml; charset=utf-8",
        )

    @classmethod
    def parse_soap_response(cls, raw_xml: str | bytes | None) -> dict[str, Any]:
        """Strip namespace prefixes and recurse XML into a dict (TeenvaXmlClient::parse)."""
        if raw_xml is None:
            return {}
        text = raw_xml.decode("utf-8") if isinstance(raw_xml, (bytes, bytearray)) else str(raw_xml)
        text = text.strip()
        if not text:
            return {}
        cleaned = _PREFIX_RE.sub(r"\1\3", text)
        try:
            root = etree.fromstring(cleaned.encode("utf-8"))
        except etree.XMLSyntaxError:
            return {}
        return cls._element_to_dict(root)

    @classmethod
    def _resolve_service(
        cls,
        client: Client,
        *,
        service_name: str | None,
        port_name: str | None,
    ) -> Any:
        if service_name and port_name:
            return client.bind(service_name, port_name)
        # Prefer first SOAP 1.2-capable binding / default service proxy.
        return client.service

    @classmethod
    def _soap_action_for(cls, service: Any, operation: str) -> str:
        try:
            binding = getattr(service, "_binding", None)
            op = binding.get(operation) if binding is not None else None
            action = getattr(op, "soapaction", None) if op is not None else None
            if action:
                return str(action).strip().strip('"')
        except Exception:
            pass
        return f"http://tempuri.org/{operation}"

    @classmethod
    def _rewrite_wsa_to(cls, envelope: etree._Element, to_address: str) -> None:
        # Match any To in addressing namespace(s).
        for el in envelope.xpath(
            ".//*[local-name()='To' and "
            "(namespace-uri()='http://www.w3.org/2005/08/addressing' "
            "or namespace-uri()='http://schemas.xmlsoap.org/ws/2004/08/addressing')]"
        ):
            el.text = to_address

    @classmethod
    def _element_to_dict(cls, element: etree._Element) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for child in element:
            tag = etree.QName(child).localname
            nested = cls._element_to_dict(child)
            attrs: dict[str, Any] = {}
            if child.attrib:
                attrs["@attributes"] = {str(k): str(v) for k, v in child.attrib.items()}
            text = (child.text or "").strip()
            if text:
                if attrs or nested:
                    attrs["@values"] = text
                else:
                    attrs = text  # type: ignore[assignment]
            if nested:
                element_data: Any = {**attrs, **nested} if isinstance(attrs, dict) else nested
            else:
                element_data = attrs

            if tag in result:
                existing = result[tag]
                if not isinstance(existing, list):
                    result[tag] = [existing]
                result[tag].append(element_data)
            else:
                result[tag] = element_data
        return result
