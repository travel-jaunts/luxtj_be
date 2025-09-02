from emporio.core.serializer import BaseSerializer


class NewUserDetails(BaseSerializer):
    phone_number: str


# -----------------------------------------------------------------------------
class UserSignupResponse(BaseSerializer):
    user_id: str
    phone_number: str
