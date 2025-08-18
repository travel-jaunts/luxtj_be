import os

DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
DB_DSN: str = os.getenv(
    "DB_DSN",
    ""
)
