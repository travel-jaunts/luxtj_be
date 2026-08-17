from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException

from luxtj.contexts.account.application.gallery_commands import (
    ConfirmImageUploadCommand,
    CreateAlbumCommand,
    GetAlbumCommand,
    ListPublicAlbumsCommand,
    RemoveAlbumCommand,
    RemoveGalleryImageCommand,
    RequestImageUploadCommand,
    UpdateAlbumCommand,
    UpdateGalleryImageCommand,
)
from luxtj.contexts.account.application.gallery_use_cases import (
    ConfirmImageUpload,
    CreateAlbum,
    GetAlbum,
    ListAlbums,
    ListPublicAlbums,
    RemoveAlbum,
    RemoveGalleryImage,
    RequestImageUpload,
    UpdateAlbum,
    UpdateGalleryImage,
)
from luxtj.contexts.account.bootstrap import (
    build_confirm_image_upload,
    build_create_album,
    build_get_album,
    build_list_albums,
    build_list_public_albums,
    build_remove_album,
    build_remove_gallery_image,
    build_request_image_upload,
    build_update_album,
    build_update_gallery_image,
)
from luxtj.contexts.account.domain.errors import (
    AccountProfileError,
    AlbumNotFoundError,
    ImageNotFoundError,
    SystemAlbumImmutableError,
)
from luxtj.contexts.account.domain.patch import UNSET, Patch
from luxtj.contexts.account.presentation.http.dependencies import (
    AccountPrincipal,
    get_current_account_principal,
)
from luxtj.contexts.account.presentation.http.gallery_schemas import (
    AlbumDetailSerializer,
    AlbumIdBody,
    AlbumInfoSerializer,
    AlbumListSerializer,
    ConfirmImageUploadBody,
    CreateAlbumBody,
    ImageIdBody,
    ImageSerializer,
    RequestImageUploadBody,
    TargetAccountBody,
    UpdateAlbumBody,
    UpdateImageBody,
    UploadIntentSerializer,
)
from luxtj.contexts.account.presentation.http.profile_schemas import patched
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiErrorResponse,
    ApiSuccessResponse,
    RequestProcessStatus,
)

account_gallery_router = APIRouter(prefix="/account/gallery", tags=["account-gallery"])


def _raise_for(exc: AccountProfileError) -> None:
    if isinstance(exc, AlbumNotFoundError | ImageNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, SystemAlbumImmutableError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    raise HTTPException(status_code=422, detail=str(exc)) from exc


def _uuid(raw: str, label: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid {label}") from exc


@account_gallery_router.post(
    "/albums/list",
    response_model=ApiSuccessResponse[AlbumListSerializer] | ApiErrorResponse,
    status_code=200,
)
async def list_albums(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[ListAlbums, Depends(build_list_albums)],
) -> ApiSuccessResponse[AlbumListSerializer] | ApiErrorResponse:
    summaries = await use_case(principal.account_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK, output=AlbumListSerializer.from_dto(summaries)
    )


@account_gallery_router.post(
    "/albums/create",
    response_model=ApiSuccessResponse[AlbumInfoSerializer] | ApiErrorResponse,
    status_code=200,
)
async def create_album(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[CreateAlbum, Depends(build_create_album)],
    body: Annotated[CreateAlbumBody, Body(...)],
) -> ApiSuccessResponse[AlbumInfoSerializer] | ApiErrorResponse:
    try:
        album = await use_case(
            CreateAlbumCommand(
                account_id=principal.account_id,
                name=body.name,
                description=body.description,
                visibility=body.visibility,
            )
        )
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK, output=AlbumInfoSerializer.from_dto(album)
    )


@account_gallery_router.post(
    "/albums/update",
    response_model=ApiSuccessResponse[AlbumInfoSerializer] | ApiErrorResponse,
    status_code=200,
)
async def update_album(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[UpdateAlbum, Depends(build_update_album)],
    body: Annotated[UpdateAlbumBody, Body(...)],
) -> ApiSuccessResponse[AlbumInfoSerializer] | ApiErrorResponse:
    cover_image_id = _uuid(body.cover_image_id, "cover image id") if body.cover_image_id else None
    try:
        album = await use_case(
            UpdateAlbumCommand(
                account_id=principal.account_id,
                album_id=_uuid(body.album_id, "album id"),
                name=patched(body, "name", body.name),
                description=patched(body, "description", body.description),
                visibility=patched(body, "visibility", body.visibility),
                cover_image_id=patched(body, "cover_image_id", cover_image_id),
            )
        )
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK, output=AlbumInfoSerializer.from_dto(album)
    )


@account_gallery_router.post(
    "/albums/remove",
    response_model=ApiSuccessResponse[None] | ApiErrorResponse,
    status_code=200,
)
async def remove_album(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[RemoveAlbum, Depends(build_remove_album)],
    body: Annotated[AlbumIdBody, Body(...)],
) -> ApiSuccessResponse[None] | ApiErrorResponse:
    try:
        await use_case(
            RemoveAlbumCommand(
                account_id=principal.account_id,
                album_id=_uuid(body.album_id, "album id"),
            )
        )
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(status=RequestProcessStatus.OK)


