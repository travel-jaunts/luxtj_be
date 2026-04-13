from dataclasses import dataclass


@dataclass
class UpdateAffiliatePartnerDetailsDTO:
    name: str
    website: str
    social_media: str
    contact: str
    affiliate_link: str
    commission_percent: float
