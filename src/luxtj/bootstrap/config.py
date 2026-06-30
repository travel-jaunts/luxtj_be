import os

from luxtj._version import __version__

VERSION: str = __version__
ENVIRONMENT: str = os.getenv("LTJBE_ENV", "unknown")
OTEL_SERVICE_NAME: str = f"luxtj-be-{ENVIRONMENT}"
OTEL_ENDPOINT: str | None = os.getenv("LTJBE_OTLP_ENDPOINT")
DATABASE_URL: str = os.environ["LTJBE_DATABASE_URL"]
DATABASE_ECHO: bool = os.getenv("LTJBE_DATABASE_ECHO", "false").lower() == "true"
DATABASE_AUTO_CREATE: bool = os.getenv("LTJBE_DATABASE_AUTO_CREATE", "false").lower() == "true"

AUTH_JWT_SECRET: str = os.getenv("LTJBE_AUTH_JWT_SECRET", "insecure-dev-secret")
AUTH_JWT_ALGORITHM: str = os.getenv("LTJBE_AUTH_JWT_ALGORITHM", "HS256")
AUTH_ACCESS_TOKEN_TTL_SECONDS: int = int(os.getenv("LTJBE_AUTH_ACCESS_TOKEN_TTL_SECONDS", "900"))
AUTH_REFRESH_TOKEN_TTL_SECONDS: int = int(
    os.getenv("LTJBE_AUTH_REFRESH_TOKEN_TTL_SECONDS", "2592000")
)
AUTH_OTP_PEPPER: str = os.getenv("LTJBE_AUTH_OTP_PEPPER", "insecure-dev-pepper")
AUTH_OTP_TTL_SECONDS: int = int(os.getenv("LTJBE_AUTH_OTP_TTL_SECONDS", "300"))
AUTH_OTP_MAX_ATTEMPTS: int = int(os.getenv("LTJBE_AUTH_OTP_MAX_ATTEMPTS", "5"))

TWILIO_ACCOUNT_SID: str | None = os.getenv("LTJBE_TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN: str | None = os.getenv("LTJBE_TWILIO_AUTH_TOKEN")
TWILIO_FROM_PHONE: str | None = os.getenv("LTJBE_TWILIO_FROM_PHONE")
ENABLE_OUTBOX_PROJECTOR: bool = (
    os.getenv("LTJBE_ENABLE_OUTBOX_PROJECTOR", "false").lower() == "true"
)
