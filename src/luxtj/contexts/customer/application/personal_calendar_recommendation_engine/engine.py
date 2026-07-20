import asyncio
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from .config import DEFAULT_CONFIG, ENGINE_VERSION, EngineConfig
from .enums import RecommendationStatus, RejectionReason
from .features import build_pool_statistics, extract_feature_vector
from .filters import validate_candidate
from .ml_model import LinearRankingModel
from .models import (
    DealCandidate,
    DealRecommendation,
    DealSearchRequest,
    OpportunityRecommendationResult,
    PersonalCalendarRecommendationInput,
    PersonalCalendarRecommendationResult,
    RankingCandidateObservation,
    RankingObservation,
    RecommendationOption,
    TravelOpportunity,
    TravelWindow,
    UnavailableRecommendation,
    WindowRecommendationResult,
)
from .observers.interfaces import RankingObserver
from .opportunity_logic import build_travel_opportunities
from .providers.interfaces import DealInventoryProvider
from .ranking import rank_candidate, rank_key, why_candidate_won


@dataclass(frozen=True, slots=True)
class _RecommendationJob:
    opportunity_index: int
    window_index: int
    option_index: int
    request: DealSearchRequest


def _request_for(
    context: PersonalCalendarRecommendationInput,
    opportunity: TravelOpportunity,
    window: TravelWindow,
    plan_type,
    tier,
) -> DealSearchRequest:
    return DealSearchRequest(
        account_id=context.account_id,
        origin_city=context.origin_city,
        origin_country=context.origin_country,
        reference_date=context.reference_date,
        pricing_currency=context.pricing_currency,
        source_item_id=opportunity.source_item_id,
        source_type=opportunity.source_type,
        source_label=opportunity.source_label,
        holiday_types=opportunity.holiday_types,
        requires_family_suitability=opportunity.requires_family_suitability,
        window=window,
        allowed_start=opportunity.allowed_start,
        allowed_end=opportunity.allowed_end,
        plan_type=plan_type,
        tier=tier,
        interests=context.preferences.interests,
        travel_intent=context.preferences.travel_intent,
        travel_party=context.travel_party,
        history=context.history,
        budget=context.budget,
        passport_country=context.passport_country,
        residency_country=context.residency_country,
    )


def _deduplicate_candidates(candidates: Sequence[DealCandidate]) -> tuple[DealCandidate, ...]:
    by_identity: dict[tuple[str, str], DealCandidate] = {}
    for candidate in candidates:
        key = (candidate.provider_id, candidate.candidate_id)
        by_identity.setdefault(key, candidate)
    return tuple(by_identity.values())


def _unavailable(
    request: DealSearchRequest,
    reason_codes: tuple[RejectionReason, ...],
    message: str,
) -> UnavailableRecommendation:
    return UnavailableRecommendation(
        status=RecommendationStatus.UNAVAILABLE,
        plan_type=request.plan_type,
        tier=request.tier,
        reason_codes=reason_codes,
        message=message,
    )


async def _recommend_option(
    request: DealSearchRequest,
    inventory_provider: DealInventoryProvider,
    config: EngineConfig,
    model: LinearRankingModel | None,
    semaphore: asyncio.Semaphore,
    ranking_observer: RankingObserver | None,
) -> RecommendationOption:
    try:
        async with semaphore:
            raw_candidates = await inventory_provider.search_deals(request)
    except Exception as exc:
        return _unavailable(
            request,
            (RejectionReason.PROVIDER_ERROR,),
            f"Inventory provider failed: {type(exc).__name__}",
        )

    candidates = _deduplicate_candidates(tuple(raw_candidates))
    if not candidates:
        return _unavailable(
            request,
            (RejectionReason.NO_CANDIDATES,),
            "No inventory candidates were returned for this window, plan type, and tier.",
        )

    accepted: list[DealCandidate] = []
    rejected_reasons: list[RejectionReason] = []
    for candidate in candidates:
        decision = validate_candidate(candidate, request, config)
        if decision.accepted:
            accepted.append(candidate)
        else:
            rejected_reasons.extend(decision.reason_codes)

    if not accepted:
        counts = Counter(rejected_reasons)
        ordered = tuple(
            reason
            for reason, _ in sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0].value),
            )
        )
        return _unavailable(
            request,
            ordered or (RejectionReason.NO_VALID_CANDIDATES,),
            "All returned inventory candidates failed hard business-rule validation.",
        )

    accepted_tuple = tuple(accepted)
    pool = build_pool_statistics(accepted_tuple)
    ranked = [
        rank_candidate(
            candidate,
            extract_feature_vector(candidate, request, pool, config),
            request,
            config,
            model,
        )
        for candidate in accepted_tuple
    ]
    ranked.sort(key=rank_key)
    winner = ranked[0]
    if ranking_observer is not None:
        observation = RankingObservation(
            account_id=request.account_id,
            source_item_id=request.source_item_id,
            source_type=request.source_type,
            window_start=request.window.start_date,
            window_end=request.window.end_date,
            plan_type=request.plan_type,
            tier=request.tier,
            recorded_at=datetime.now(UTC),
            ranker_version=winner.metadata.ranker_version,
            model_version=winner.metadata.model_version,
            candidates=tuple(
                RankingCandidateObservation(
                    candidate_id=item.candidate.candidate_id,
                    provider_id=item.candidate.provider_id,
                    rank=index,
                    selected=index == 1,
                    features=item.features,
                    heuristic_score=item.metadata.heuristic_score,
                    ml_score=item.metadata.ml_score,
                    final_score=item.final_score,
                )
                for index, item in enumerate(ranked, start=1)
            ),
        )
        try:
            await ranking_observer.record_ranking(observation)
        except Exception:
            pass
    return DealRecommendation(
        status=RecommendationStatus.AVAILABLE,
        plan_type=request.plan_type,
        tier=request.tier,
        candidate=winner.candidate,
        final_score=winner.final_score,
        business_score_breakdown=winner.business_breakdown,
        ranking_metadata=winner.metadata,
        why_this_won=why_candidate_won(winner),
    )


