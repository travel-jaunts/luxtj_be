from uuid import uuid4

from fastapi import APIRouter

from .serializer import NewUserDetails, UserSignupResponse

user_router = APIRouter(prefix="/user", tags=["user"])


@user_router.post("/account/signup", response_model=UserSignupResponse)
async def biz_user_signup(new_user_details: NewUserDetails) -> UserSignupResponse:
    return UserSignupResponse(
        user_id=str(
            uuid4()
        )  # This should be replaced with actual logic to create a user
    )
