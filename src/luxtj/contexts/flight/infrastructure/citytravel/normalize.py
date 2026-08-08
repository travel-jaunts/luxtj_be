"""City Travel AeroSearch normalize — FlightData → B2C rows + itinerary grouping."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def force_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def extract_aero_search_result(parsed: dict[str, Any] | None) -> dict[str, Any]:
    """Unwrap SOAP parse tree or accept a flat AeroSearchResult-shaped dict."""
    if not isinstance(parsed, dict) or not parsed:
        return {}
    if "FlightData" in parsed and ("Success" in parsed or "SearchGuid" in parsed):
        return parsed
    if "AeroSearchResult" in parsed and isinstance(parsed["AeroSearchResult"], dict):
        return parsed["AeroSearchResult"]
    body = parsed.get("Body")
    if isinstance(body, dict):
        resp = body.get("AeroSearchResponse") or body.get("AeroSearchResult") or {}
        if isinstance(resp, dict):
            if "AeroSearchResult" in resp and isinstance(resp["AeroSearchResult"], dict):
                return resp["AeroSearchResult"]
            if "FlightData" in resp or "Success" in resp:
                return resp
    return {}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def parse_ct_datetime(raw: str | None) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def cabin_label(raw: str | None) -> str:
    key = str(raw or "").strip().lower().replace(" ", "")
    return {
        "econom": "Economy",
        "economy": "Economy",
        "premiumeconomy": "PremiumEconomy",
        "business": "Business",
        "first": "First",
    }.get(key, "Economy")


def flight_class_for_soap(cabin: str | None) -> str:
    key = str(cabin or "Economy").strip().lower().replace(" ", "").replace("_", "")
    return {
        "economy": "Econom",
        "econom": "Econom",
        "premiumeconomy": "PremiumEconomy",
        "business": "Business",
        "first": "First",
    }.get(key, "Econom")


def date_to_ct(iso_date: str) -> str:
    text = str(iso_date or "").strip().split("T")[0]
    try:
        dt = datetime.strptime(text, "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except ValueError:
        return text


def offer_infos(flight_data: dict[str, Any]) -> list[dict[str, Any]]:
    offers = flight_data.get("Offers") or flight_data.get("OfferInfo")
    if isinstance(offers, dict):
        infos = offers.get("OfferInfo") or offers.get("Offer") or offers
        return [x for x in force_list(infos) if isinstance(x, dict)]
    return [x for x in force_list(offers) if isinstance(x, dict)]


def segments_from_offer(offer: dict[str, Any]) -> list[dict[str, Any]]:
    segs = offer.get("Segments") or offer.get("OfferSegment")
    if isinstance(segs, dict):
        inner = segs.get("OfferSegment") or segs.get("Segment") or segs
        return [x for x in force_list(inner) if isinstance(x, dict)]
    return [x for x in force_list(segs) if isinstance(x, dict)]


def itinerary_fingerprint(flight_data: dict[str, Any]) -> str:
    """Stable key ignoring OfferCode / price — same flights → same group."""
    parts: list[str] = []
    for offer in offer_infos(flight_data):
        rph = str(offer.get("Rph") or "1")
        for seg in segments_from_offer(offer):
            dep = seg.get("Departure") if isinstance(seg.get("Departure"), dict) else {}
            arr = seg.get("Arrival") if isinstance(seg.get("Arrival"), dict) else {}
            flight_num = str(seg.get("FlightNum") or "").strip().upper()
            dep_iata = str(dep.get("Iata") or "").strip().upper()
            arr_iata = str(arr.get("Iata") or "").strip().upper()
            dep_dt = parse_ct_datetime(str(dep.get("Date") or ""))
            dep_key = dep_dt.strftime("%Y-%m-%dT%H:%M") if dep_dt else str(dep.get("Date") or "")
            parts.append(f"{rph}:{flight_num}:{dep_iata}:{arr_iata}:{dep_key}")
    return "|".join(parts)


def map_segment(seg: dict[str, Any]) -> dict[str, Any]:
    dep = seg.get("Departure") if isinstance(seg.get("Departure"), dict) else {}
    arr = seg.get("Arrival") if isinstance(seg.get("Arrival"), dict) else {}
    dep_dt = parse_ct_datetime(str(dep.get("Date") or ""))
    arr_dt = parse_ct_datetime(str(arr.get("Date") or ""))
    marketing = str(seg.get("MarketingAirline") or "").strip().upper()
    operating = str(seg.get("OperatingAirline") or marketing).strip().upper()
    flight_num = str(seg.get("FlightNum") or "").strip()
    number_only = flight_num.split("-", 1)[-1] if "-" in flight_num else flight_num
    bag = seg.get("Baggage") if isinstance(seg.get("Baggage"), dict) else {}
    bag_count = bag.get("Count")
    bag_type = str(bag.get("BaggageType") or "")
    check_in = None
    if bag_count not in (None, "") and bag_type.lower() not in {"", "unknown", "nil"}:
        check_in = f"{bag_count} {bag_type}".strip()
    minutes = int(_as_float(seg.get("FlightMinutes"), 0))
    return {
        "Origin": {
            "AirportCode": str(dep.get("Iata") or "").upper(),
            "CityName": "",
            "AirportName": "",
            "date_time": dep_dt.isoformat() if dep_dt else None,
            "DateTime": dep_dt.strftime("%Y-%m-%d %H:%M:%S") if dep_dt else None,
            "date": dep_dt.strftime("%Y-%m-%d") if dep_dt else None,
            "time": dep_dt.strftime("%H:%M:%S") if dep_dt else None,
            "FDTV": int(dep_dt.timestamp()) if dep_dt else None,
            "OriginTerminal": dep.get("Terminal"),
        },
        "Destination": {
            "AirportCode": str(arr.get("Iata") or "").upper(),
            "CityName": "",
            "AirportName": "",
            "date_time": arr_dt.isoformat() if arr_dt else None,
            "DateTime": arr_dt.strftime("%Y-%m-%d %H:%M:%S") if arr_dt else None,
            "date": arr_dt.strftime("%Y-%m-%d") if arr_dt else None,
            "time": arr_dt.strftime("%H:%M:%S") if arr_dt else None,
            "FATV": int(arr_dt.timestamp()) if arr_dt else None,
            "DestinationTerminal": arr.get("Terminal"),
        },
        "OperatorCode": marketing,
        "DisplayOperatorCode": marketing,
        "OperatorName": marketing,
        "FlightNumber": number_only,
        "CabinClass": cabin_label(str(seg.get("FlightClass") or "")),
        "CabinClassName": cabin_label(str(seg.get("FlightClass") or "")),
        "Duration": minutes,
        "Attr": {
            "AvailableSeats": seg.get("ResBookDesigQuantity"),
            "Baggage": check_in,
            "CabinBaggage": None,
            "AircraftCode": seg.get("AirCraft"),
            "OperatingCarrier": operating,
            "SelfConnect": _as_bool(seg.get("SelfConnect")),
            "Charter": _as_bool(seg.get("Charter")),
            "LowCost": _as_bool(seg.get("LowCost")),
        },
    }


def build_flight_details(flight_data: dict[str, Any]) -> list[list[dict[str, Any]]]:
    legs: dict[str, list[dict[str, Any]]] = {}
    for offer in offer_infos(flight_data):
        rph = str(offer.get("Rph") or "1")
        legs.setdefault(rph, [])
        for seg in segments_from_offer(offer):
            legs[rph].append(map_segment(seg))
    ordered_keys = sorted(legs.keys(), key=lambda k: (0, int(k)) if str(k).isdigit() else (1, k))
    return [legs[k] for k in ordered_keys if legs[k]]


def build_price_block(
    flight_data: dict[str, Any],
    *,
    search_data: dict[str, Any] | None,
    supplier_currency: str,
    admin_currency: str,
    conversion_rate: float,
) -> dict[str, Any]:
    total_supplier = _as_float(flight_data.get("TotalPrice"))
    adult_supplier = _as_float(flight_data.get("AdultPrice"), total_supplier)
    child_supplier = _as_float(flight_data.get("ChildPrice"))
    infant_supplier = _as_float(flight_data.get("InfantPrice"))

    adults = int((search_data or {}).get("adult_config") or 1)
    children = int((search_data or {}).get("child_config") or 0)
    infants = int((search_data or {}).get("infant_config") or 0)

    def to_admin(amount: float) -> float:
        return round(amount * conversion_rate, 2)

    total_admin = to_admin(total_supplier)
    tax_admin = round(total_admin * 0.15, 2)
    base_admin = round(total_admin - tax_admin, 2)

    breakup: dict[str, Any] = {}
    if adults > 0:
        per = to_admin(adult_supplier)
        breakup["ADT"] = {
            "PassengerCount": adults,
            "BasePrice": round(per * 0.85, 2),
            "Tax": round(per * 0.15, 2),
            "TotalPrice": per,
            "Penalties": [],
            "BaggageAllowance": [],
        }
    if children > 0 and child_supplier > 0:
        per = to_admin(child_supplier)
        breakup["CHD"] = {
            "PassengerCount": children,
            "BasePrice": round(per * 0.85, 2),
            "Tax": round(per * 0.15, 2),
            "TotalPrice": per,
            "Penalties": [],
            "BaggageAllowance": [],
        }
    if infants > 0 and infant_supplier > 0:
        per = to_admin(infant_supplier)
        breakup["INF"] = {
            "PassengerCount": infants,
            "BasePrice": round(per * 0.85, 2),
            "Tax": round(per * 0.15, 2),
            "TotalPrice": per,
            "Penalties": [],
            "BaggageAllowance": [],
        }

    return {
        "Fare_Type": "Publish",
        "PassengerBreakup": breakup,
        "Currency": admin_currency,
        "currency": admin_currency,
        "currency_conversion_rate": round(conversion_rate, 6),
        "supplier_currency": supplier_currency if supplier_currency != admin_currency else None,
        "TotalDisplayFare": total_admin,
        "PriceBreakup": {
            "Tax": tax_admin,
            "BasicFare": base_admin,
            "AgentCommission": 0,
            "AgentTdsOnCommision": 0,
        },
    }


def validating_airline(flight_data: dict[str, Any]) -> str:
    for offer in offer_infos(flight_data):
        code = str(offer.get("ValidatingAirline") or "").strip().upper()
        if code:
            return code
    for offer in offer_infos(flight_data):
        for seg in segments_from_offer(offer):
            code = str(seg.get("MarketingAirline") or "").strip().upper()
            if code:
                return code
    return ""


def is_lcc(flight_data: dict[str, Any]) -> bool:
    for offer in offer_infos(flight_data):
        for seg in segments_from_offer(offer):
            if _as_bool(seg.get("LowCost")):
                return True
    return False


def flight_data_list(result: dict[str, Any]) -> list[dict[str, Any]]:
    raw = result.get("FlightData")
    if isinstance(raw, dict) and "FlightData" in raw:
        return [x for x in force_list(raw["FlightData"]) if isinstance(x, dict)]
    return [x for x in force_list(raw) if isinstance(x, dict)]
