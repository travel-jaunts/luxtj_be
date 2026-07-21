from enum import StrEnum


class CalendarSourceType(StrEnum):
    EVENT = "event"
    PERIOD = "period"


class PlanType(StrEnum):
    HOTEL_FLIGHT = "hotel_flight"
    HOTEL = "hotel"
    VILLA = "villa"
    TRAIN = "train"
    CRUISE = "cruise"
    ACTIVITY = "activity"
    LUXURY_INDULGENCE = "luxury_indulgence"


class DealTier(StrEnum):
    LITE = "Lite"
    PLUS = "Plus"
    ULTRA = "Ultra"


class TravelerType(StrEnum):
    SOLO = "solo"
    COUPLE = "couple"
    FAMILY = "family"
    MULTI_GENERATIONAL = "multi_gen"
    FRIENDS = "friends"


class RecommendationStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class CancellationPolicy(StrEnum):
    NON_REFUNDABLE = "non_refundable"
    STRICT = "strict"
    PARTIAL = "partial"
    FLEXIBLE = "flexible"
    FREE_CANCELLATION = "free_cancellation"
    REFUNDABLE = "refundable"
    UNKNOWN = "unknown"


class TravelAdvisory(StrEnum):
    NORMAL = "normal"
    CAUTION = "caution"
    SERIOUS = "serious"
    DO_NOT_TRAVEL = "do_not_travel"
    UNKNOWN = "unknown"


class NewsRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SEVERE = "severe"
    UNKNOWN = "unknown"


class PhysicalIntensity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class LogisticsComplexity(StrEnum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    UNKNOWN = "unknown"


class WalkingLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class SeasonType(StrEnum):
    SHOULDER = "shoulder"
    BEST = "best"
    PEAK = "peak"
    AVOID = "avoid"
    STANDARD = "standard"
    UNKNOWN = "unknown"


class CrowdLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class LocationScope(StrEnum):
    LOCAL = "local"
    WITHIN_COUNTRY = "within_country"
    OUTSIDE_COUNTRY = "outside_country"


class UnknownReviewPolicy(StrEnum):
    ALLOW_WITH_PENALTY = "allow_with_penalty"
    REJECT = "reject"


class RankingMode(StrEnum):
    HEURISTIC = "heuristic"
    HYBRID = "hybrid"
    ML = "ml"


class RejectionReason(StrEnum):
    WRONG_PLAN_TYPE = "wrong_plan_type"
    WRONG_TIER = "wrong_tier"
    TRAVEL_IN_PAST = "travel_in_past"
    DATE_MISMATCH = "date_mismatch"
    DURATION_MISMATCH = "duration_mismatch"
    QUALITY_BELOW_TIER = "quality_below_tier"
    REVIEW_COUNT_BELOW_TIER = "review_count_below_tier"
    REVIEW_COUNT_UNKNOWN = "review_count_unknown"
    ORIGIN_MISMATCH = "origin_mismatch"
    INCOMPLETE_PACKAGE = "incomplete_package"
    CURRENCY_MISMATCH = "currency_mismatch"
    BUDGET_EXCEEDED = "budget_exceeded"
    OCCUPANCY_UNSUPPORTED = "occupancy_unsupported"
    VISA_PROCESSING_IMPOSSIBLE = "visa_processing_impossible"
    SERIOUS_TRAVEL_ADVISORY = "serious_travel_advisory"
    SEVERE_REALTIME_RISK = "severe_realtime_risk"
    FAMILY_SUITABILITY_CONFLICT = "family_suitability_conflict"
    CHILD_TRIP_NOT_FAMILY_SUITABLE = "child_trip_not_family_suitable"
    CHILD_TRIP_TOO_SHORT = "child_trip_too_short"
    COUPLE_ONLY_PRODUCT = "couple_only_product"
    LOCAL_ONLY_PRODUCT = "local_only_product"
    MINIMUM_STAY_NOT_MET = "minimum_stay_not_met"
    MOBILITY_INTENSITY_CONFLICT = "mobility_intensity_conflict"
    INACCESSIBLE_PRODUCT = "inaccessible_product"
    COMPLEX_LOGISTICS = "complex_logistics"
    REJECTED_DESTINATION = "rejected_destination"
    SUPPLIER_COMPLAINT_RATIO_HIGH = "supplier_complaint_ratio_high"
    SUPPLIER_RELIABILITY_LOW = "supplier_reliability_low"
    REFUND_FREQUENCY_HIGH = "refund_frequency_high"
    INVALID_PRICE = "invalid_price"
    PROVIDER_ERROR = "provider_error"
    NO_CANDIDATES = "no_candidates"
    NO_VALID_CANDIDATES = "no_valid_candidates"
