from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    # env vars (with defaults)
    app_log_level: str
    app_log_requests: bool
    app_log_responses: bool
    app_exec_env: str
    app_auth_enabled: bool

    app_tourradar_oauth_base_url: str
    app_tourradar_oauth_client_id: str
    app_tourradar_oauth_client_secret: str
    app_tourradar_api_base_url: str

    # constants
    app_title: str = "LuxTJ Backend"
    app_version: str = "0.1.0"


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
    _env_tourradar_oauth_base_url: str = os.getenv("LTJBE_TOURRADAR_OAUTH_BASE_URL", "")
    _env_tourradar_oauth_client_id: str = os.getenv("LTJBE_TOURRADAR_CLIENT_ID", "")
    _env_tourradar_oauth_client_secret: str = os.getenv("LTJBE_TOURRADAR_CLIENT_SECRET", "")
    _env_tourradar_api_base_url: str = os.getenv("LTJBE_TOURRADAR_API_BASE_URL", "")

    return Settings(
        app_log_level="DEBUG"
        if _env_debug_flag
        else ("INFO" if _env_exec_env == "production" else "DEBUG"),
        app_log_requests=_env_debug_flag if _env_debug_flag else _env_log_requests_flag,
        app_log_responses=_env_debug_flag if _env_debug_flag else _env_log_responses_flag,
        app_exec_env=_env_exec_env,
        app_auth_enabled=_env_auth_flag,
        app_tourradar_oauth_base_url=_env_tourradar_oauth_base_url,
        app_tourradar_oauth_client_id=_env_tourradar_oauth_client_id,
        app_tourradar_oauth_client_secret=_env_tourradar_oauth_client_secret,
        app_tourradar_api_base_url=_env_tourradar_api_base_url,
    )
