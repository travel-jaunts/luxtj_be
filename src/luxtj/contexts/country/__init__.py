"""Shared country catalog — static CSV-backed service for all modules."""

from __future__ import annotations

from luxtj.contexts.country.service import CountryService, get_country_service

__all__ = ["CountryService", "get_country_service"]
