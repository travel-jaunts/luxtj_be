from dataclasses import dataclass


@dataclass
class PaginationMeta:
    """Data class for pagination metadata"""

    total: int
    page: int
    size: int
