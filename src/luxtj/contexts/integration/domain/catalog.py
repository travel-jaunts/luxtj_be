"""Capability catalog (Layer A) — no secrets. Codes and credential field shapes only."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BookingApiCatalogEntry:
    code: str
    name: str
    configs: tuple[str, ...]
    lib_name: str
    auth_required: bool = False


@dataclass(frozen=True, slots=True)
class PaymentGatewayCatalogEntry:
    code: str
    name: str
    configs: tuple[str, ...]
    currency: str
    lib_name: str
    # "yes" = gateway exposes a programmatic refund API; "no" = manual refund only
    refund_api: str = "no"


@dataclass(frozen=True, slots=True)
class OtherApiCatalogEntry:
    code: str
    name: str
    configs: tuple[str, ...]


MODULES_AND_THEMES: dict[str, tuple[int, ...]] = {
    "ADMIN": (1,),
    "B2C": (0, 1, 2),
    "B2B": (1,),
}

SUB_MODULES_AND_BOOKING_APIS: dict[str, dict[str, BookingApiCatalogEntry]] = {
    "FLIGHT": {
        "citytravel": BookingApiCatalogEntry(
            code="citytravel",
            name="City Travel",
            configs=(
                "ApiLogin",
                "ApiPassword",
                "TokenGuid",
                "DeviceId",
                "EndPointUrl",
            ),
            lib_name="CityTravel",
            auth_required=False,
        ),
    },
    "HOTEL": {
        "ratehawk": BookingApiCatalogEntry(
            code="ratehawk",
            name="Ratehawk",
            configs=("API key ID", "API key access token", "EndPointUrl"),
            lib_name="Ratehawk",
            auth_required=False,
        ),
    },
    "CAR": {},
    "ACTIVITIES": {},
    "PACKAGES": {},
    "BUS": {},
    "TRAIN": {},
    "INSURANCE": {},
}

PAYMENT_GATEWAYS: dict[str, PaymentGatewayCatalogEntry] = {
    "razorpay": PaymentGatewayCatalogEntry(
        code="razorpay",
        name="Razorpay",
        configs=("API Key", "API Secret", "Company Name"),
        currency="INR",
        lib_name="Razorpay",
        refund_api="yes",
    ),
}

OTHER_APIS: dict[str, OtherApiCatalogEntry] = {
    "exchangerate-api": OtherApiCatalogEntry(
        code="exchangerate-api",
        name="ExchangeRate-API",
        configs=("API Key",),
    ),
    "googlemap": OtherApiCatalogEntry(
        code="googlemap",
        name="Google Maps",
        configs=("API Key",),
    ),
    "twilio": OtherApiCatalogEntry(
        code="twilio",
        name="Twilio SMS",
        configs=("Account SID", "Auth Token", "From Phone"),
    ),
    "telegram": OtherApiCatalogEntry(
        code="telegram",
        name="Telegram OTP (dev)",
        configs=("Bot Token", "Chat ID"),
    ),
    "bucketlistsuggestions": OtherApiCatalogEntry(
        code="bucketlistsuggestions",
        name="Bucket List Suggestions",
        configs=("Base URL", "API Key"),
    ),
}


def normalize_config_key(label: str) -> str:
    """Spaces → _; other non [A-Za-z0-9-_] → ._. """
    out: list[str] = []
    for ch in label:
        if ch == " ":
            out.append("_")
        elif ch.isalnum() or ch in "-_":
            out.append(ch)
        else:
            out.append("._.")
    return "".join(out)


def credential_value(configs: dict[str, str], *labels: str) -> str:
    """Read a credential by catalog label(s), trying normalized and raw keys."""
    for label in labels:
        for key in (normalize_config_key(label), label):
            value = configs.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
    return ""


def normalize_booking_api_currency(currency: str | None) -> str | None:
    """Return uppercased ISO-4217-ish code (3 letters) or None if empty/invalid."""
    if currency is None:
        return None
    code = str(currency).strip().upper()
    if not code:
        return None
    if len(code) != 3 or not code.isalpha():
        return None
    return code


def gateway_supports_refund_api(pg_code: str) -> bool:
    entry = PAYMENT_GATEWAYS.get(str(pg_code or "").strip().lower())
    if entry is None:
        return False
    return str(entry.refund_api or "no").strip().lower() == "yes"

