"""City Travel AeroSearch normalize — FlightData → B2C rows + itinerary grouping."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

import airportsdata


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


def extract_aero_prebook_result(parsed: dict[str, Any] | None) -> dict[str, Any]:
    """Unwrap SOAP parse tree or accept a flat AeroPrebookResult-shaped dict."""
    if not isinstance(parsed, dict) or not parsed:
        return {}
    if "FullPrice" in parsed or ("OfferCode" in parsed and "Offers" in parsed):
        return parsed
    if "AeroPrebookResult" in parsed and isinstance(parsed["AeroPrebookResult"], dict):
        return parsed["AeroPrebookResult"]
    body = parsed.get("Body")
    if isinstance(body, dict):
        resp = body.get("AeroPrebookResponse") or body.get("AeroPrebookResult") or {}
        if isinstance(resp, dict):
            if "AeroPrebookResult" in resp and isinstance(resp["AeroPrebookResult"], dict):
                return resp["AeroPrebookResult"]
            if "FullPrice" in resp or "Offers" in resp or "Success" in resp:
                return resp
    return {}


def _unwrap_soap_result(
    parsed: dict[str, Any] | None,
    *,
    response_keys: tuple[str, ...],
    result_keys: tuple[str, ...],
    identity_keys: tuple[str, ...] = (),
) -> dict[str, Any]:
    if not isinstance(parsed, dict) or not parsed:
        return {}
    for key in identity_keys:
        if key in parsed:
            return parsed
    for key in result_keys:
        node = parsed.get(key)
        if isinstance(node, dict):
            return node
    body = parsed.get("Body")
    if isinstance(body, dict):
        for rk in response_keys:
            resp = body.get(rk)
            if isinstance(resp, dict):
                for key in result_keys:
                    node = resp.get(key)
                    if isinstance(node, dict):
                        return node
                if any(k in resp for k in identity_keys):
                    return resp
    return {}


def extract_aero_book_result(parsed: dict[str, Any] | None) -> dict[str, Any]:
    return _unwrap_soap_result(
        parsed,
        response_keys=("AeroBookResponse",),
        result_keys=("AeroBookResult",),
        identity_keys=("BookId", "BookGuid", "Offers", "Success"),
    )


def extract_confirm_book_result(parsed: dict[str, Any] | None) -> dict[str, Any]:
    result = _unwrap_soap_result(
        parsed,
        response_keys=("ConfirmBookResponse",),
        result_keys=("ConfirmBookResult",),
        identity_keys=("OrderInfoData", "Success"),
    )
    if not result:
        return {}
    order = result.get("OrderInfoData")
    if isinstance(order, dict):
        merged = dict(order)
        if "Success" in result:
            merged["Success"] = result.get("Success")
        return merged
    return result


def extract_order_info_result(parsed: dict[str, Any] | None) -> dict[str, Any]:
    result = _unwrap_soap_result(
        parsed,
        response_keys=("OrderInfoResponse",),
        result_keys=("OrderInfoResult",),
        identity_keys=("OrderInfoData", "Success", "BookingStatus"),
    )
    if not result:
        return {}
    order = result.get("OrderInfoData")
    if isinstance(order, dict):
        merged = dict(order)
        if "Success" in result:
            merged["Success"] = result.get("Success")
        return merged
    return result


def extract_annulate_book_result(parsed: dict[str, Any] | None) -> dict[str, Any]:
    return _unwrap_soap_result(
        parsed,
        response_keys=("AnnulateBookResponse",),
        result_keys=("AnnulateBookResult",),
        identity_keys=("Success", "Currency", "ServiceUrl"),
    )


def soap_flag_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes"}


def void_deadline_utc(order: dict[str, Any]) -> datetime | None:
    """Parse DeadLineDateUtc (preferred) or DeadLineDate from OrderInfo/ConfirmBook."""
    raw = str(order.get("DeadLineDateUtc") or order.get("DeadLineDate") or "").strip()
    parsed = parse_ct_datetime(raw)
    if parsed is None:
        return None
    # CT docs treat DeadLineDateUtc as UTC wall clock without offset.
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def first_pnr_from_offers(book_or_order: dict[str, Any]) -> str:
    candidates: list[Any] = []
    offers = book_or_order.get("Offers")
    if isinstance(offers, dict):
        candidates.extend(force_list(offers.get("OfferInfo") or offers.get("Offer") or offers))
    else:
        candidates.extend(force_list(offers))
    gates = book_or_order.get("MultiGatesInfo")
    if isinstance(gates, dict):
        candidates.extend(force_list(gates.get("OfferInfo") or gates))
    else:
        candidates.extend(force_list(gates))
    for offer in candidates:
        if not isinstance(offer, dict):
            continue
        origin = str(offer.get("OriginPnr") or "").strip()
        if origin:
            return origin
        pnr = str(offer.get("PNR") or "").strip()
        if pnr:
            return pnr
    return ""


def ticket_passengers_from_order(order: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize ticket rows from ConfirmBook / OrderInfo MultiGatesInfo."""
    out: list[dict[str, Any]] = []
    gates = order.get("MultiGatesInfo")
    offers = force_list(gates.get("OfferInfo") if isinstance(gates, dict) else gates)
    for offer in offers:
        if not isinstance(offer, dict):
            continue
        pax_node = offer.get("Passengers") or offer.get("OfferPassenger")
        for pax in force_list(
            pax_node.get("OfferPassenger") if isinstance(pax_node, dict) else pax_node
        ):
            if not isinstance(pax, dict):
                continue
            ticket = str(pax.get("TicketNumber") or "").strip()
            if not ticket:
                continue
            out.append(
                {
                    "Guid": str(pax.get("Guid") or "").strip(),
                    "TicketNumber": ticket,
                    "PNR": str(offer.get("OriginPnr") or offer.get("PNR") or "").strip(),
                }
            )
    return out


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except TypeError, ValueError:
        return default


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


