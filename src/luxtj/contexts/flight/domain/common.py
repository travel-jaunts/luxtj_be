"""Flight common helpers — tokens, cabin normalize, search validation."""

from __future__ import annotations

import base64
import json
import re
import secrets
import time
import uuid
from typing import Any


class FlightCommon:
    """Shared helpers for flight providers and blender."""

    @staticmethod
    def encode_result_token(booking_source: str, token: str) -> str:
        payload = {
            "booking_source": booking_source,
            "token": token,
            "time": int(time.time()),
        }
        return base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()

    @staticmethod
    def decode_result_token(encoded: str) -> dict[str, Any] | None:
        try:
            raw = base64.b64decode(encoded.encode()).decode()
            data = json.loads(raw)
            if isinstance(data, dict) and "booking_source" in data and "token" in data:
                return data
        except Exception:
            return None
        return None

    @staticmethod
    def generate_uuid(prefix: str = "", random_length: int = 16) -> str:
        time_part = f"{time.time():.6f}".replace(".", "")
        random_part = secrets.token_hex(random_length)
        return f"{prefix}{time_part}{random_part}"

    @staticmethod
    def generate_app_reference() -> str:
        return "FLT" + uuid.uuid4().hex[:16].upper()

    @staticmethod
    def normalize_cabin_class(raw: str) -> str:
        key = re.sub(r"[\s_]+", "", (raw or "").strip().lower())
        return {
            "premiumeconomy": "PremiumEconomy",
            "business": "Business",
            "premiumbusiness": "PremiumBusiness",
            "premiumbusines": "PremiumBusiness",
            "first": "First",
            "econom": "Economy",
            "economy": "Economy",
            "all": "Economy",
        }.get(key, "Economy")

    @staticmethod
    def normalize_trip_type(raw: str) -> str:
        key = (raw or "oneway").strip().lower().replace(" ", "").replace("_", "")
        if key in {"return", "roundtrip", "round", "rt"}:
            return "return"
        if key in {"multicity", "multi", "mc"}:
            return "multicity"
        return "oneway"

    @staticmethod
    def normalize_iata(code: Any) -> str:
        return str(code or "").strip().upper()

    @classmethod
    def normalize_search_request(cls, body: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        """
        Normalize B2C PreSearch body → internal search_data.

        Accepts either architecture-style ``JourneyType`` / ``Segments`` or a
        flatter ``trip_type`` / ``from`` / ``to`` / ``departure`` payload.
        """
        journey = cls.normalize_trip_type(
            str(body.get("JourneyType") or body.get("trip_type") or "oneway")
        )
        cabin = cls.normalize_cabin_class(
            str(body.get("CabinClass") or body.get("cabin_class") or "Economy")
        )
        adults = int(body.get("AdultCount") or body.get("adult_config") or body.get("adults") or 0)
        children = int(body.get("ChildCount") or body.get("child_config") or body.get("children") or 0)
        infants = int(body.get("InfantCount") or body.get("infant_config") or body.get("infants") or 0)

        if adults < 1 or adults > 9:
            return None, "AdultCount must be between 1 and 9"
        if children < 0 or children > 9:
            return None, "ChildCount must be between 0 and 9"
        if infants < 0 or infants > adults:
            return None, "InfantCount cannot exceed AdultCount"
        if adults + children > 9:
            return None, "Adults + children cannot exceed 9"

        segments_raw = body.get("Segments") or body.get("segments")
        clean: dict[str, Any] = {
            "trip_type": journey,
            "cabin_class": cabin,
            "adult_config": adults,
            "child_config": children,
            "infant_config": infants,
            "is_domestic": bool(body.get("IsDomestic") or body.get("is_domestic") or False),
        }

        if isinstance(segments_raw, list) and segments_raw:
            if journey == "multicity":
                origins = [cls.normalize_iata(s.get("Origin") or s.get("from")) for s in segments_raw]
                dests = [
                    cls.normalize_iata(s.get("Destination") or s.get("to")) for s in segments_raw
                ]
                deps = []
                for s in segments_raw:
                    d = str(s.get("DepartureDate") or s.get("departure") or s.get("date") or "")
                    deps.append(d.split("T")[0] if d else "")
                if any(not o or not t or not d for o, t, d in zip(origins, dests, deps, strict=False)):
                    return None, "Each multi-city segment requires Origin, Destination, DepartureDate"
                clean["from"] = origins
                clean["to"] = dests
                clean["depature"] = deps
                clean["segments"] = [
                    {"origin": o, "destination": t, "departure_date": d}
                    for o, t, d in zip(origins, dests, deps, strict=False)
                ]
            else:
                seg = segments_raw[0] if isinstance(segments_raw[0], dict) else {}
                origin = cls.normalize_iata(seg.get("Origin") or seg.get("from") or body.get("from"))
                dest = cls.normalize_iata(
                    seg.get("Destination") or seg.get("to") or body.get("to")
                )
                dep = str(
                    seg.get("DepartureDate")
                    or seg.get("departure")
                    or body.get("departure")
                    or body.get("depature")
                    or ""
                ).split("T")[0]
                if not origin or not dest or not dep:
                    return None, "Origin, Destination and DepartureDate are required"
                clean["from"] = origin
                clean["to"] = dest
                clean["depature"] = dep
                if journey == "return":
                    ret = str(
                        seg.get("ReturnDate")
                        or body.get("return")
                        or body.get("return_date")
                        or ""
                    ).split("T")[0]
                    if not ret:
                        return None, "ReturnDate is required for round-trip"
                    clean["return"] = ret
        else:
            origin = cls.normalize_iata(body.get("from") or body.get("Origin"))
            dest = cls.normalize_iata(body.get("to") or body.get("Destination"))
            dep = str(
                body.get("departure") or body.get("depature") or body.get("DepartureDate") or ""
            ).split("T")[0]
            if not origin or not dest or not dep:
                return None, "from, to and departure are required"
            clean["from"] = origin
            clean["to"] = dest
            clean["depature"] = dep
            if journey == "return":
                ret = str(body.get("return") or body.get("return_date") or body.get("ReturnDate") or "")
                ret = ret.split("T")[0]
                if not ret:
                    return None, "return date is required for round-trip"
                clean["return"] = ret
            if journey == "multicity":
                return None, "Segments are required for multi-city"

        return clean, None
