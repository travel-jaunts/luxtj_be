import base64
import json
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

_JWT_DEV_SECRET = "insecure-dev-secret"
_JWT_DEV_ACCOUNT_SECRET = "insecure-dev-account-secret"
_JWT_DEV_IDENTITY_SECRET = "insecure-dev-identity-secret"
AUTH_JWT_ALGORITHM: str = os.getenv("LTJBE_AUTH_JWT_ALGORITHM", "HS256")
AUTH_JWT_ALLOWED_ALGORITHMS: tuple[str, ...] = tuple(
    item.strip()
    for item in os.getenv("LTJBE_AUTH_JWT_ALLOWED_ALGORITHMS", AUTH_JWT_ALGORITHM).split(",")
    if item.strip()
)
AUTH_JWT_CLOCK_SKEW_SECONDS: int = int(os.getenv("LTJBE_AUTH_JWT_CLOCK_SKEW_SECONDS", "30"))
AUTH_ACCOUNT_JWT_ISSUER: str = os.getenv("LTJBE_AUTH_ACCOUNT_JWT_ISSUER", "luxtj-account-auth")
AUTH_ACCOUNT_JWT_AUDIENCE: str = os.getenv("LTJBE_AUTH_ACCOUNT_JWT_AUDIENCE", "luxtj-account")
AUTH_ACCOUNT_JWT_ACTIVE_KID: str = os.getenv("LTJBE_AUTH_ACCOUNT_JWT_ACTIVE_KID", "account-v1")
AUTH_ACCOUNT_JWT_SECRET: str = os.getenv("LTJBE_AUTH_ACCOUNT_JWT_SECRET", _JWT_DEV_ACCOUNT_SECRET)
AUTH_IDENTITY_JWT_ISSUER: str = os.getenv("LTJBE_AUTH_IDENTITY_JWT_ISSUER", "luxtj-identity-auth")
AUTH_IDENTITY_JWT_AUDIENCE: str = os.getenv("LTJBE_AUTH_IDENTITY_JWT_AUDIENCE", "luxtj")
AUTH_IDENTITY_JWT_ACTIVE_KID: str = os.getenv("LTJBE_AUTH_IDENTITY_JWT_ACTIVE_KID", "identity-v1")
AUTH_IDENTITY_JWT_SECRET: str = os.getenv(
    "LTJBE_AUTH_IDENTITY_JWT_SECRET", _JWT_DEV_IDENTITY_SECRET
)


def _jwt_keys(variable: str, active_kid: str, fallback_secret: str) -> dict[str, str]:
    raw = os.getenv(variable, "").strip()
    if not raw:
        return {active_kid: fallback_secret}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict) or not all(
        isinstance(key, str) and isinstance(value, str) and value for key, value in parsed.items()
    ):
        raise ValueError(f"{variable} must be a JSON object of key IDs to secrets")
    return parsed


AUTH_ACCOUNT_JWT_KEYS: dict[str, str] = _jwt_keys(
    "LTJBE_AUTH_ACCOUNT_JWT_KEYS", AUTH_ACCOUNT_JWT_ACTIVE_KID, AUTH_ACCOUNT_JWT_SECRET
)
AUTH_IDENTITY_JWT_KEYS: dict[str, str] = _jwt_keys(
    "LTJBE_AUTH_IDENTITY_JWT_KEYS", AUTH_IDENTITY_JWT_ACTIVE_KID, AUTH_IDENTITY_JWT_SECRET
)

if "none" in AUTH_JWT_ALLOWED_ALGORITHMS:
    raise ValueError("The JWT algorithm allowlist must not include none")


