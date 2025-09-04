from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from emporio.user.serializer import NewUserDetails, UserSignupResponse
from emporio.core.context import RequestContext

from emporio.user.service import UserService

user_router = APIRouter()


# @user_router.post("/account/signup", response_model=UserSignupResponse)
# async def biz_user_signup(
#     request: Request,
#     new_user_details: NewUserDetails,
#     db_session: AsyncSession = Depends(RequestContext.get_db_session),
# ) -> UserSignupResponse:
#     print(await UserService.register_new_user())

#     return UserSignupResponse(
#         user_id=str(
#             uuid4()
#         ),  # This should be replaced with actual logic to create a user
#         phone_number=new_user_details.phone_number,
#     )
