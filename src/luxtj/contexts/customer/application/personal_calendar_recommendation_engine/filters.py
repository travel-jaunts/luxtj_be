from .config import EngineConfig
from .enums import (
    LocationScope,
    LogisticsComplexity,
    NewsRisk,
    PhysicalIntensity,
    PlanType,
    RejectionReason,
    TravelAdvisory,
    TravelerType,
    UnknownReviewPolicy,
)
from .models import DealCandidate, DealSearchRequest, FilterDecision
from .taxonomy import normalize_text, normalized_set


def location_scope(candidate: DealCandidate, request: DealSearchRequest) -> LocationScope:
    origin_city = normalize_text(request.origin_city)
    origin_country = normalize_text(request.origin_country)
    if origin_city and origin_city in {
        normalize_text(candidate.city),
        normalize_text(candidate.destination),
    }:
        return LocationScope.LOCAL
    if origin_country and origin_country == normalize_text(candidate.country):
        return LocationScope.WITHIN_COUNTRY
    return LocationScope.OUTSIDE_COUNTRY


def _minimum_nights(plan_type: PlanType, scope: LocationScope) -> int:
    if plan_type in {PlanType.HOTEL, PlanType.HOTEL_FLIGHT}:
        return 2 if scope is LocationScope.LOCAL else 3
    if plan_type is PlanType.VILLA:
        return {
            LocationScope.LOCAL: 2,
            LocationScope.WITHIN_COUNTRY: 3,
            LocationScope.OUTSIDE_COUNTRY: 4,
        }[scope]
    if plan_type in {PlanType.TRAIN, PlanType.CRUISE}:
        return {
            LocationScope.LOCAL: 0,
            LocationScope.WITHIN_COUNTRY: 2,
            LocationScope.OUTSIDE_COUNTRY: 3,
        }[scope]
    if plan_type is PlanType.ACTIVITY:
        return 0 if scope is LocationScope.LOCAL else 2
    return 0


def _traveler_suitability_reasons(
    candidate: DealCandidate,
    request: DealSearchRequest,
) -> list[RejectionReason]:
    reasons: list[RejectionReason] = []
    suited_for = set(candidate.suited_for)
    traveler_type = request.travel_party.traveler_type
    if suited_for:
        if traveler_type is TravelerType.MULTI_GENERATIONAL:
            if not suited_for.intersection({TravelerType.FAMILY, TravelerType.MULTI_GENERATIONAL}):
                reasons.append(RejectionReason.FAMILY_SUITABILITY_CONFLICT)
        elif traveler_type not in suited_for:
            reasons.append(RejectionReason.FAMILY_SUITABILITY_CONFLICT)

    if request.requires_family_suitability or request.travel_party.children:
        if TravelerType.FAMILY not in suited_for and not candidate.family_friendly:
            reasons.append(RejectionReason.CHILD_TRIP_NOT_FAMILY_SUITABLE)
        if candidate.duration_nights < 5 and request.source_type.value == "period":
            reasons.append(RejectionReason.CHILD_TRIP_TOO_SHORT)

    if request.plan_type is PlanType.LUXURY_INDULGENCE and traveler_type is not TravelerType.COUPLE:
        reasons.append(RejectionReason.COUPLE_ONLY_PRODUCT)

    return reasons


def _occupancy_reasons(
    candidate: DealCandidate,
    request: DealSearchRequest,
) -> list[RejectionReason]:
    if (
        candidate.maximum_travelers is not None
        and candidate.maximum_travelers < request.travel_party.total_travelers
    ):
        return [RejectionReason.OCCUPANCY_UNSUPPORTED]
    if (
        candidate.rooms_included is not None
        and candidate.rooms_included < request.travel_party.rooms
    ):
        return [RejectionReason.OCCUPANCY_UNSUPPORTED]
    return []