def validate_jwt_configuration() -> None:
    if ENVIRONMENT not in {"production", "prod"}:
        return
    if AUTH_JWT_ALGORITHM not in AUTH_JWT_ALLOWED_ALGORITHMS:
        raise RuntimeError("Configured JWT algorithm is not in the allowed algorithm list")
    if not AUTH_ACCOUNT_JWT_KEYS.get(AUTH_ACCOUNT_JWT_ACTIVE_KID):
        raise RuntimeError("Account JWT active key is missing")
    if not AUTH_IDENTITY_JWT_KEYS.get(AUTH_IDENTITY_JWT_ACTIVE_KID):
        raise RuntimeError("Identity JWT active key is missing")
    if set(AUTH_ACCOUNT_JWT_KEYS.values()) & set(AUTH_IDENTITY_JWT_KEYS.values()):
        raise RuntimeError("Account and identity JWT keys must be different")
    if AUTH_ACCOUNT_JWT_ISSUER == AUTH_IDENTITY_JWT_ISSUER:
        raise RuntimeError("Account and identity JWT issuers must be different")
    if AUTH_ACCOUNT_JWT_AUDIENCE == AUTH_IDENTITY_JWT_AUDIENCE:
        raise RuntimeError("Account and identity JWT audiences must be different")
    if any(
        secret in {_JWT_DEV_SECRET, _JWT_DEV_ACCOUNT_SECRET, _JWT_DEV_IDENTITY_SECRET}
        for secret in (*AUTH_ACCOUNT_JWT_KEYS.values(), *AUTH_IDENTITY_JWT_KEYS.values())
    ):
        raise RuntimeError("Production JWT keys must not use development defaults")


AUTH_ACCESS_TOKEN_TTL_SECONDS: int = int(os.getenv("LTJBE_AUTH_ACCESS_TOKEN_TTL_SECONDS", "900"))
AUTH_REFRESH_TOKEN_TTL_SECONDS: int = int(
    os.getenv("LTJBE_AUTH_REFRESH_TOKEN_TTL_SECONDS", "2592000")
)
AUTH_REFRESH_SESSION_RETENTION_SECONDS: int = int(
    os.getenv("LTJBE_AUTH_REFRESH_SESSION_RETENTION_SECONDS", "7776000")
)
AUTH_REFRESH_SESSION_CLEANUP_INTERVAL_SECONDS: int = int(
    os.getenv("LTJBE_AUTH_REFRESH_SESSION_CLEANUP_INTERVAL_SECONDS", "3600")
)
AUTH_PASSWORD_RESET_TTL_SECONDS: int = int(
    os.getenv("LTJBE_AUTH_PASSWORD_RESET_TTL_SECONDS", "3600")
)
AUTH_OTP_PEPPER: str = os.getenv("LTJBE_AUTH_OTP_PEPPER", "insecure-dev-pepper")
AUTH_OTP_TTL_SECONDS: int = int(os.getenv("LTJBE_AUTH_OTP_TTL_SECONDS", "300"))
AUTH_OTP_MAX_ATTEMPTS: int = int(os.getenv("LTJBE_AUTH_OTP_MAX_ATTEMPTS", "5"))
AUTH_OTP_ALLOW_TEST_SENDER: bool = (
    os.getenv("LTJBE_AUTH_OTP_ALLOW_TEST_SENDER", "false").lower() == "true"
)

# Fernet keys for PII at rest. First key encrypts; the rest only decrypt, enabling rotation.
_PII_DEV_KEY: str = base64.urlsafe_b64encode(b"luxtj-insecure-dev-pii-key-00000").decode()
PII_ENCRYPTION_KEYS: list[str] = [
    key.strip() for key in os.getenv("LTJBE_PII_ENCRYPTION_KEYS", "").split(",") if key.strip()
] or [_PII_DEV_KEY]


def validate_pii_encryption_configuration() -> None:
    if ENVIRONMENT not in {"production", "prod"}:
        return
    if _PII_DEV_KEY in PII_ENCRYPTION_KEYS:
        raise RuntimeError("Production PII encryption keys must not use the development default")


S3_ENDPOINT_URL: str = os.getenv("LTJBE_S3_ENDPOINT_URL", "").strip()
S3_REGION: str = os.getenv("LTJBE_S3_REGION", "us-east-1")
S3_BUCKET: str = os.getenv("LTJBE_S3_BUCKET", "luxtj-dev")
S3_ACCESS_KEY_ID: str = os.getenv("LTJBE_S3_ACCESS_KEY_ID", "")
S3_SECRET_ACCESS_KEY: str = os.getenv("LTJBE_S3_SECRET_ACCESS_KEY", "")
S3_UPLOAD_URL_TTL_SECONDS: int = int(os.getenv("LTJBE_S3_UPLOAD_URL_TTL_SECONDS", "900"))
S3_DOWNLOAD_URL_TTL_SECONDS: int = int(os.getenv("LTJBE_S3_DOWNLOAD_URL_TTL_SECONDS", "900"))


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
