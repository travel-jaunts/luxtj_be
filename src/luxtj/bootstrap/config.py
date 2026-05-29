import os

from luxtj._version import __version__

VERSION: str = __version__
ENVIRONMENT: str = os.getenv("LTJBE_ENV", "unknown")
OTEL_SERVICE_NAME: str = f"luxtj-be-{ENVIRONMENT}"
OTEL_ENDPOINT: str | None = os.getenv("LTJBE_OTLP_ENDPOINT")
DATABASE_URL: str = os.environ["LTJBE_DATABASE_URL"]
DATABASE_ECHO: bool = os.getenv("LTJBE_DATABASE_ECHO", "false").lower() == "true"
DATABASE_AUTO_CREATE: bool = os.getenv("LTJBE_DATABASE_AUTO_CREATE", "false").lower() == "true"