def _build_jobs(
    context: PersonalCalendarRecommendationInput,
    opportunities: tuple[TravelOpportunity, ...],
) -> tuple[_RecommendationJob, ...]:
    jobs: list[_RecommendationJob] = []
    for opportunity_index, opportunity in enumerate(opportunities):
        for window_index, window in enumerate(opportunity.windows):
            option_index = 0
            for plan_type in context.preferences.plan_types:
                for tier in context.preferences.tiers:
                    jobs.append(
                        _RecommendationJob(
                            opportunity_index=opportunity_index,
                            window_index=window_index,
                            option_index=option_index,
                            request=_request_for(
                                context,
                                opportunity,
                                window,
                                plan_type,
                                tier,
                            ),
                        )
                    )
                    option_index += 1
    return tuple(jobs)


async def recommend_best_deal(
    context: PersonalCalendarRecommendationInput,
    inventory_provider: DealInventoryProvider,
    config: EngineConfig = DEFAULT_CONFIG,
    *,
    ranking_model: LinearRankingModel | None = None,
    ranking_observer: RankingObserver | None = None,
    generated_at: datetime | None = None,
) -> PersonalCalendarRecommendationResult:
    """Recommend deals for mapped personal-calendar events and periods.

    The caller must load the personal calendar from its database and map the domain
    object into ``PersonalCalendarRecommendationInput``. This engine performs no
    database, SQLAlchemy, FastAPI, HTTP, environment-variable, or personal-calendar
    API access.
    """

    opportunities = build_travel_opportunities(context, config)
    jobs = _build_jobs(context, opportunities)
    semaphore = asyncio.Semaphore(config.max_concurrent_searches)
    job_results = await asyncio.gather(
        *(
            _recommend_option(
                job.request,
                inventory_provider,
                config,
                ranking_model,
                semaphore,
                ranking_observer,
            )
            for job in jobs
        )
    )
    result_by_position = {
        (job.opportunity_index, job.window_index, job.option_index): result
        for job, result in zip(jobs, job_results, strict=True)
    }

    option_count = len(context.preferences.plan_types) * len(context.preferences.tiers)
    opportunity_results: list[OpportunityRecommendationResult] = []
    for opportunity_index, opportunity in enumerate(opportunities):
        window_results: list[WindowRecommendationResult] = []
        for window_index, window in enumerate(opportunity.windows):
            options = tuple(
                result_by_position[(opportunity_index, window_index, option_index)]
                for option_index in range(option_count)
            )
            window_results.append(WindowRecommendationResult(window=window, options=options))
        opportunity_results.append(
            OpportunityRecommendationResult(
                source_item_id=opportunity.source_item_id,
                source_type=opportunity.source_type,
                source_label=opportunity.source_label,
                target_date=opportunity.target_date,
                holiday_types=opportunity.holiday_types,
                windows=tuple(window_results),
            )
        )

    return PersonalCalendarRecommendationResult(
        account_id=context.account_id,
        opportunities=tuple(opportunity_results),
        generated_at=generated_at or datetime.now(UTC),
        engine_version=ENGINE_VERSION,
    )
