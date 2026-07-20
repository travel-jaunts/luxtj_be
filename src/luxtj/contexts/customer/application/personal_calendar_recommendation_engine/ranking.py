from dataclasses import dataclass

from .config import FEATURE_SCHEMA_VERSION, EngineConfig
from .enums import RankingMode
from .features import business_score_breakdown
from .ml_model import LinearRankingModel
from .models import (
    BusinessScoreBreakdown,
    DealCandidate,
    DealSearchRequest,
    FeatureVector,
    RankingMetadata,
)

RANKER_VERSION = "hybrid-ltr-1.0.0"


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    candidate: DealCandidate
    features: FeatureVector
    business_breakdown: BusinessScoreBreakdown
    final_score: float
    metadata: RankingMetadata


def _business_score(
    breakdown: BusinessScoreBreakdown,
    config: EngineConfig,
) -> float:
    weights = config.business_weights.as_dict()
    values = breakdown.as_dict()
    return sum(values[name] * weights[name] for name in weights)


def rank_candidate(
    candidate: DealCandidate,
    features: FeatureVector,
    request: DealSearchRequest,
    config: EngineConfig,
    model: LinearRankingModel | None,
) -> RankedCandidate:
    del request  # request-derived information is already encoded in the feature vector
    breakdown = business_score_breakdown(features)
    heuristic_score = _business_score(breakdown, config)

    approved_model = model if model is not None and model.approved_for_serving else None
    if approved_model is None:
        ml_score = None
        blend_weight = 0.0
        mode = RankingMode.HEURISTIC
        final_score = heuristic_score
        model_version = None
    else:
        ml_score = approved_model.predict(features)
        blend_weight = config.ml_blend_weight
        mode = RankingMode.ML if blend_weight == 1.0 else RankingMode.HYBRID
        final_score = heuristic_score * (1.0 - blend_weight) + ml_score * blend_weight
        model_version = approved_model.model_version

    return RankedCandidate(
        candidate=candidate,
        features=features,
        business_breakdown=breakdown,
        final_score=round(final_score, 6),
        metadata=RankingMetadata(
            mode=mode,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            ranker_version=RANKER_VERSION,
            model_version=model_version,
            heuristic_score=round(heuristic_score, 6),
            ml_score=None if ml_score is None else round(ml_score, 6),
            ml_blend_weight=blend_weight,
        ),
    )


def rank_key(item: RankedCandidate) -> tuple[object, ...]:
    values = item.features.as_dict()
    return (
        -item.final_score,
        -item.metadata.heuristic_score,
        -item.business_breakdown.product_quality,
        -values["quality_rating"],
        -values["review_confidence"],
        item.candidate.total_price,
        item.candidate.destination.casefold(),
        item.candidate.candidate_id,
    )


def why_candidate_won(item: RankedCandidate) -> tuple[str, ...]:
    values = item.features.as_dict()
    reasons: list[str] = []
    if values["date_match"] >= 0.95 and values["duration_match"] >= 0.95:
        reasons.append("Exact fit for the selected personal-calendar travel window.")
    if values["holiday_type_match"] >= 0.70:
        reasons.append("Strong match to the saved holiday-type preference.")
    if values["occasion_label_match"] >= 0.70:
        reasons.append("Strong fit for the calendar occasion.")
    if values["traveler_fit"] >= 0.90 or values["family_fit"] >= 0.90:
        reasons.append("Suitable for the specified travel party.")
    if values["quality_adjusted_value"] >= 0.75 or values["market_discount"] >= 0.75:
        reasons.append("Strong quality-adjusted price value within the comparable candidate pool.")
    if values["budget_fit"] >= 0.90:
        reasons.append("Fits the configured travel budget well.")
    if item.business_breakdown.product_quality >= 0.85:
        reasons.append("High product quality and supplier confidence.")
    if values["logistics_ease"] >= 0.80:
        reasons.append("Low-friction travel logistics.")
    if values["wishlist_match"] >= 1.0 or values["liked_destination"] >= 1.0:
        reasons.append("Past traveller preferences reinforce this option.")
    if item.metadata.mode is not RankingMode.HEURISTIC:
        reasons.append("The approved learning-to-rank model also preferred this candidate.")
    if not reasons:
        reasons.append("Highest deterministic score after all hard business rules were satisfied.")
    return tuple(reasons[:6])
