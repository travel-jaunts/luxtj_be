import os

from api.version import __version__ as api_version

VERSION: str = api_version
OTEL_SERVICE_NAME: str = "luxtj-be"
ENVIRONMENT: str = os.getenv("LTJBE_ENV", "unknown")
OTEL_ENDPOINT: str | None = os.getenv("LTJBE_OTLP_ENDPOINT")
