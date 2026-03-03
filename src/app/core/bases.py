from typing import Tuple, Dict, Any
from abc import ABC, abstractmethod


class SingletonMeta(type):
    _instances: Dict[object, object] = {}

    def __call__(cls, *args: Tuple[Any, ...], **kwargs: Dict[str, Any]) -> object:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class IAsyncCachingProvider(ABC):
    @abstractmethod
    async def get(self, key: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: str, ttl_seconds: int = 0) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError
