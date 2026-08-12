import os

from luxtj._version import __version__

VERSION: str = __version__
ENVIRONMENT: str = os.getenv("LTJBE_ENV", "unknown")
OTEL_SERVICE_NAME: str = f"luxtj-be-{ENVIRONMENT}"
OTEL_ENDPOINT: str | None = os.getenv("LTJBE_OTLP_ENDPOINT")
DATABASE_URL: str = os.environ["LTJBE_DATABASE_URL"]
# Hotel CRS + region catalogue DB (may be a different host). Falls back to main DB.
CRS_DATABASE_URL: str = os.getenv("LTJBE_CRS_DATABASE_URL", "").strip() or DATABASE_URL
DATABASE_ECHO: bool = os.getenv("LTJBE_DATABASE_ECHO", "false").lower() == "true"
DATABASE_AUTO_CREATE: bool = os.getenv("LTJBE_DATABASE_AUTO_CREATE", "false").lower() == "true"
ADMIN_CURRENCY: str = os.getenv("LTJBE_ADMIN_CURRENCY", "INR").upper()
PUBLIC_BASE_URL: str = os.getenv("LTJBE_PUBLIC_BASE_URL", "http://localhost:9001").rstrip("/")
BYPASS_PAYMENT: bool = os.getenv("LTJBE_BYPASS_PAYMENT", "false").lower() == "true"
HTTP_MAX_RETRIES: int = int(os.getenv("LTJBE_HTTP_MAX_RETRIES", "2"))
HTTP_DEFAULT_TIMEOUT: float = float(os.getenv("LTJBE_HTTP_DEFAULT_TIMEOUT", "60"))

AUTH_JWT_SECRET: str = os.getenv("LTJBE_AUTH_JWT_SECRET", "insecure-dev-secret")
AUTH_JWT_ALGORITHM: str = os.getenv("LTJBE_AUTH_JWT_ALGORITHM", "HS256")
AUTH_ACCESS_TOKEN_TTL_SECONDS: int = int(os.getenv("LTJBE_AUTH_ACCESS_TOKEN_TTL_SECONDS", "900"))
AUTH_REFRESH_TOKEN_TTL_SECONDS: int = int(
    os.getenv("LTJBE_AUTH_REFRESH_TOKEN_TTL_SECONDS", "2592000")
)
AUTH_PASSWORD_RESET_TTL_SECONDS: int = int(
    os.getenv("LTJBE_AUTH_PASSWORD_RESET_TTL_SECONDS", "3600")
)
AUTH_OTP_PEPPER: str = os.getenv("LTJBE_AUTH_OTP_PEPPER", "insecure-dev-pepper")
AUTH_OTP_TTL_SECONDS: int = int(os.getenv("LTJBE_AUTH_OTP_TTL_SECONDS", "300"))
AUTH_OTP_MAX_ATTEMPTS: int = int(os.getenv("LTJBE_AUTH_OTP_MAX_ATTEMPTS", "5"))

# Bootstrapped on first startup if missing (not configurable via env).
SUPERADMIN_EMAIL: str = "superadmin@luxtj.in"
SUPERADMIN_PASSWORD: str = "Luxtj@123"
SUPERADMIN_FULL_NAME: str = "Super Admin"

ENABLE_OUTBOX_PROJECTOR: bool = (
    os.getenv("LTJBE_ENABLE_OUTBOX_PROJECTOR", "false").lower() == "true"
)

# Comma-separated browser origins allowed to call the API (admin + web).
# Example: https://admin.example.com,https://www.example.com,https://example.com
# In development, CORS allows all origins when this is empty.
CORS_ORIGINS: list[str] = [
    origin.strip().rstrip("/")
    for origin in os.getenv("LTJBE_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
