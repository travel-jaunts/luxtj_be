from decimal import Decimal
from math import log1p
from statistics import median

from .config import FEATURE_SCHEMA_VERSION, EngineConfig
from .enums import (
    CancellationPolicy,
    CrowdLevel,
    LogisticsComplexity,
    NewsRisk,
    PhysicalIntensity,
    SeasonType,
    TravelAdvisory,
    TravelerType,
    WalkingLevel,
)
from .models import (
    BusinessScoreBreakdown,
    CandidatePoolStatistics,
    DealCandidate,
    DealSearchRequest,
    FeatureVector,
)
from .taxonomy import (
    holiday_type_match_score,
    normalize_text,
    normalized_set,
    phrase_overlap_score,
)

FEATURE_NAMES: tuple[str, ...] = (
    "date_match",
    "duration_match",
    "holiday_type_match",
    "interest_match",
    "occasion_label_match",
    "traveler_fit",
    "family_fit",
    "mobility_fit",
    "quality_rating",
    "review_confidence",
    "cancellation_flexibility",
    "supplier_reliability",
    "supplier_complaint_health",
    "refund_health",
    "relative_price_value",
    "quality_adjusted_value",
    "budget_fit",
    "market_discount",
    "value_additions",
    "seasonality",
    "crowd_preference",
    "safety",
    "visa_feasibility",
    "logistics_ease",
    "wishlist_match",
    "liked_destination",
    "preferred_product_match",
    "conversion_signal",
    "booking_popularity",
    "novelty",
    "missing_review_count",
    "missing_supplier_signal",
    "missing_market_reference_price",
)


