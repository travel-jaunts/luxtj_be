"""Shared XML / SOAP infrastructure.

Import::

    from luxtj.shared_kernel.infrastructure.xml import XmlSoapClient, SoapRequest
"""

from luxtj.shared_kernel.infrastructure.xml.soap_client import SoapRequest, XmlSoapClient

__all__ = ["SoapRequest", "XmlSoapClient"]
