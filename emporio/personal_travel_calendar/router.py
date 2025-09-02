from fastapi import APIRouter

from emporio.personal_travel_calendar.serializers import (
    DefaultOcassionsView,
    DefaultBreaksView,
)


personal_travel_calendar = APIRouter()


@personal_travel_calendar.get(
    "/default-ocassions", response_model=DefaultOcassionsView
)
async def get_personal_travel_calendar_default_ocassions() -> (
    DefaultOcassionsView
):
    return DefaultOcassionsView.get_defaults()


@personal_travel_calendar.get(
    "/default-breaks", response_model=DefaultBreaksView
)
async def get_personal_travel_calendar_default_breaks() -> DefaultBreaksView:
    return DefaultBreaksView.get_defaults()
