import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import exp
from pathlib import Path
from types import MappingProxyType
from typing import Self

from .config import FEATURE_SCHEMA_VERSION
from .exceptions import RankingModelError
from .features import FEATURE_NAMES
from .models import FeatureVector


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = exp(-value)
        return 1.0 / (1.0 + z)
    z = exp(value)
    return z / (1.0 + z)


@dataclass(frozen=True, slots=True)
class LinearRankingModel:
    model_version: str
    feature_schema_version: str
    feature_names: tuple[str, ...]
    weights: tuple[float, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    bias: float = 0.0
    training_examples: int = 0
    approved_for_serving: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_version.strip():
            raise RankingModelError("model_version is required")
        if self.feature_schema_version != FEATURE_SCHEMA_VERSION:
            raise RankingModelError(
                f"Feature schema mismatch: expected {FEATURE_SCHEMA_VERSION}, "
                f"got {self.feature_schema_version}"
            )
        if self.feature_names != FEATURE_NAMES:
            raise RankingModelError("Model feature names do not match the serving feature schema")
        lengths = {
            len(self.feature_names),
            len(self.weights),
            len(self.means),
            len(self.scales),
        }
        if len(lengths) != 1:
            raise RankingModelError("Model feature arrays must have equal lengths")
        if any(scale <= 0.0 for scale in self.scales):
            raise RankingModelError("Model scales must be positive")
        if self.training_examples < 0:
            raise RankingModelError("training_examples cannot be negative")
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))

    def predict(self, features: FeatureVector) -> float:
        if features.names != self.feature_names:
            raise RankingModelError("Runtime FeatureVector is incompatible with the model")
        standardized = tuple(
            (value - mean) / scale
            for value, mean, scale in zip(
                features.values,
                self.means,
                self.scales,
                strict=True,
            )
        )
        logit = self.bias + sum(
            weight * value for weight, value in zip(self.weights, standardized, strict=True)
        )
        return _sigmoid(logit)

    def to_dict(self) -> dict[str, object]:
        return {
            "modelVersion": self.model_version,
            "featureSchemaVersion": self.feature_schema_version,
            "featureNames": list(self.feature_names),
            "weights": list(self.weights),
            "means": list(self.means),
            "scales": list(self.scales),
            "bias": self.bias,
            "trainingExamples": self.training_examples,
            "approvedForServing": self.approved_for_serving,
            "createdAt": self.created_at,
            "metrics": dict(self.metrics),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> Self:
        try:
            return cls(
                model_version=str(payload["modelVersion"]),
                feature_schema_version=str(payload["featureSchemaVersion"]),
                feature_names=tuple(str(item) for item in payload["featureNames"]),
                weights=tuple(float(item) for item in payload["weights"]),
                means=tuple(float(item) for item in payload["means"]),
                scales=tuple(float(item) for item in payload["scales"]),
                bias=float(payload.get("bias", 0.0)),
                training_examples=int(payload.get("trainingExamples", 0)),
                approved_for_serving=bool(payload.get("approvedForServing", False)),
                created_at=str(payload.get("createdAt", datetime.now(UTC).isoformat())),
                metrics={
                    str(key): float(value)
                    for key, value in dict(payload.get("metrics", {})).items()
                },
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RankingModelError("Invalid ranking-model payload") from exc

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def read_json(cls, path: str | Path) -> Self:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RankingModelError("Unable to read ranking-model artifact") from exc
        if not isinstance(payload, dict):
            raise RankingModelError("Ranking-model artifact must contain a JSON object")
        return cls.from_dict(payload)
