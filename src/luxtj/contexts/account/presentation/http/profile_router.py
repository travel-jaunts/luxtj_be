from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException

from luxtj.contexts.account.application.gallery_commands import (
    SetProfilePictureCommand,
)
from luxtj.contexts.account.application.gallery_use_cases import (
    ClearProfilePicture,
    SetProfilePicture,
)
from luxtj.contexts.account.application.profile_commands import (
    AddFrequentTravellerCommand,
    RemoveFrequentTravellerCommand,
    UpdateContactInfoCommand,
    UpdateDestinationsCommand,
    UpdateFrequentTravellerCommand,
    UpdatePersonalInfoCommand,
    UpdatePreferencesCommand,
)
from luxtj.contexts.account.application.profile_use_cases import (
    AddFrequentTraveller,
    GetAccountProfile,
    ListFrequentTravellers,
    RemoveFrequentTraveller,
    UpdateContactInfo,
    UpdateFrequentTraveller,
    UpdatePersonalInfo,
    UpdatePreferredDestinations,
    UpdateTravelPreferences,
)
from luxtj.contexts.account.bootstrap import (
    build_add_frequent_traveller,
    build_clear_profile_picture,
    build_get_account_profile,
    build_list_frequent_travellers,
    build_remove_frequent_traveller,
    build_set_profile_picture,
    build_update_contact_info,
    build_update_frequent_traveller,
    build_update_personal_info,
    build_update_preferred_destinations,
    build_update_travel_preferences,
)
from luxtj.contexts.account.domain.errors import (
    AccountProfileError,
    FrequentTravellerNotFoundError,
    ImageNotFoundError,
    InvalidProfilePictureError,
    ProfileNotFoundError,
)
from luxtj.contexts.account.domain.profile_value_objects import CityLocation, EmergencyContact
from luxtj.contexts.account.domain.value_objects import PhoneIdentity
from luxtj.contexts.account.presentation.http.dependencies import (
    AccountPrincipal,
    get_current_account_principal,
)
from luxtj.contexts.account.presentation.http.profile_schemas import (
    AccountProfileSerializer,
    AddFrequentTravellerBody,
    FrequentTravellerListSerializer,
    FrequentTravellerSerializer,
    ProfilePictureSerializer,
    SetProfilePictureBody,
    TravellerIdBody,
    UpdateContactInfoBody,
    UpdateDestinationsBody,
    UpdateFrequentTravellerBody,
    UpdatePersonalInfoBody,
    UpdatePreferencesBody,
    patched,
)
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiErrorResponse,
    ApiSuccessResponse,
    RequestProcessStatus,
)

account_profile_router = APIRouter(prefix="/account/profile", tags=["account-profile"])

_NOT_FOUND_ERRORS = (
    ProfileNotFoundError,
    FrequentTravellerNotFoundError,
    ImageNotFoundError,
)


def _raise_for(exc: AccountProfileError) -> None:
    if isinstance(exc, _NOT_FOUND_ERRORS):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, InvalidProfilePictureError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _full_profile(
    account_id: UUID,
    get_profile: GetAccountProfile,
    list_travellers: ListFrequentTravellers,
) -> AccountProfileSerializer:
    view = await get_profile(account_id)
    travellers = await list_travellers(account_id)
    return AccountProfileSerializer.from_dto(view, travellers)


@account_profile_router.post(
    "/get",
    response_model=ApiSuccessResponse[AccountProfileSerializer] | ApiErrorResponse,
    status_code=200,
)
async def get_profile(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    get_profile_use_case: Annotated[GetAccountProfile, Depends(build_get_account_profile)],
    list_travellers: Annotated[ListFrequentTravellers, Depends(build_list_frequent_travellers)],
) -> ApiSuccessResponse[AccountProfileSerializer] | ApiErrorResponse:
    try:
        output = await _full_profile(principal.account_id, get_profile_use_case, list_travellers)
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=output)


@account_profile_router.post(
    "/personal",
    response_model=ApiSuccessResponse[AccountProfileSerializer] | ApiErrorResponse,
    status_code=200,
)
async def update_personal(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[UpdatePersonalInfo, Depends(build_update_personal_info)],
    get_profile_use_case: Annotated[GetAccountProfile, Depends(build_get_account_profile)],
    list_travellers: Annotated[ListFrequentTravellers, Depends(build_list_frequent_travellers)],
    body: Annotated[UpdatePersonalInfoBody, Body(...)],
) -> ApiSuccessResponse[AccountProfileSerializer] | ApiErrorResponse:
    location = (
        CityLocation(
            city_name=body.location.city_name,
            country_code=body.location.country_code,
            latitude=body.location.latitude,
            longitude=body.location.longitude,
        )
        if body.location is not None
        else None
    )
    try:
        await use_case(
            UpdatePersonalInfoCommand(
                account_id=principal.account_id,
                first_name=patched(body, "first_name", body.first_name),
                last_name=patched(body, "last_name", body.last_name),
                gender=patched(body, "gender", body.gender),
                date_of_birth=patched(body, "date_of_birth", body.date_of_birth),
                nationality=patched(body, "nationality", body.nationality),
                location=patched(body, "location", location),
                language=patched(body, "language", body.language),
                description=patched(body, "description", body.description),
                email=patched(body, "email", body.email),
                facebook=patched(body, "facebook", body.facebook),
                instagram=patched(body, "instagram", body.instagram),
                linkedin=patched(body, "linkedin", body.linkedin),
            )
        )
        output = await _full_profile(principal.account_id, get_profile_use_case, list_travellers)
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=output)


