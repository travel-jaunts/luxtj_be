from dataclasses import dataclass


@dataclass
class UpdatePropertyPartnerDetailsDTO:
    property_name: str
    property_owner_name: str
    property_contact_number: str
    partner_email: str
    property_address: str
    property_amenities: list[str]
    property_description: str
    property_room_types: list[str]
    property_base_price_amount: float
    property_base_price_currency: str
    location_latitude: float
    location_longitude: float
    location_address_line1: str
    location_address_line2: str | None
    location_city: str
    location_state: str
    location_postal_code: str
    location_country: str