def validate_candidate(
    candidate: DealCandidate,
    request: DealSearchRequest,
    config: EngineConfig,
) -> FilterDecision:
    reasons: list[RejectionReason] = []

    if candidate.plan_type is not request.plan_type:
        reasons.append(RejectionReason.WRONG_PLAN_TYPE)
    if candidate.tier is not request.tier:
        reasons.append(RejectionReason.WRONG_TIER)
    if candidate.start_date < request.reference_date:
        reasons.append(RejectionReason.TRAVEL_IN_PAST)
    if candidate.total_price <= 0:
        reasons.append(RejectionReason.INVALID_PRICE)
    if candidate.currency != request.pricing_currency:
        reasons.append(RejectionReason.CURRENCY_MISMATCH)
    if (
        request.budget is not None
        and request.budget.maximum_total is not None
        and candidate.total_price > request.budget.maximum_total
    ):
        reasons.append(RejectionReason.BUDGET_EXCEEDED)

    if request.plan_type in {PlanType.ACTIVITY, PlanType.LUXURY_INDULGENCE}:
        if not (
            request.window.start_date <= candidate.start_date <= request.window.end_date
            and candidate.end_date <= request.window.end_date
        ):
            reasons.append(RejectionReason.DATE_MISMATCH)
    else:
        if candidate.start_date != request.window.start_date:
            reasons.append(RejectionReason.DATE_MISMATCH)
        if candidate.start_date < request.allowed_start:
            reasons.append(RejectionReason.DATE_MISMATCH)
        if candidate.end_date > request.allowed_end:
            reasons.append(RejectionReason.DATE_MISMATCH)
        duration_delta = abs(candidate.duration_nights - request.window.nights)
        if duration_delta > config.duration_tolerance_nights:
            reasons.append(RejectionReason.DURATION_MISMATCH)

    quality_threshold = config.quality_threshold(request.tier)
    if candidate.quality_rating < quality_threshold:
        reasons.append(RejectionReason.QUALITY_BELOW_TIER)
    review_threshold = config.review_count_threshold(request.tier)
    if candidate.review_count is None:
        if config.unknown_review_policy is UnknownReviewPolicy.REJECT:
            reasons.append(RejectionReason.REVIEW_COUNT_UNKNOWN)
    elif candidate.review_count < review_threshold:
        reasons.append(RejectionReason.REVIEW_COUNT_BELOW_TIER)

    if request.plan_type is PlanType.HOTEL_FLIGHT:
        if candidate.origin_city and normalize_text(candidate.origin_city) != normalize_text(
            request.origin_city
        ):
            reasons.append(RejectionReason.ORIGIN_MISMATCH)
        if not candidate.package_components_complete:
            reasons.append(RejectionReason.INCOMPLETE_PACKAGE)

    reasons.extend(_occupancy_reasons(candidate, request))

    scope = location_scope(candidate, request)
    if request.plan_type is PlanType.LUXURY_INDULGENCE and scope is not LocationScope.LOCAL:
        reasons.append(RejectionReason.LOCAL_ONLY_PRODUCT)
    if request.window.nights < _minimum_nights(request.plan_type, scope):
        reasons.append(RejectionReason.MINIMUM_STAY_NOT_MET)

    lead_days = max((candidate.start_date - request.reference_date).days, 0)
    if (
        scope is LocationScope.OUTSIDE_COUNTRY
        and candidate.visa_processing_days is not None
        and candidate.visa_processing_days > lead_days
    ):
        reasons.append(RejectionReason.VISA_PROCESSING_IMPOSSIBLE)
    if candidate.travel_advisory in {
        TravelAdvisory.SERIOUS,
        TravelAdvisory.DO_NOT_TRAVEL,
    }:
        reasons.append(RejectionReason.SERIOUS_TRAVEL_ADVISORY)
    if candidate.news_risk is NewsRisk.SEVERE:
        reasons.append(RejectionReason.SEVERE_REALTIME_RISK)

    reasons.extend(_traveler_suitability_reasons(candidate, request))

    if request.travel_party.mobility_sensitive:
        if candidate.physical_intensity is PhysicalIntensity.HIGH:
            reasons.append(RejectionReason.MOBILITY_INTENSITY_CONFLICT)
        if candidate.accessibility is False:
            reasons.append(RejectionReason.INACCESSIBLE_PRODUCT)
        if candidate.logistics_complexity is LogisticsComplexity.COMPLEX:
            reasons.append(RejectionReason.COMPLEX_LOGISTICS)

    rejected = normalized_set(request.history.rejected_destinations)
    if (
        normalize_text(candidate.destination) in rejected
        or normalize_text(candidate.country) in rejected
    ):
        reasons.append(RejectionReason.REJECTED_DESTINATION)

    if candidate.supplier_complaint_ratio is not None and candidate.supplier_complaint_ratio > 0.25:
        reasons.append(RejectionReason.SUPPLIER_COMPLAINT_RATIO_HIGH)
    if candidate.supplier_reliability is not None and candidate.supplier_reliability < 0.75:
        reasons.append(RejectionReason.SUPPLIER_RELIABILITY_LOW)
    if candidate.refund_frequency is not None and candidate.refund_frequency > 0.25:
        reasons.append(RejectionReason.REFUND_FREQUENCY_HIGH)

    return FilterDecision(
        accepted=not reasons,
        reason_codes=tuple(dict.fromkeys(reasons)),
    )
