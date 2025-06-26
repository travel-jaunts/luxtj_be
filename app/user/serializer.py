from app.core.serializer import BaseSerializer


class NewUserDetails(BaseSerializer):
    phone_number: str


# -----------------------------------------------------------------------------
class UserSignupResponse(BaseSerializer):
    user_id: str
