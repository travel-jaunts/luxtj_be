from typing import Any, Protocol


class ILogger(Protocol):
    def debug(self, message: str, extra: dict[str, Any] | None = None):
        """
        Log a debug message
        """
        ...

    def info(self, message: str, extra: dict[str, Any] | None = None):
        """
        Log an info message
        """
        ...

    def error(self, message: str, extra: dict[str, Any] | None = None):
        """
        Log an error message
        """
        ...

    def critical(self, message: str, extra: dict[str, Any] | None = None):
        """
        Log a critical message
        """
        ...