@lru_cache(maxsize=1)
def _iata_airports() -> dict[str, dict[str, Any]]:
    return airportsdata.load("IATA")


def iana_timezone_for_iata(iata: str) -> str | None:
    """Resolve IANA TZ for an airport IATA (City Travel dates are local wall times)."""
    code = str(iata or "").strip().upper()
    if not code:
        return None
    row = _iata_airports().get(code)
    if not row:
        return None
    tz = str(row.get("tz") or "").strip()
    return tz or None


def format_utc_offset(delta: timedelta | None) -> str | None:
    if delta is None:
        return None
    total = int(delta.total_seconds())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    hours, rem = divmod(total, 3600)
    minutes = rem // 60
    return f"{sign}{hours:02d}:{minutes:02d}"


def format_airport_local_datetime(naive: datetime | None, iata: str) -> dict[str, str | None]:
    """
    City Travel ``Departure/Arrival/Date`` is already **local airport wall time**
    with no TZ. Look up the airport IANA zone (via IATA → airportsdata) only to
    compute ``UtcOffset`` for that local clock; return separate date / time / offset.
    """
    empty = {"date": None, "time": None, "UtcOffset": None}
    if naive is None:
        return empty

    date_s = naive.strftime("%Y-%m-%d")
    time_s = naive.strftime("%H:%M:%S")
    tz_name = iana_timezone_for_iata(iata)
    if not tz_name:
        return {"date": date_s, "time": time_s, "UtcOffset": None}
    try:
        aware = naive.replace(tzinfo=ZoneInfo(tz_name))
        offset = format_utc_offset(aware.utcoffset())
    except Exception:
        offset = None
    return {"date": date_s, "time": time_s, "UtcOffset": offset}


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


def clean_terminal(value: Any) -> str | None:
    """XML empty ``<Terminal/>`` often parses as ``{}`` — normalize to null."""
    if value is None or value == "" or value == {}:
        return None
    if isinstance(value, dict):
        for key in ("Terminal", "Value", "#text"):
            if key in value:
                return clean_terminal(value.get(key))
        return None
    text = str(value).strip()
    return text or None