@account_profile_router.post(
    "/contact",
    response_model=ApiSuccessResponse[AccountProfileSerializer] | ApiErrorResponse,
    status_code=200,
)
async def update_contact(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[UpdateContactInfo, Depends(build_update_contact_info)],
    get_profile_use_case: Annotated[GetAccountProfile, Depends(build_get_account_profile)],
    list_travellers: Annotated[ListFrequentTravellers, Depends(build_list_frequent_travellers)],
    body: Annotated[UpdateContactInfoBody, Body(...)],
) -> ApiSuccessResponse[AccountProfileSerializer] | ApiErrorResponse:
    alternative_phone = (
        PhoneIdentity(body.alternative_phone.dial_code, body.alternative_phone.phone_number)
        if body.alternative_phone is not None
        else None
    )
    emergency_contact = (
        EmergencyContact(
            first_name=body.emergency_contact.first_name,
            dial_code=body.emergency_contact.dial_code,
            phone_number=body.emergency_contact.phone_number,
        )
        if body.emergency_contact is not None
        else None
    )
    try:
        await use_case(
            UpdateContactInfoCommand(
                account_id=principal.account_id,
                alternative_phone=patched(body, "alternative_phone", alternative_phone),
                preferred_contact_method=patched(
                    body, "preferred_contact_method", body.preferred_contact_method
                ),
                emergency_contact=patched(body, "emergency_contact", emergency_contact),
            )
        )
        output = await _full_profile(principal.account_id, get_profile_use_case, list_travellers)
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=output)


@account_profile_router.post(
    "/preferences",
    response_model=ApiSuccessResponse[AccountProfileSerializer] | ApiErrorResponse,
    status_code=200,
)
async def update_preferences(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[UpdateTravelPreferences, Depends(build_update_travel_preferences)],
    get_profile_use_case: Annotated[GetAccountProfile, Depends(build_get_account_profile)],
    list_travellers: Annotated[ListFrequentTravellers, Depends(build_list_frequent_travellers)],
    body: Annotated[UpdatePreferencesBody, Body(...)],
) -> ApiSuccessResponse[AccountProfileSerializer] | ApiErrorResponse:
    try:
        await use_case(
            UpdatePreferencesCommand(
                account_id=principal.account_id,
                stay_hotels=patched(body, "stay_hotels", body.stay_hotels),
                stay_villas=patched(body, "stay_villas", body.stay_villas),
                stay_resorts=patched(body, "stay_resorts", body.stay_resorts),
                stay_boutique_hotels=patched(
                    body, "stay_boutique_hotels", body.stay_boutique_hotels
                ),
                stay_cruises=patched(body, "stay_cruises", body.stay_cruises),
                flight_class=patched(body, "flight_class", body.flight_class),
                flight_priority=patched(body, "flight_priority", body.flight_priority),
                trip_pace=patched(body, "trip_pace", body.trip_pace),
                baggage_style=patched(body, "baggage_style", body.baggage_style),
            )
        )
        output = await _full_profile(principal.account_id, get_profile_use_case, list_travellers)
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=output)


@account_profile_router.post(
    "/destinations",
    response_model=ApiSuccessResponse[AccountProfileSerializer] | ApiErrorResponse,
    status_code=200,
)
async def update_destinations(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[UpdatePreferredDestinations, Depends(build_update_preferred_destinations)],
    get_profile_use_case: Annotated[GetAccountProfile, Depends(build_get_account_profile)],
    list_travellers: Annotated[ListFrequentTravellers, Depends(build_list_frequent_travellers)],
    body: Annotated[UpdateDestinationsBody, Body(...)],
) -> ApiSuccessResponse[AccountProfileSerializer] | ApiErrorResponse:
    try:
        await use_case(
            UpdateDestinationsCommand(
                account_id=principal.account_id,
                countries_visited=patched(body, "countries_visited", tuple(body.countries_visited)),
                indian_states_visited=patched(
                    body, "indian_states_visited", tuple(body.indian_states_visited)
                ),
                places_loved=patched(body, "places_loved", tuple(body.places_loved)),
                places_recommended=patched(
                    body, "places_recommended", tuple(body.places_recommended)
                ),
                travel_moments_enjoyed=patched(
                    body, "travel_moments_enjoyed", tuple(body.travel_moments_enjoyed)
                ),
            )
        )
        output = await _full_profile(principal.account_id, get_profile_use_case, list_travellers)
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=output)


