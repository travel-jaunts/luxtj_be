from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends

from luxtj.contexts.customer.application.commands import (
    AddBucketListItemCommand,
    DeleteBucketListItemCommand,
    SuggestDestinationsCommand,
    UpdateBucketListItemCommand,
)
from luxtj.contexts.customer.application.queries import GetBucketListQuery
from luxtj.contexts.customer.application.use_cases import (
    AddBucketListItem,
    DeleteBucketListItem,
    GetBucketList,
    SuggestDestinations,
    UpdateBucketListItem,
)
from luxtj.contexts.customer.bootstrap import (
    build_add_bucket_list_item,
    build_delete_bucket_list_item,
    build_get_bucket_list,
    build_suggest_destinations,
    build_update_bucket_list_item,
)
from luxtj.contexts.customer.domain.errors import CustomerBucketListError
from luxtj.contexts.customer.presentation.http.schemas import (
    AddBucketListItemBody,
    BucketListItemSerializer,
    BucketListSerializer,
    DestinationSuggestionResultSerializer,
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