def format_baggage(raw: Any) -> str | None:
    """Map City Travel Baggage / CabinBaggage → display string (e.g. ``23 KG``, ``1 PC``, ``0 KG``)."""
    if not isinstance(raw, dict) or not raw:
        return None
    btype = str(raw.get("BaggageType") or "").strip()
    count_raw = raw.get("Count")
    count_n: int | None
    try:
        count_n = int(float(count_raw)) if count_raw not in (None, "") else None
    except TypeError, ValueError:
        count_n = None

    key = btype.lower()
    if key in {"nil", "nilselect", "unknown", ""}:
        # Nil / NilSelect / unknown = no included checked/cabin bag allowance
        return "0 KG"
    if count_n is None:
        return btype or None
    if key == "kilos":
        return f"{count_n} KG"
    if key == "pounds":
        return f"{count_n} LB"
    if key == "pieces":
        return f"{count_n} PC"
    return f"{count_n} {btype}".strip()


def index_airports(result: dict[str, Any]) -> dict[str, dict[str, str]]:
    raw = result.get("AirPorts")
    infos: list[Any]
    if isinstance(raw, dict):
        infos = force_list(raw.get("AirPortInfo") or raw.get("AirPort") or [])
    else:
        infos = force_list(raw)
    out: dict[str, dict[str, str]] = {}
    for info in infos:
        if not isinstance(info, dict):
            continue
        iata = str(info.get("Iata") or "").strip().upper()
        if not iata:
            continue
        out[iata] = {
            "City": str(info.get("City") or "").strip(),
            "Name": str(info.get("Name") or "").strip(),
        }
    return out


def index_airlines(result: dict[str, Any]) -> dict[str, str]:
    raw = result.get("AirCompany")
    values: list[Any]
    if isinstance(raw, dict):
        values = force_list(raw.get("CodeValue") or [])
    else:
        values = force_list(raw)
    out: dict[str, str] = {}
    for item in values:
        if not isinstance(item, dict):
            continue
        code = str(item.get("Code") or "").strip().upper()
        name = str(item.get("Value") or item.get("Name") or "").strip()
        if code and name:
            out[code] = name
    return out


def map_segment(
    seg: dict[str, Any],
    *,
    airports: dict[str, dict[str, str]] | None = None,
    airlines: dict[str, str] | None = None,
) -> dict[str, Any]:
    airports = airports or {}
    airlines = airlines or {}
    dep = seg.get("Departure") if isinstance(seg.get("Departure"), dict) else {}
    arr = seg.get("Arrival") if isinstance(seg.get("Arrival"), dict) else {}
    dep_dt = parse_ct_datetime(str(dep.get("Date") or ""))
    arr_dt = parse_ct_datetime(str(arr.get("Date") or ""))
    marketing = str(seg.get("MarketingAirline") or "").strip().upper()
    operating = str(seg.get("OperatingAirline") or marketing).strip().upper()
    flight_num = str(seg.get("FlightNum") or "").strip()
    number_only = flight_num.split("-", 1)[-1] if "-" in flight_num else flight_num
    dep_iata = str(dep.get("Iata") or "").strip().upper()
    arr_iata = str(arr.get("Iata") or "").strip().upper()
    dep_meta = airports.get(dep_iata) or {}
    arr_meta = airports.get(arr_iata) or {}
    seats_raw = seg.get("ResBookDesigQuantity")
    try:
        seats = int(float(seats_raw)) if seats_raw not in (None, "") else None
    except TypeError, ValueError:
        seats = seats_raw
    aircraft = seg.get("AirCraft")
    aircraft_code = None if str(aircraft or "").strip().upper() in {"", "NA", "N/A"} else aircraft
    minutes = int(_as_float(seg.get("FlightMinutes"), 0))
    dep_when = format_airport_local_datetime(dep_dt, dep_iata)
    arr_when = format_airport_local_datetime(arr_dt, arr_iata)
    return {
        "Origin": {
            "AirportCode": dep_iata,
            "CityName": str(dep.get("City") or "").strip() or dep_meta.get("City") or "",
            "AirportName": str(dep.get("Name") or "").strip() or dep_meta.get("Name") or "",
            "date": dep_when["date"],
            "time": dep_when["time"],
            "UtcOffset": dep_when["UtcOffset"],
            "OriginTerminal": clean_terminal(dep.get("Terminal")),
        },
        "Destination": {
            "AirportCode": arr_iata,
            "CityName": str(arr.get("City") or "").strip() or arr_meta.get("City") or "",
            "AirportName": str(arr.get("Name") or "").strip() or arr_meta.get("Name") or "",
            "date": arr_when["date"],
            "time": arr_when["time"],
            "UtcOffset": arr_when["UtcOffset"],
            "DestinationTerminal": clean_terminal(arr.get("Terminal")),
        },
        "MarketingAirlineCode": marketing or None,
        "MarketingAirlineName": (
            str(seg.get("MarketingAirlineName") or "").strip()
            or ((airlines.get(marketing) or marketing) if marketing else None)
        ),
        "OperatingAirlineCode": operating or None,
        "OperatingAirlineName": (
            str(seg.get("OperatingAirlineName") or "").strip()
            or ((airlines.get(operating) or operating) if operating else None)
        ),
        "FlightNumber": number_only,
        "CabinClass": cabin_label(str(seg.get("FlightClass") or "")),
        "Duration": minutes,
        "AircraftCode": aircraft_code,
        "AvailableSeats": seats,
    }