def _bounded(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def _neutral(value: float | None, neutral: float = 0.5) -> float:
    return neutral if value is None else _bounded(value)


def build_pool_statistics(candidates: tuple[DealCandidate, ...]) -> CandidatePoolStatistics:
    if not candidates:
        raise ValueError("At least one candidate is required to build pool statistics")
    currencies = {candidate.currency for candidate in candidates}
    if len(currencies) != 1:
        raise ValueError("Candidate pool must contain a single normalized currency")
    prices = sorted(candidate.total_price for candidate in candidates)
    quality_adjusted = sorted(
        candidate.total_price / Decimal(str(max(candidate.quality_rating, 0.1)))
        for candidate in candidates
    )
    return CandidatePoolStatistics(
        currency=currencies.pop(),
        candidate_count=len(candidates),
        minimum_price=prices[0],
        median_price=Decimal(str(median(prices))),
        maximum_price=prices[-1],
        median_quality_adjusted_price=Decimal(str(median(quality_adjusted))),
    )


def _relative_price_value(
    candidate: DealCandidate,
    pool: CandidatePoolStatistics,
) -> float:
    if pool.maximum_price == pool.minimum_price:
        return 0.75
    position = float(
        (candidate.total_price - pool.minimum_price) / (pool.maximum_price - pool.minimum_price)
    )
    return _bounded(1.0 - position)


def _quality_adjusted_value(
    candidate: DealCandidate,
    pool: CandidatePoolStatistics,
) -> float:
    candidate_ratio = candidate.total_price / Decimal(str(max(candidate.quality_rating, 0.1)))
    if candidate_ratio <= 0:
        return 0.0
    ratio = float(pool.median_quality_adjusted_price / candidate_ratio)
    return _bounded(0.5 + (ratio - 1.0) * 0.5)


def _budget_fit(candidate: DealCandidate, request: DealSearchRequest) -> float:
    budget = request.budget
    if budget is None:
        return 0.65
    if budget.maximum_total is not None and candidate.total_price > budget.maximum_total:
        return 0.0
    if budget.target_total is not None:
        if candidate.total_price <= budget.target_total:
            return 1.0
        upper = budget.maximum_total or budget.target_total * Decimal("1.5")
        span = max(upper - budget.target_total, Decimal("1"))
        return _bounded(1.0 - float((candidate.total_price - budget.target_total) / span))
    if budget.maximum_total is not None:
        return _bounded(1.0 - 0.35 * float(candidate.total_price / budget.maximum_total))
    return 0.65


def _market_discount(candidate: DealCandidate) -> float:
    reference = candidate.market_reference_price
    if reference is None:
        return 0.5
    discount = float((reference - candidate.total_price) / reference)
    return _bounded(0.5 + discount)


def _date_match(candidate: DealCandidate, request: DealSearchRequest) -> float:
    if candidate.start_date == request.window.start_date:
        return 1.0
    delta = abs((candidate.start_date - request.window.start_date).days)
    return _bounded(1.0 - delta / max(request.window.nights, 1))


def _duration_match(candidate: DealCandidate, request: DealSearchRequest) -> float:
    delta = abs(candidate.duration_nights - request.window.nights)
    return _bounded(1.0 - delta / max(request.window.nights, 1))


def _review_confidence(
    candidate: DealCandidate,
    request: DealSearchRequest,
    config: EngineConfig,
) -> float:
    if candidate.review_count is None:
        return config.unknown_review_confidence
    threshold = config.review_count_threshold(request.tier)
    scale = max(threshold * 5, 1)
    return _bounded(log1p(candidate.review_count) / log1p(scale))


def _cancellation(candidate: DealCandidate) -> float:
    return {
        CancellationPolicy.NON_REFUNDABLE: 0.20,
        CancellationPolicy.STRICT: 0.40,
        CancellationPolicy.PARTIAL: 0.65,
        CancellationPolicy.FLEXIBLE: 0.90,
        CancellationPolicy.FREE_CANCELLATION: 1.00,
        CancellationPolicy.REFUNDABLE: 0.95,
        CancellationPolicy.UNKNOWN: 0.50,
    }[candidate.cancellation_policy]


def _traveler_fit(candidate: DealCandidate, request: DealSearchRequest) -> float:
    suited = set(candidate.suited_for)
    traveler_type = request.travel_party.traveler_type
    if not suited:
        return 0.65
    if traveler_type in suited:
        return 1.0
    if traveler_type is TravelerType.MULTI_GENERATIONAL and suited.intersection(
        {TravelerType.FAMILY, TravelerType.MULTI_GENERATIONAL}
    ):
        return 0.95
    return 0.25


def _family_fit(candidate: DealCandidate, request: DealSearchRequest) -> float:
    family_required = request.requires_family_suitability or bool(request.travel_party.children)
    if not family_required:
        return 0.75
    if candidate.family_friendly or TravelerType.FAMILY in candidate.suited_for:
        return 1.0
    return 0.0


def _mobility_fit(candidate: DealCandidate, request: DealSearchRequest) -> float:
    if not request.travel_party.mobility_sensitive:
        return 0.80
    score = 1.0
    if candidate.accessibility is None:
        score -= 0.15
    elif not candidate.accessibility:
        return 0.0
    if candidate.physical_intensity is PhysicalIntensity.MEDIUM:
        score -= 0.20
    elif candidate.physical_intensity is PhysicalIntensity.HIGH:
        return 0.0
    elif candidate.physical_intensity is PhysicalIntensity.UNKNOWN:
        score -= 0.10
    if candidate.walking_level is WalkingLevel.MEDIUM:
        score -= 0.15
    elif candidate.walking_level is WalkingLevel.HIGH:
        score -= 0.35
    elif candidate.walking_level is WalkingLevel.UNKNOWN:
        score -= 0.08
    return _bounded(score)


def _logistics_ease(candidate: DealCandidate, request: DealSearchRequest) -> float:
    score = 1.0
    score -= min(candidate.layovers, 3) * 0.12
    score -= min(candidate.internal_transfer_count, 4) * 0.08
    if candidate.estimated_travel_hours is not None:
        score -= min(candidate.estimated_travel_hours / 30.0, 0.35)
    elif candidate.flight_duration_hours is not None:
        score -= min(candidate.flight_duration_hours / 30.0, 0.30)
    score += {
        LogisticsComplexity.SIMPLE: 0.05,
        LogisticsComplexity.MODERATE: -0.05,
        LogisticsComplexity.COMPLEX: -0.25,
        LogisticsComplexity.UNKNOWN: -0.08,
    }[candidate.logistics_complexity]
    if request.travel_party.mobility_sensitive:
        score += (_mobility_fit(candidate, request) - 0.5) * 0.35
    return _bounded(score)


def _seasonality(candidate: DealCandidate) -> float:
    return {
        SeasonType.SHOULDER: 1.00,
        SeasonType.BEST: 0.92,
        SeasonType.PEAK: 0.72,
        SeasonType.STANDARD: 0.70,
        SeasonType.AVOID: 0.15,
        SeasonType.UNKNOWN: 0.55,
    }[candidate.season_type]


def _crowd(candidate: DealCandidate) -> float:
    return {
        CrowdLevel.LOW: 1.00,
        CrowdLevel.MEDIUM: 0.72,
        CrowdLevel.HIGH: 0.35,
        CrowdLevel.UNKNOWN: 0.55,
    }[candidate.crowd_level]


def _safety(candidate: DealCandidate) -> float:
    advisory = {
        TravelAdvisory.NORMAL: 1.00,
        TravelAdvisory.CAUTION: 0.68,
        TravelAdvisory.SERIOUS: 0.10,
        TravelAdvisory.DO_NOT_TRAVEL: 0.0,
        TravelAdvisory.UNKNOWN: 0.55,
    }[candidate.travel_advisory]
    news = {
        NewsRisk.LOW: 1.00,
        NewsRisk.MEDIUM: 0.72,
        NewsRisk.HIGH: 0.30,
        NewsRisk.SEVERE: 0.0,
        NewsRisk.UNKNOWN: 0.55,
    }[candidate.news_risk]
    return _bounded((advisory + news + _neutral(candidate.safety_score, 0.60)) / 3.0)


def _visa_feasibility(candidate: DealCandidate, request: DealSearchRequest) -> float:
    if normalize_text(candidate.country) == normalize_text(request.origin_country):
        return 1.0
    if candidate.visa_processing_days is None:
        return 0.60
    lead_days = max((candidate.start_date - request.reference_date).days, 0)
    if candidate.visa_processing_days > lead_days:
        return 0.0
    margin = lead_days - candidate.visa_processing_days
    return _bounded(0.65 + min(margin / 90.0, 0.35))


def _history_features(candidate: DealCandidate, request: DealSearchRequest) -> tuple[float, ...]:
    history = request.history
    destination = normalize_text(candidate.destination)
    country = normalize_text(candidate.country)
    tags = normalized_set(candidate.tags)
    details_text = " ".join(normalize_text(value) for value in candidate.details.values())

    wishlist = normalized_set(history.wishlist)
    liked_places = normalized_set(history.liked_places)
    liked_countries = normalized_set(history.liked_countries)
    style_match = any(
        normalize_text(style) in tags or normalize_text(style) in details_text
        for style in history.liked_hotel_styles
    )
    product_match = style_match or any(
        normalize_text(preference) in details_text
        for preference in (*history.preferred_airlines, *history.accommodation_preferences)
    )
    return (
        1.0 if destination in wishlist or country in wishlist else 0.0,
        1.0 if destination in liked_places or country in liked_countries else 0.0,
        1.0 if product_match else 0.0,
    )


def _conversion_signal(candidate: DealCandidate) -> float:
    values: list[float] = []
    if candidate.conversion_rate is not None:
        values.append(_bounded(candidate.conversion_rate / 0.25))
    if candidate.click_through_rate is not None:
        values.append(_bounded(candidate.click_through_rate / 0.12))
    if candidate.repeat_booking_rate is not None:
        values.append(_bounded(candidate.repeat_booking_rate / 0.35))
    return sum(values) / len(values) if values else 0.50


def _booking_popularity(candidate: DealCandidate) -> float:
    if candidate.number_of_bookings is None:
        return 0.50
    return _bounded(log1p(candidate.number_of_bookings) / log1p(1000))


def extract_feature_vector(
    candidate: DealCandidate,
    request: DealSearchRequest,
    pool: CandidatePoolStatistics,
    config: EngineConfig,
) -> FeatureVector:
    candidate_terms = (
        *candidate.tags,
        candidate.name,
        candidate.destination,
        *candidate.value_additions,
    )
    holiday_match = holiday_type_match_score(request.holiday_types, candidate_terms)
    interest_match = phrase_overlap_score(request.interests, candidate_terms)
    label_words = tuple(
        word
        for word in normalize_text(request.source_label).replace("/", " ").split()
        if len(word) > 2
    )
    label_match = phrase_overlap_score(label_words, candidate_terms)
    wishlist_match, liked_destination, preferred_product = _history_features(candidate, request)

    complaint_health = (
        0.50
        if candidate.supplier_complaint_ratio is None
        else _bounded(1.0 - candidate.supplier_complaint_ratio)
    )
    refund_health = (
        0.50 if candidate.refund_frequency is None else _bounded(1.0 - candidate.refund_frequency)
    )
    value_additions = _bounded(
        0.35
        + len(candidate.value_additions) * 0.10
        + (0.15 if candidate.private_experience else 0.0)
    )

    values = (
        _date_match(candidate, request),
        _duration_match(candidate, request),
        holiday_match,
        interest_match,
        label_match,
        _traveler_fit(candidate, request),
        _family_fit(candidate, request),
        _mobility_fit(candidate, request),
        candidate.quality_rating / 5.0,
        _review_confidence(candidate, request, config),
        _cancellation(candidate),
        _neutral(candidate.supplier_reliability, 0.55),
        complaint_health,
        refund_health,
        _relative_price_value(candidate, pool),
        _quality_adjusted_value(candidate, pool),
        _budget_fit(candidate, request),
        _market_discount(candidate),
        value_additions,
        _seasonality(candidate),
        _crowd(candidate),
        _safety(candidate),
        _visa_feasibility(candidate, request),
        _logistics_ease(candidate, request),
        wishlist_match,
        liked_destination,
        preferred_product,
        _conversion_signal(candidate),
        _booking_popularity(candidate),
        _neutral(candidate.novelty, 0.55),
        1.0 if candidate.review_count is None else 0.0,
        1.0 if candidate.supplier_reliability is None else 0.0,
        1.0 if candidate.market_reference_price is None else 0.0,
    )
    return FeatureVector(names=FEATURE_NAMES, values=tuple(_bounded(value) for value in values))


def business_score_breakdown(features: FeatureVector) -> BusinessScoreBreakdown:
    value = features.value
    date_match = (value("date_match") + value("duration_match")) / 2.0
    ease_of_travel = (
        value("logistics_ease") * 0.35
        + value("visa_feasibility") * 0.20
        + value("mobility_fit") * 0.15
        + value("safety") * 0.30
    )
    product_quality = (
        value("quality_rating") * 0.45
        + value("review_confidence") * 0.20
        + value("supplier_reliability") * 0.15
        + value("supplier_complaint_health") * 0.10
        + value("refund_health") * 0.10
    )
    emotional_fit = (
        value("holiday_type_match") * 0.28
        + value("interest_match") * 0.20
        + value("occasion_label_match") * 0.17
        + value("traveler_fit") * 0.20
        + value("family_fit") * 0.15
    )
    historical_conversion = (
        value("conversion_signal") * 0.35
        + value("booking_popularity") * 0.20
        + value("wishlist_match") * 0.20
        + value("liked_destination") * 0.15
        + value("preferred_product_match") * 0.10
    )
    value_addition = (
        value("relative_price_value") * 0.25
        + value("quality_adjusted_value") * 0.25
        + value("budget_fit") * 0.20
        + value("market_discount") * 0.15
        + value("value_additions") * 0.15
    )
    destination_appeal = (
        value("seasonality") * 0.25
        + value("crowd_preference") * 0.15
        + value("safety") * 0.25
        + value("novelty") * 0.10
        + value("wishlist_match") * 0.15
        + value("liked_destination") * 0.10
    )
    return BusinessScoreBreakdown(
        date_match=_bounded(date_match),
        ease_of_travel=_bounded(ease_of_travel),
        product_quality=_bounded(product_quality),
        emotional_fit=_bounded(emotional_fit),
        cancellation_flexibility=value("cancellation_flexibility"),
        historical_conversion=_bounded(historical_conversion),
        value_addition=_bounded(value_addition),
        destination_appeal=_bounded(destination_appeal),
    )


def feature_schema_version() -> str:
    return FEATURE_SCHEMA_VERSION
