class AccountAuthError(Exception):
    pass


class InvalidAccountStatusError(AccountAuthError):
    pass


class OtpDeliveryUnavailableError(AccountAuthError):
    pass


class InvalidRefreshTokenError(AccountAuthError):
    pass


class OtpChallengeNotFoundError(AccountAuthError):
    pass


class OtpInvalidError(AccountAuthError):
    pass


class OtpExpiredError(AccountAuthError):
    pass


class OtpConsumedError(AccountAuthError):
    pass


class OtpAttemptsExceededError(AccountAuthError):
    pass


class AccountProfileError(Exception):
    pass


class ProfileNotFoundError(AccountProfileError):
    pass


class FrequentTravellerNotFoundError(AccountProfileError):
    pass


class InvalidProfileFieldError(AccountProfileError):
    pass


class AlbumNotFoundError(AccountProfileError):
    pass


class ImageNotFoundError(AccountProfileError):
    pass


class SystemAlbumImmutableError(AccountProfileError):
    pass


class InvalidProfilePictureError(AccountProfileError):
    pass
