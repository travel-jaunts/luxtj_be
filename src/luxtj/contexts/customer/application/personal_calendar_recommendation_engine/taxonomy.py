from collections.abc import Iterable

from luxtj.contexts.customer.domain.enums import HolidayTypeEnum

HOLIDAY_TYPE_SYNONYMS: dict[HolidayTypeEnum, frozenset[str]] = {
    HolidayTypeEnum.AFRICAN_SAFARIS_AND_WILDLIFE_TOURS: frozenset(
        {"safari", "wildlife", "game drive", "nature reserve", "big five"}
    ),
    HolidayTypeEnum.LUXURY_STAYS_HOTELS_VILLAS: frozenset(
        {"luxury hotel", "luxury stay", "villa", "resort", "suite", "private villa"}
    ),
    HolidayTypeEnum.WELLNESS_AND_SPA_RETREATS: frozenset(
        {"wellness", "spa", "retreat", "yoga", "mindfulness", "detox"}
    ),
    HolidayTypeEnum.HONEYMOONS_AND_ROMANTIC_HOLIDAYS: frozenset(
        {"honeymoon", "romantic", "romance", "couples", "anniversary", "private dining"}
    ),
    HolidayTypeEnum.FAMILY_LUXURY_HOLIDAYS: frozenset(
        {"family", "children", "kids", "child friendly", "family resort", "school holiday"}
    ),
    HolidayTypeEnum.SKI_GOLF_AND_CASINO_TRIPS: frozenset(
        {"ski", "skiing", "golf", "casino", "winter sport", "golf resort"}
    ),
    HolidayTypeEnum.CULTURE_FOOD_AND_SHOPPING_TOURS: frozenset(
        {"culture", "cultural", "food", "culinary", "shopping", "heritage", "museum"}
    ),
    HolidayTypeEnum.ALL_INCLUSIVE_LUXURY_DEALS: frozenset(
        {"all inclusive", "full board", "inclusive package", "luxury package"}
    ),
    HolidayTypeEnum.ONCE_IN_A_LIFE_TIME_TRIPS: frozenset(
        {"once in a lifetime", "bucket list", "expedition", "iconic", "rare experience"}
    ),
    HolidayTypeEnum.DISNEY_AND_EURAIL_TICKETS: frozenset(
        {"disney", "theme park", "eurail", "rail pass", "europe rail", "family attraction"}
    ),
    HolidayTypeEnum.SIGNATURE_EXPERIENCES: frozenset(
        {"signature experience", "exclusive", "private experience", "vip", "bespoke"}
    ),
}


def normalize_text(value: object | None) -> str:
    return " ".join(str(value or "").casefold().replace("_", " ").replace("-", " ").split())


def normalized_set(values: Iterable[object]) -> set[str]:
    return {normalized for value in values if (normalized := normalize_text(value))}


def holiday_terms(holiday_types: Iterable[HolidayTypeEnum]) -> set[str]:
    terms: set[str] = set()
    for holiday_type in holiday_types:
        terms.add(normalize_text(holiday_type.value))
        terms.update(normalized_set(HOLIDAY_TYPE_SYNONYMS[holiday_type]))
    return terms


def holiday_type_match_score(
    holiday_types: Iterable[HolidayTypeEnum],
    candidate_terms: Iterable[str],
) -> float:
    selected = tuple(holiday_types)
    if not selected:
        return 0.75
    candidate = normalized_set(candidate_terms)
    if not candidate:
        return 0.0
    matches: list[float] = []
    for holiday_type in selected:
        terms = {normalize_text(holiday_type.value)}
        terms.update(normalized_set(HOLIDAY_TYPE_SYNONYMS[holiday_type]))
        matched = any(
            term == candidate_term or term in candidate_term or candidate_term in term
            for term in terms
            for candidate_term in candidate
        )
        matches.append(1.0 if matched else 0.0)
    return sum(matches) / len(matches)


def phrase_overlap_score(required_terms: Iterable[str], candidate_terms: Iterable[str]) -> float:
    required = normalized_set(required_terms)
    candidate = normalized_set(candidate_terms)
    if not required:
        return 0.75
    if not candidate:
        return 0.0

    matched = 0
    for required_term in required:
        if any(
            required_term == candidate_term
            or required_term in candidate_term
            or candidate_term in required_term
            for candidate_term in candidate
        ):
            matched += 1
    return matched / len(required)
