"""
Threshold configuration for the detection engine.

Injected into classifiers so values come from settings, not magic numbers.
Future: load per-user overrides from DB and merge with global defaults.
"""
from dataclasses import dataclass

from app.core.constants import DEFAULT_WHALE_THRESHOLD_USD


@dataclass(frozen=True)
class ThresholdConfig:
    whale_threshold_usd: float = DEFAULT_WHALE_THRESHOLD_USD
    large_swap_threshold_usd: float = 50_000.0
    liquidity_threshold_usd: float = 25_000.0
    accumulation_min_transfers: int = 3        # transfers in one batch to flag accumulation
    min_confidence_to_persist: float = 0.5    # discard low-confidence noise

    @classmethod
    def from_settings(cls) -> "ThresholdConfig":
        from app.core.config import get_settings
        s = get_settings()
        return cls(whale_threshold_usd=s.whale_threshold_usd)
