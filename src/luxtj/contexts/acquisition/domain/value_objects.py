from __future__ import annotations

import re
from dataclasses import dataclass

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _EMAIL_RE.match(normalized):
            raise ValueError(f"Invalid email address: {self.value!r}")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class AcquisitionContext:
    """Fingerprint captured from the HTTP request at registration time."""

    ip_address: str | None
    user_agent: str | None
    referer: str | None
    accept_language: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_term: str | None
    utm_content: str | None

    def to_dict(self) -> dict[str, str]:
        return {
            k: v
            for k, v in {
                "ip_address": self.ip_address,
                "user_agent": self.user_agent,
                "referer": self.referer,
                "accept_language": self.accept_language,
                "utm_source": self.utm_source,
                "utm_medium": self.utm_medium,
                "utm_campaign": self.utm_campaign,
                "utm_term": self.utm_term,
                "utm_content": self.utm_content,
            }.items()
            if v is not None
        }
