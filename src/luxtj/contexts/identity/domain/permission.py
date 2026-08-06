from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Permission:
    id: UUID
    code: str
    name: str
    description: str
    resource: str
    action: str
    created_at: datetime
