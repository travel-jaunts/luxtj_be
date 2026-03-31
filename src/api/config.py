import os

from api.version import __version__ as api_version

VERSION: str = api_version
ENVIRONMENT: str = os.getenv("LTJBE_ENV", "unknown")
OTEL_SERVICE_NAME: str = f"luxtj-be-{ENVIRONMENT}"
OTEL_ENDPOINT: str | None = os.getenv("LTJBE_OTLP_ENDPOINT")
