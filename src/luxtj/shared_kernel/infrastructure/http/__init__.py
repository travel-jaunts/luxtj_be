"""Shared HTTP infrastructure for all booking sub-modules.

Mirrors Laravel ``App\\TeenvaLibraries`` cross-cutting HTTP helpers
(``TeenvaCurlMultiHandler`` + booking API audit).

Blenders (hotel, flight, …) and providers should import from this package only::

    from luxtj.shared_kernel.infrastructure.http import MultiHttpClient, HandleDescriptor

``multi_http_client`` is an internal transport module — do not import it from
product contexts.
"""

from luxtj.shared_kernel.infrastructure.http.audit_models import BookingApiRequestResponseRow
from luxtj.shared_kernel.infrastructure.http.audit_repository import (
    RequestResponseAuditRepository,
    SqlAlchemyRequestResponseAuditRepository,
)
from luxtj.shared_kernel.infrastructure.http.multi_http import (
    HandleDescriptor,
    InMemoryResponseCache,
    MultiHttpClient,
    decode_basic_auth_header,
    detect_response_format,
    dict_handle_to_descriptor,
    ensure_format_headers,
    normalize_request_format,
    normalize_response_text,
    parse_response_body,
    serialize_request_body,
)

__all__ = [
    "BookingApiRequestResponseRow",
    "HandleDescriptor",
    "InMemoryResponseCache",
    "MultiHttpClient",
    "RequestResponseAuditRepository",
    "SqlAlchemyRequestResponseAuditRepository",
    "decode_basic_auth_header",
    "detect_response_format",
    "dict_handle_to_descriptor",
    "ensure_format_headers",
    "normalize_request_format",
    "normalize_response_text",
    "parse_response_body",
    "serialize_request_body",
]