@account_gallery_router.post(
    "/albums/get",
    response_model=ApiSuccessResponse[AlbumDetailSerializer] | ApiErrorResponse,
    status_code=200,
)
async def get_album(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[GetAlbum, Depends(build_get_album)],
    body: Annotated[AlbumIdBody, Body(...)],
) -> ApiSuccessResponse[AlbumDetailSerializer] | ApiErrorResponse:
    try:
        detail = await use_case(
            GetAlbumCommand(
                account_id=principal.account_id,
                album_id=_uuid(body.album_id, "album id"),
            )
        )
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK, output=AlbumDetailSerializer.from_dto(detail)
    )


@account_gallery_router.post(
    "/albums/list-public",
    response_model=ApiSuccessResponse[AlbumListSerializer] | ApiErrorResponse,
    status_code=200,
)
async def list_public_albums(
    _: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[ListPublicAlbums, Depends(build_list_public_albums)],
    body: Annotated[TargetAccountBody, Body(...)],
) -> ApiSuccessResponse[AlbumListSerializer] | ApiErrorResponse:
    summaries = await use_case(
        ListPublicAlbumsCommand(target_account_id=_uuid(body.account_id, "account id"))
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK, output=AlbumListSerializer.from_dto(summaries)
    )


@account_gallery_router.post(
    "/images/upload-intent",
    response_model=ApiSuccessResponse[UploadIntentSerializer] | ApiErrorResponse,
    status_code=200,
)
async def request_image_upload(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[RequestImageUpload, Depends(build_request_image_upload)],
    body: Annotated[RequestImageUploadBody, Body(...)],
) -> ApiSuccessResponse[UploadIntentSerializer] | ApiErrorResponse:
    try:
        intent = await use_case(
            RequestImageUploadCommand(
                account_id=principal.account_id,
                content_type=body.content_type,
                album_id=_uuid(body.album_id, "album id") if body.album_id else None,
            )
        )
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK, output=UploadIntentSerializer.from_dto(intent)
    )


@account_gallery_router.post(
    "/images/confirm",
    response_model=ApiSuccessResponse[ImageSerializer] | ApiErrorResponse,
    status_code=200,
)
async def confirm_image_upload(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[ConfirmImageUpload, Depends(build_confirm_image_upload)],
    body: Annotated[ConfirmImageUploadBody, Body(...)],
) -> ApiSuccessResponse[ImageSerializer] | ApiErrorResponse:
    try:
        view = await use_case(
            ConfirmImageUploadCommand(
                account_id=principal.account_id,
                image_id=_uuid(body.image_id, "image id"),
                width=body.width,
                height=body.height,
                caption=body.caption,
                city_name=body.city_name,
                latitude=body.latitude,
                longitude=body.longitude,
            )
        )
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(status=RequestProcessStatus.OK, output=ImageSerializer.from_dto(view))


@account_gallery_router.post(
    "/images/update",
    response_model=ApiSuccessResponse[None] | ApiErrorResponse,
    status_code=200,
)
async def update_image(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[UpdateGalleryImage, Depends(build_update_gallery_image)],
    body: Annotated[UpdateImageBody, Body(...)],
) -> ApiSuccessResponse[None] | ApiErrorResponse:
    target_album: Patch[UUID] = UNSET
    if "album_id" in body.model_fields_set and body.album_id:
        target_album = _uuid(body.album_id, "album id")
    try:
        await use_case(
            UpdateGalleryImageCommand(
                account_id=principal.account_id,
                image_id=_uuid(body.image_id, "image id"),
                caption=patched(body, "caption", body.caption),
                city_name=patched(body, "city_name", body.city_name),
                latitude=patched(body, "latitude", body.latitude),
                longitude=patched(body, "longitude", body.longitude),
                sort_order=patched(body, "sort_order", body.sort_order),
                album_id=target_album,
            )
        )
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(status=RequestProcessStatus.OK)


@account_gallery_router.post(
    "/images/remove",
    response_model=ApiSuccessResponse[None] | ApiErrorResponse,
    status_code=200,
)
async def remove_image(
    principal: Annotated[AccountPrincipal, Depends(get_current_account_principal)],
    use_case: Annotated[RemoveGalleryImage, Depends(build_remove_gallery_image)],
    body: Annotated[ImageIdBody, Body(...)],
) -> ApiSuccessResponse[None] | ApiErrorResponse:
    try:
        await use_case(
            RemoveGalleryImageCommand(
                account_id=principal.account_id,
                image_id=_uuid(body.image_id, "image id"),
            )
        )
    except AccountProfileError as exc:
        _raise_for(exc)
    return ApiSuccessResponse(status=RequestProcessStatus.OK)
