from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request

from luxtj.contexts.acquisition.application.commands import RegisterWaitlistEntryCommand
from luxtj.contexts.acquisition.application.use_cases import RegisterWaitlistEntry
from luxtj.contexts.acquisition.bootstrap import build_register_waitlist_entry
from luxtj.contexts.acquisition.domain.errors import DuplicateEmailError
from luxtj.contexts.acquisition.domain.value_objects import AcquisitionContext, Email
from luxtj.contexts.acquisition.presentation.http.schemas import (
    RegisterWaitlistEntryBody,
    WaitlistEntrySerializer,
)
from luxtj.shared_kernel.presentation.http.schemas import (
    ApiErrorResponse,
    ApiSuccessResponse,
    RequestProcessStatus,
)

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


def _extract_acquisition_context(
    request: Request, body: RegisterWaitlistEntryBody
) -> AcquisitionContext:
    forwarded_for = request.headers.get("x-forwarded-for")
    ip = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else (request.client.host if request.client else None)
    )
    return AcquisitionContext(
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer"),
        accept_language=request.headers.get("accept-language"),
        utm_source=request.query_params.get("utm_source"),
        utm_medium=request.query_params.get("utm_medium"),
        utm_campaign=request.query_params.get("utm_campaign"),
        utm_term=request.query_params.get("utm_term"),
        utm_content=request.query_params.get("utm_content"),
    )


@router.post(
    "/register",
    response_model=ApiSuccessResponse[WaitlistEntrySerializer] | ApiErrorResponse,
    status_code=200,
    summary="Join the waitlist",
    name="Register Waitlist Entry",
)
async def register_waitlist_entry(
    request: Request,
    use_case: Annotated[RegisterWaitlistEntry, Depends(build_register_waitlist_entry)],
    body: Annotated[RegisterWaitlistEntryBody, Body(...)],
) -> ApiSuccessResponse[WaitlistEntrySerializer] | ApiErrorResponse:
    try:
        email = Email(body.email)
    except ValueError as exc:
        return ApiErrorResponse(error_message=str(exc))

    command = RegisterWaitlistEntryCommand(
        name=body.name,
        email=email,
        source=body.source,
        referral_code=body.referral_code,
        acquisition_context=_extract_acquisition_context(request, body),
    )

    try:
        dto = await use_case(command)
    except DuplicateEmailError as exc:
        return ApiErrorResponse(error_message=str(exc))

    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=WaitlistEntrySerializer.from_dto(dto),
    )
