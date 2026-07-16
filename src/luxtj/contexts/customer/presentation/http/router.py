from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends

from luxtj.contexts.customer.application.commands import (
    AddBucketListItemCommand,
    AddPersonalCalendarEventCommand,
    AddPersonalCalendarPeriodCommand,
    DeleteBucketListItemCommand,
    SuggestDestinationsCommand,
    UpdateBucketListItemCommand,
)
from luxtj.contexts.customer.application.queries import GetBucketListQuery
from luxtj.contexts.customer.application.use_cases import (
    AddBucketListItem,
    AddPersonalCalendarEvent,
    AddPersonalCalendarPeriod,
    DeleteBucketListItem,
    GetBucketList,
    GetPersonalCalendarConsolidatedView,
    GetPersonalCalendarHolidayTypes,
    SuggestDestinations,
    UpdateBucketListItem,
)
from luxtj.contexts.customer.bootstrap import (
    build_add_bucket_list_item,
    build_add_personal_calendar_event,
    build_add_personal_calendar_period,
    build_delete_bucket_list_item,
    build_get_bucket_list,
    build_get_personal_calendar_consolidated_view,
    build_get_personal_calendar_holiday_types,
    build_suggest_destinations,
    build_update_bucket_list_item,
)
from luxtj.contexts.customer.domain.errors import (
    CustomerBucketListError,
    CustomerPersonalCalendarError,
)
from luxtj.contexts.customer.presentation.http.schemas import (
    AddBucketListItemBody,
    AddPersonalCalendarEventBody,
    AddPersonalCalendarPeriodBody,
    BucketListItemSerializer,
    BucketListSerializer,
    DestinationSuggestionResultSerializer,
    HolidayTypeListSerializer,
    PersonalCalendarConsolidatedViewSerializer,
    PersonalCalendarEventItemSerializer,
    PersonalCalendarPeriodItemSerializer,
    SuggestDestinationsBody,
    UpdateBucketListItemBody,
    ViewBucketListBody,
)
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiErrorResponse,
    ApiSuccessResponse,
    RequestProcessStatus,
)

customer_bucket_list_router = APIRouter(prefix="/bucket-list", tags=["customer_bucket_list"])
customer_personal_calendar_router = APIRouter(
    prefix="/personal-calendar",
    tags=["customer_personal_calendar"],
)


@customer_bucket_list_router.post(
    "/suggestions",
    response_model=ApiSuccessResponse[DestinationSuggestionResultSerializer] | ApiErrorResponse,
    status_code=200,
)
async def suggest_destinations(
    use_case: Annotated[SuggestDestinations, Depends(build_suggest_destinations)],
    body: Annotated[SuggestDestinationsBody, Body(...)],
) -> ApiSuccessResponse[DestinationSuggestionResultSerializer] | ApiErrorResponse:
    try:
        result = await use_case(
            SuggestDestinationsCommand(
                query=body.query,
                selected_kind=body.selected_kind,
                selected_name=body.selected_name,
            )
        )
    except CustomerBucketListError as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=DestinationSuggestionResultSerializer.from_dto(result),
    )


@customer_bucket_list_router.post(
    "/{account_id}/items/add",
    response_model=ApiSuccessResponse[BucketListItemSerializer] | ApiErrorResponse,
    status_code=200,
)
async def add_bucket_list_item(
    account_id: UUID,
    use_case: Annotated[AddBucketListItem, Depends(build_add_bucket_list_item)],
    body: Annotated[AddBucketListItemBody, Body(...)],
) -> ApiSuccessResponse[BucketListItemSerializer] | ApiErrorResponse:
    try:
        item = await use_case(
            AddBucketListItemCommand(
                account_id=account_id,
                destination_kind=body.destination_kind,
                destination_name=body.destination_name,
                parent_country=body.parent_country,
                ideal_days=body.ideal_days,
                display_order=body.display_order,
                notes=body.notes,
            )
        )
    except CustomerBucketListError as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=BucketListItemSerializer.from_dto(item),
    )


@customer_bucket_list_router.post(
    "/{account_id}/items/{item_id}/update",
    response_model=ApiSuccessResponse[BucketListItemSerializer] | ApiErrorResponse,
    status_code=200,
)
async def update_bucket_list_item(
    account_id: UUID,
    item_id: UUID,
    use_case: Annotated[UpdateBucketListItem, Depends(build_update_bucket_list_item)],
    body: Annotated[UpdateBucketListItemBody, Body(...)],
) -> ApiSuccessResponse[BucketListItemSerializer] | ApiErrorResponse:
    try:
        item = await use_case(
            UpdateBucketListItemCommand(
                account_id=account_id,
                item_id=item_id,
                ideal_days=body.ideal_days,
                display_order=body.display_order,
                notes=body.notes,
            )
        )
    except (CustomerBucketListError, KeyError) as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=BucketListItemSerializer.from_dto(item),
    )


