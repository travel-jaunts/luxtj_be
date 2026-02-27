from dataclasses import dataclass
import os

from app.__version__ import __version__


@dataclass(frozen=True)
class Settings:
    # constants
    app_title: str = "LuxTJ Backend"
    app_version: str = __version__

    # env vars (with defaults)
    app_log_level: str = "INFO"
    app_log_requests: bool = False
    app_log_responses: bool = False
    app_exec_env: str = "development"
    app_auth_enabled: bool = False


def get_settings() -> Settings:
    _env_debug_flag: bool = os.getenv("LTJBE_DEBUG", "False").lower() in ("true", "1", "t")
    _env_exec_env: str = os.getenv("LTJBE_ENV", "development").lower()
    _env_auth_flag: bool = os.getenv("LTJBE_AUTH_ENABLED", "True").lower() in ("true", "1", "t")
    _env_log_requests_flag: bool = os.getenv("LTJBE_LOG_REQUESTS", "False").lower() in (
        "true",
        "1",
        "t",
    )
    _env_log_responses_flag: bool = os.getenv("LTJBE_LOG_RESPONSES", "False").lower() in (
        "true",
        "1",
        "t",
    )

    return Settings(
        app_log_level="DEBUG"
        if _env_debug_flag
        else ("INFO" if _env_exec_env == "production" else "DEBUG"),
        app_log_requests=_env_debug_flag if _env_debug_flag else _env_log_requests_flag,
        app_log_responses=_env_debug_flag if _env_debug_flag else _env_log_responses_flag,
        app_exec_env=_env_exec_env,
        app_auth_enabled=_env_auth_flag,
    )
