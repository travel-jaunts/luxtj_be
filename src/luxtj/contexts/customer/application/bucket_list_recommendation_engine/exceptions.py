"""Domain-specific exceptions for the Bucket List Recommendation Engine."""


class RecommendationEngineError(Exception):
    """Base exception for all recommendation-engine errors."""


class InvalidItineraryError(RecommendationEngineError):
    """Raised when the itinerary is invalid."""


class MissingInventoryError(RecommendationEngineError):
    """Raised when required inventory is completely unavailable."""


class IncompleteRecommendationError(RecommendationEngineError):
    """Raised when a recommendation candidate is incomplete."""


class InvalidPricingError(RecommendationEngineError):
    """Raised when pricing is negative or internally inconsistent."""


class UnsupportedTierError(RecommendationEngineError):
    """Raised when the requested hotel tier is unsupported."""


class InvalidTravelDatesError(RecommendationEngineError):
    """Raised when travel or stay dates are inconsistent."""
