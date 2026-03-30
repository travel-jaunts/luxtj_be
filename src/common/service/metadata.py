from dataclasses import dataclass


@dataclass
class PaginationMeta:
    total: int
    page: int
    size: int
