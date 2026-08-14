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