@customer_bucket_list_router.post(
    "/{account_id}/items/{item_id}/delete",
    response_model=ApiSuccessResponse[BucketListItemSerializer] | ApiErrorResponse,
    status_code=200,
)
async def delete_bucket_list_item(
    account_id: UUID,
    item_id: UUID,
    use_case: Annotated[DeleteBucketListItem, Depends(build_delete_bucket_list_item)],
) -> ApiSuccessResponse[BucketListItemSerializer] | ApiErrorResponse:
    try:
        item = await use_case(
            DeleteBucketListItemCommand(
                account_id=account_id,
                item_id=item_id,
            )
        )
    except (CustomerBucketListError, KeyError) as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=BucketListItemSerializer.from_dto(item),
    )


@customer_bucket_list_router.post(
    "/{account_id}/view",
    response_model=ApiSuccessResponse[BucketListSerializer],
    status_code=200,
)
async def view_bucket_list(
    account_id: UUID,
    use_case: Annotated[GetBucketList, Depends(build_get_bucket_list)],
    body: Annotated[ViewBucketListBody, Body(...)],
) -> ApiSuccessResponse[BucketListSerializer]:
    bucket_list = await use_case(
        GetBucketListQuery(account_id=account_id, include_deleted=body.include_deleted)
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=BucketListSerializer.from_dto(bucket_list),
    )


@customer_personal_calendar_router.post(
    "/{account_id}/events/add",
    response_model=ApiSuccessResponse[PersonalCalendarEventItemSerializer] | ApiErrorResponse,
    status_code=200,
)
async def add_personal_calendar_event(
    account_id: UUID,
    use_case: Annotated[AddPersonalCalendarEvent, Depends(build_add_personal_calendar_event)],
    body: Annotated[AddPersonalCalendarEventBody, Body(...)],
) -> ApiSuccessResponse[PersonalCalendarEventItemSerializer] | ApiErrorResponse:
    try:
        item = await use_case(
            AddPersonalCalendarEventCommand(
                account_id=account_id,
                event_type=body.event_type,
                event_date=body.event_date,
                holiday_types=body.holiday_types,
                birthday_for=body.birthday_for,
                anniversary_for=body.anniversary_for,
                person_name=body.person_name,
                person1_name=body.person1_name,
                person2_name=body.person2_name,
                event_name=body.event_name,
            )
        )
    except CustomerPersonalCalendarError as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PersonalCalendarEventItemSerializer.from_dto(item),
    )


@customer_personal_calendar_router.post(
    "/{account_id}/periods/add",
    response_model=ApiSuccessResponse[PersonalCalendarPeriodItemSerializer] | ApiErrorResponse,
    status_code=200,
)
async def add_personal_calendar_period(
    account_id: UUID,
    use_case: Annotated[AddPersonalCalendarPeriod, Depends(build_add_personal_calendar_period)],
    body: Annotated[AddPersonalCalendarPeriodBody, Body(...)],
) -> ApiSuccessResponse[PersonalCalendarPeriodItemSerializer] | ApiErrorResponse:
    try:
        item = await use_case(
            AddPersonalCalendarPeriodCommand(
                account_id=account_id,
                period_name=body.period_name,
                period_start=body.period_start,
                period_end=body.period_end,
                is_date_flexible=body.is_date_flexible,
                holiday_types=body.holiday_types,
            )
        )
    except CustomerPersonalCalendarError as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PersonalCalendarPeriodItemSerializer.from_dto(item),
    )


@customer_personal_calendar_router.post(
    "/holiday-types/view",
    response_model=ApiSuccessResponse[HolidayTypeListSerializer],
    status_code=200,
)
async def view_personal_calendar_holiday_types(
    use_case: Annotated[
        GetPersonalCalendarHolidayTypes,
        Depends(build_get_personal_calendar_holiday_types),
    ],
) -> ApiSuccessResponse[HolidayTypeListSerializer]:
    holiday_types = await use_case()
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=HolidayTypeListSerializer.from_dto(holiday_types),
    )


@customer_personal_calendar_router.post(
    "/{account_id}/view",
    response_model=ApiSuccessResponse[PersonalCalendarConsolidatedViewSerializer],
    status_code=200,
)
async def view_personal_calendar(
    account_id: UUID,
    use_case: Annotated[
        GetPersonalCalendarConsolidatedView,
        Depends(build_get_personal_calendar_consolidated_view),
    ],
) -> ApiSuccessResponse[PersonalCalendarConsolidatedViewSerializer]:
    consolidated_view = await use_case(account_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PersonalCalendarConsolidatedViewSerializer.from_dto(consolidated_view),
    )
