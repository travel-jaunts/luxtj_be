from datetime import datetime
from typing import Annotated, Any, Literal

try:
    from uuid import uuid7
except ImportError:  # pragma: no cover - Python < 3.14 compatibility for local tooling
    from uuid import uuid4 as uuid7

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]


class BaseDomainEvent(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )

    id: NonEmptyStr = Field(
        default_factory=lambda: str(uuid7()),
        description="CloudEvent id. Unique within the scope of source.",
    )
    source: NonEmptyStr = Field(..., description="CloudEvent source URI-reference.")
    specversion: Literal["1.0"] = Field(default="1.0", description="CloudEvents spec version.")
    type: NonEmptyStr = Field(..., description="CloudEvent type.")

    datacontenttype: str | None = Field(default=None, description="CloudEvent data media type.")
    dataschema: AnyUrl | None = Field(default=None, description="Schema URI for data.")
    subject: str | None = Field(default=None, description="Subject within source context.")
    time: datetime | None = Field(default=None, description="Timestamp of when the event occurred.")
    data: Any | None = Field(default=None, description="Event payload.")
