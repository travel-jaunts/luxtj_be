class PersonalCalendarRecommendationEngineError(Exception):
    """Base exception for the standalone recommendation engine."""


class InvalidEngineInputError(PersonalCalendarRecommendationEngineError, ValueError):
    """Raised when a typed input violates an engine invariant."""


class RankingModelError(PersonalCalendarRecommendationEngineError, ValueError):
    """Raised when a ranking-model artifact is invalid or incompatible."""
