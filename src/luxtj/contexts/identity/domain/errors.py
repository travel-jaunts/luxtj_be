class IdentityError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AuthenticationError(IdentityError):
    pass


class AuthorizationError(IdentityError):
    pass


class NotFoundError(IdentityError):
    pass


class ConflictError(IdentityError):
    pass


class ValidationError(IdentityError):
    pass