def build_flight_details(
    flight_data: dict[str, Any],
    *,
    airports: dict[str, dict[str, str]] | None = None,
    airlines: dict[str, str] | None = None,
) -> list[list[dict[str, Any]]]:
    legs: dict[str, list[dict[str, Any]]] = {}
    for offer in offer_infos(flight_data):
        rph = str(offer.get("Rph") or "1")
        legs.setdefault(rph, [])
        for seg in segments_from_offer(offer):
            legs[rph].append(map_segment(seg, airports=airports, airlines=airlines))
    ordered_keys = sorted(legs.keys(), key=lambda k: (0, int(k)) if str(k).isdigit() else (1, k))
    return [legs[k] for k in ordered_keys if legs[k]]


def _tariff_info(flight_data: dict[str, Any]) -> dict[str, Any]:
    raw = flight_data.get("TariffInfo")
    return raw if isinstance(raw, dict) else {}


def build_baggage_allowance(
    flight_data: dict[str, Any],
    *,
    search_data: dict[str, Any] | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Segment OD → pax type → baggage. City Travel search bags are segment-level (same for all pax)."""
    adults = int((search_data or {}).get("adult_config") or 1)
    children = int((search_data or {}).get("child_config") or 0)
    infants = int((search_data or {}).get("infant_config") or 0)
    pax_types = [
        code for code, n in (("ADT", adults), ("CHD", children), ("INF", infants)) if n > 0
    ]
    if not pax_types:
        pax_types = ["ADT"]

    out: dict[str, dict[str, dict[str, Any]]] = {}
    for offer in offer_infos(flight_data):
        for seg in segments_from_offer(offer):
            if not isinstance(seg, dict):
                continue
            dep = seg.get("Departure") if isinstance(seg.get("Departure"), dict) else {}
            arr = seg.get("Arrival") if isinstance(seg.get("Arrival"), dict) else {}
            origin = str(dep.get("Iata") or "").strip().upper()
            dest = str(arr.get("Iata") or "").strip().upper()
            key = f"{origin}-{dest}".strip("-")
            if not key or key == "-":
                continue
            bag = {
                "Baggage": format_baggage(seg.get("Baggage")),
                "CabinBaggage": format_baggage(seg.get("CabinBaggage")),
            }
            out[key] = {pax: dict(bag) for pax in pax_types}
    return out


def build_price_block(
    flight_data: dict[str, Any],
    *,
    search_data: dict[str, Any] | None,
    conversion_rate: float,
) -> dict[str, Any]:
    """Build Price in **admin** amounts. No currency metadata (FE assumes admin currency)."""
    tariff = _tariff_info(flight_data)
    total_supplier = _as_float(flight_data.get("TotalPrice"))
    adult_total = _as_float(
        tariff.get("AdultPrice") or flight_data.get("AdultPrice"), total_supplier
    )
    adult_base = _as_float(tariff.get("AdultBasePrice"))
    child_total = _as_float(tariff.get("ChildPrice") or flight_data.get("ChildPrice"))
    child_base = _as_float(tariff.get("ChildBasePrice"))
    infant_total = _as_float(tariff.get("InfantPrice") or flight_data.get("InfantPrice"))
    infant_base = _as_float(tariff.get("InfantBasePrice"))

    adults = int((search_data or {}).get("adult_config") or 1)
    children = int((search_data or {}).get("child_config") or 0)
    infants = int((search_data or {}).get("infant_config") or 0)

    def to_admin(amount: float) -> float:
        return round(amount * conversion_rate, 2)

    def pax_row(count: int, total_one: float, base_one: float) -> dict[str, Any]:
        total = to_admin(total_one)
        if base_one > 0:
            base = to_admin(base_one)
            tax = round(total - base, 2)
        else:
            # Fallback split only when TariffInfo base is missing
            tax = round(total * 0.15, 2)
            base = round(total - tax, 2)
        return {
            "PassengerCount": count,
            "BasePrice": base,
            "Tax": tax,
            "TotalPrice": total,
            "Penalties": [],
        }

    breakup: dict[str, Any] = {}
    if adults > 0 and adult_total > 0:
        breakup["ADT"] = pax_row(adults, adult_total, adult_base)
    if children > 0 and child_total > 0:
        breakup["CHD"] = pax_row(children, child_total, child_base)
    if infants > 0 and infant_total > 0:
        breakup["INF"] = pax_row(infants, infant_total, infant_base)

    total_admin = to_admin(total_supplier) if total_supplier > 0 else 0.0
    if total_admin <= 0 and breakup:
        total_admin = round(
            sum(float(row["TotalPrice"]) * int(row["PassengerCount"]) for row in breakup.values()),
            2,
        )

    # Prefer TariffInfo bases for BasicFare when present (amounts are totals for that pax type)
    if adult_base > 0:
        base_admin = to_admin(adult_base)
        if child_base > 0 and children > 0:
            base_admin = round(base_admin + to_admin(child_base), 2)
        if infant_base > 0 and infants > 0:
            base_admin = round(base_admin + to_admin(infant_base), 2)
        tax_admin = round(total_admin - base_admin, 2)
    else:
        tax_admin = round(total_admin * 0.15, 2)
        base_admin = round(total_admin - tax_admin, 2)

    return {
        "Fare_Type": "Publish",
        "PassengerBreakup": breakup,
        "TotalDisplayFare": total_admin,
        "PriceBreakup": {
            "Tax": tax_admin,
            "BasicFare": base_admin,
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


def flight_data_list(result: dict[str, Any]) -> list[dict[str, Any]]:
    raw = result.get("FlightData")
    if isinstance(raw, dict) and "FlightData" in raw:
        return [x for x in force_list(raw["FlightData"]) if isinstance(x, dict)]
    return [x for x in force_list(raw) if isinstance(x, dict)]


def prebook_supplier_total(prebook: dict[str, Any]) -> float:
    """Prefer FullPrice; else first PaymentPrice amount."""
    full = _as_float(prebook.get("FullPrice"))
    if full > 0:
        return full
    raw = prebook.get("PaymentPrices")
    items: list[Any]
    if isinstance(raw, dict):
        items = force_list(raw.get("PaymentPrice") or [])
    else:
        items = force_list(raw)
    for item in items:
        if not isinstance(item, dict):
            continue
        price = _as_float(item.get("Price"))
        if price > 0:
            return price
    return 0.0


def build_price_block_from_total(
    total_supplier: float,
    *,
    search_data: dict[str, Any] | None,
    conversion_rate: float,
    prior_price: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Admin Price from locked prebook total; scale prior breakup when available."""
    total_admin = round(float(total_supplier) * conversion_rate, 2)
    prior = prior_price if isinstance(prior_price, dict) else {}
    prior_total = _as_float(prior.get("TotalDisplayFare"))
    prior_breakup = (
        prior.get("PassengerBreakup") if isinstance(prior.get("PassengerBreakup"), dict) else {}
    )

    if prior_total > 0 and prior_breakup and total_admin > 0:
        scale = total_admin / prior_total
        breakup: dict[str, Any] = {}
        for code, row in prior_breakup.items():
            if not isinstance(row, dict):
                continue
            breakup[code] = {
                "PassengerCount": int(row.get("PassengerCount") or 0),
                "BasePrice": round(_as_float(row.get("BasePrice")) * scale, 2),
                "Tax": round(_as_float(row.get("Tax")) * scale, 2),
                "TotalPrice": round(_as_float(row.get("TotalPrice")) * scale, 2),
                "Penalties": list(row.get("Penalties") or []),
            }
        prior_pb = prior.get("PriceBreakup") if isinstance(prior.get("PriceBreakup"), dict) else {}
        base_admin = round(_as_float(prior_pb.get("BasicFare")) * scale, 2)
        tax_admin = round(total_admin - base_admin, 2)
        return {
            "Fare_Type": prior.get("Fare_Type") or "Publish",
            "PassengerBreakup": breakup,
            "TotalDisplayFare": total_admin,
            "PriceBreakup": {"Tax": tax_admin, "BasicFare": base_admin},
        }

    adults = int((search_data or {}).get("adult_config") or 1)
    tax_admin = round(total_admin * 0.15, 2)
    base_admin = round(total_admin - tax_admin, 2)
    per_total = round(total_admin / max(adults, 1), 2)
    per_base = round(base_admin / max(adults, 1), 2)
    per_tax = round(per_total - per_base, 2)
    return {
        "Fare_Type": "Publish",
        "PassengerBreakup": {
            "ADT": {
                "PassengerCount": adults,
                "BasePrice": per_base,
                "Tax": per_tax,
                "TotalPrice": per_total,
                "Penalties": [],
            }
        },
        "TotalDisplayFare": total_admin,
        "PriceBreakup": {"Tax": tax_admin, "BasicFare": base_admin},
    }


def service_info_list(container: Any) -> list[dict[str, Any]]:
    """Normalize Tariffs / Services wrappers → list of ServiceInfo dicts."""
    if container is None:
        return []
    if isinstance(container, dict):
        inner = container.get("ServiceInfo") or container.get("Service") or container
        return [x for x in force_list(inner) if isinstance(x, dict)]
    return [x for x in force_list(container) if isinstance(x, dict)]


def as_bool_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _service_markup_price(service: dict[str, Any]) -> float:
    direct = _as_float(service.get("Price"))
    if direct > 0 or "Price" in service:
        return direct
    raw = service.get("PaymentPriceMarkupData")
    items: list[Any]
    if isinstance(raw, dict):
        items = force_list(raw.get("PaymentPriceMarkup") or raw.get("PaymentPrice") or [])
    else:
        items = force_list(raw)
    for item in items:
        if isinstance(item, dict):
            price = _as_float(item.get("Price"))
            if price > 0:
                return price
    return 0.0


def _classify_service_type(raw_type: str) -> str:
    key = str(raw_type or "").strip().lower()
    if not key:
        return "other"
    if "bag" in key or "luggage" in key:
        return "baggage"
    if "meal" in key or "food" in key:
        return "meal"
    if key in {"checkin", "check-in", "seat", "seats"} or "seat" in key:
        return "seat"
    return "other"


def _route_metas_from_flight_details(
    flight_details: list[list[dict[str, Any]]],
) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    for journey in flight_details:
        if not isinstance(journey, list) or not journey:
            continue
        first = journey[0] if isinstance(journey[0], dict) else {}
        last = journey[-1] if isinstance(journey[-1], dict) else first
        origin = ""
        dest = ""
        if isinstance(first.get("Origin"), dict):
            origin = str(first["Origin"].get("AirportCode") or "").upper()
        if isinstance(last.get("Destination"), dict):
            dest = str(last["Destination"].get("AirportCode") or "").upper()
        routes.append({"origin": origin, "destination": dest})
    return routes


def format_extra_services_for_api(
    services: list[dict[str, Any]],
    *,
    flight_details: list[list[dict[str, Any]]],
    conversion_rate: float,
    admin_currency: str,
) -> dict[str, Any]:
    """Map City Travel AeroPrebook ``Services`` → Mystifly-like ExtraServiceDetails."""
    routes = _route_metas_from_flight_details(flight_details)
    route_count = max(1, len(routes))
    meals: list[list[dict[str, Any]]] = [[] for _ in range(route_count)]
    baggage: list[list[dict[str, Any]]] = [[] for _ in range(route_count)]
    seats: list[list[dict[str, Any]]] = [[] for _ in range(route_count)]
    other: list[dict[str, Any]] = []

    for service in services:
        if not isinstance(service, dict):
            continue
        service_id = str(service.get("Id") or "").strip()
        if not service_id:
            continue
        bucket = _classify_service_type(str(service.get("Type") or ""))
        supplier_price = _service_markup_price(service)
        admin_price = round(supplier_price * conversion_rate, 2)
        name = str(service.get("Name") or "").strip()
        text = str(service.get("Text") or "").strip()
        description = name or text or str(service.get("Type") or "Service")
        rph_raw = service.get("Rph")
        route_indexes: list[int]
        try:
            rph_n = int(float(rph_raw)) if rph_raw not in (None, "") else None
        except TypeError, ValueError:
            rph_n = None
        if rph_n is not None and rph_n >= 1:
            idx = min(rph_n - 1, route_count - 1)
            route_indexes = [idx]
        elif bucket == "other":
            route_indexes = []
        else:
            route_indexes = list(range(route_count))

        def _option(route_index: int | None) -> dict[str, Any]:
            meta = (
                routes[route_index]
                if route_index is not None and route_index < len(routes)
                else {
                    "origin": "",
                    "destination": "",
                }
            )
            prefix = {"meal": "ml", "baggage": "bg", "seat": "st"}.get(bucket, "ot")
            ri = route_index if route_index is not None else 0
            option_id = f"{prefix}_{ri}_{service_id}"
            blob = [
                {
                    "Type": "citytravel",
                    "ServiceId": service_id,
                    "Price": admin_price,
                    "SupplierAmount": supplier_price,
                    "routeIndex": ri,
                    "optionId": option_id,
                    "description": description,
                    "serviceType": str(service.get("Type") or ""),
                    "origin": meta.get("origin") or "",
                    "destination": meta.get("destination") or "",
                }
            ]
            encoded = base64.b64encode(json.dumps(blob, separators=(",", ":")).encode()).decode()
            option: dict[str, Any] = {
                "OptionId": option_id,
                "Description": description,
                "Price": admin_price,
                "Currency": admin_currency,
                "origin": meta.get("origin") or "",
                "destination": meta.get("destination") or "",
                "ServiceId": service_id,
                "ssrCode": service_id,
                "Type": str(service.get("Type") or ""),
            }
            if text and text != description:
                option["Text"] = text
            if bucket == "meal":
                option["MealKey"] = encoded
            elif bucket == "baggage":
                option["BaggageKey"] = encoded
            elif bucket == "seat":
                option["SeatKey"] = encoded
            else:
                option["ServiceKey"] = encoded
            return option

        if bucket == "other" or not route_indexes:
            other.append(_option(None))
            continue
        for ri in route_indexes:
            option = _option(ri)
            if bucket == "meal":
                meals[ri].append(option)
            elif bucket == "baggage":
                baggage[ri].append(option)
            elif bucket == "seat":
                seats[ri].append(option)
            else:
                other.append(option)

    return {
        "Meals": meals,
        "Baggage": baggage,
        "Seat": seats,
        "Other": other,
    }