@account_profile_router.post(
    "/travellers/list",
    response_model=ApiSuccessResponse[FrequentTravellerListSerializer] | ApiErrorResponse,
    status_code=200,
)
async def list_travellers(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[ListFrequentTravellers, Depends(build_list_frequent_travellers)],
) -> ApiSuccessResponse[FrequentTravellerListSerializer] | ApiErrorResponse:
    travellers = await use_case(principal.account_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=FrequentTravellerListSerializer.from_dto(travellers),
    )


@account_profile_router.post(
    "/travellers/add",
    response_model=ApiSuccessResponse[FrequentTravellerSerializer] | ApiErrorResponse,
    status_code=200,
)
async def add_traveller(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[AddFrequentTraveller, Depends(build_add_frequent_traveller)],
    body: Annotated[AddFrequentTravellerBody, Body(...)],
) -> ApiSuccessResponse[FrequentTravellerSerializer] | ApiErrorResponse:
    try:
        traveller = await use_case(
            AddFrequentTravellerCommand(
                account_id=principal.account_id,
                first_name=body.first_name,
                last_name=body.last_name,
                relationship=body.relationship,
                nationality=body.nationality,
                gender=body.gender,
                birth_year=body.birth_year,
                birth_month=body.birth_month,
                passport_number=body.passport_number,
            )
        )
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=FrequentTravellerSerializer.from_dto(traveller),
    )


@account_profile_router.post(
    "/travellers/update",
    response_model=ApiSuccessResponse[FrequentTravellerSerializer] | ApiErrorResponse,
    status_code=200,
)
async def update_traveller(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[UpdateFrequentTraveller, Depends(build_update_frequent_traveller)],
    body: Annotated[UpdateFrequentTravellerBody, Body(...)],
) -> ApiSuccessResponse[FrequentTravellerSerializer] | ApiErrorResponse:
    try:
        traveller = await use_case(
            UpdateFrequentTravellerCommand(
                account_id=principal.account_id,
                traveller_id=UUID(body.traveller_id),
                first_name=patched(body, "first_name", body.first_name),
                last_name=patched(body, "last_name", body.last_name),
                relationship=patched(body, "relationship", body.relationship),
                nationality=patched(body, "nationality", body.nationality),
                gender=patched(body, "gender", body.gender),
                birth_year=patched(body, "birth_year", body.birth_year),
                birth_month=patched(body, "birth_month", body.birth_month),
                passport_number=patched(body, "passport_number", body.passport_number),
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid traveller id") from exc
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=FrequentTravellerSerializer.from_dto(traveller),
    )


@account_profile_router.post(
    "/travellers/remove",
    response_model=ApiSuccessResponse[None] | ApiErrorResponse,
    status_code=200,
)
async def remove_traveller(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[RemoveFrequentTraveller, Depends(build_remove_frequent_traveller)],
    body: Annotated[TravellerIdBody, Body(...)],
) -> ApiSuccessResponse[None] | ApiErrorResponse:
    try:
        await use_case(
            RemoveFrequentTravellerCommand(
                account_id=principal.account_id,
                traveller_id=UUID(body.traveller_id),
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid traveller id") from exc
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(status=RequestProcessStatus.OK)


@account_profile_router.post(
    "/picture/set",
    response_model=ApiSuccessResponse[ProfilePictureSerializer] | ApiErrorResponse,
    status_code=200,
)
async def set_profile_picture(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[SetProfilePicture, Depends(build_set_profile_picture)],
    body: Annotated[SetProfilePictureBody, Body(...)],
) -> ApiSuccessResponse[ProfilePictureSerializer] | ApiErrorResponse:
    try:
        profile = await use_case(
            SetProfilePictureCommand(
                account_id=principal.account_id,
                image_id=UUID(body.image_id),
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid image id") from exc
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK, output=ProfilePictureSerializer.from_dto(profile)
    )


@account_profile_router.post(
    "/picture/clear",
    response_model=ApiSuccessResponse[ProfilePictureSerializer] | ApiErrorResponse,
    status_code=200,
)
async def clear_profile_picture(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[ClearProfilePicture, Depends(build_clear_profile_picture)],
) -> ApiSuccessResponse[ProfilePictureSerializer] | ApiErrorResponse:
    try:
        profile = await use_case(principal.account_id)
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK, output=ProfilePictureSerializer.from_dto(profile)
    )
