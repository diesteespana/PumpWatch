"""
Detection engine interfaces.

EventClassifier now takes EnrichedTransfer (defined in M2) instead of the
original (RawTransaction, TokenTransfer, usd_value) triple. EnrichedTransfer
already carries USD value, exchange labels, and token metadata — classifiers
need no additional enrichment.
"""
from abc import ABC, abstractmethod

from app.events.types import BaseEvent


class EventClassifier(ABC):
    """
    Classifies one EnrichedTransfer into a BaseEvent (or None).

    Each classifier is responsible for exactly one event type (SRP).
    A single transfer can match multiple classifiers — the engine collects all.
    Implementations must be stateless and side-effect-free.
    """

    @property
    @abstractmethod
    def event_type(self) -> str:
        """The EventType string this classifier produces."""

    @abstractmethod
    def classify(self, transfer: "EnrichedTransfer") -> BaseEvent | None:  # type: ignore[name-defined]
        """Return a BaseEvent if this classifier fires, else None."""


class DetectionEngine(ABC):
    """
    Orchestrates all classifiers over a batch of enriched transfers.

    Handles deduplication and persistence; classifiers stay pure.
    """

    @abstractmethod
    async def process_transfers(
        self, transfers: list["EnrichedTransfer"]  # type: ignore[name-defined]
    ) -> list[BaseEvent]:
        """
        Run every classifier on every transfer.
        Persist new events, skip duplicates, return the full detected set.
        """

    @abstractmethod
    async def run_cycle(self) -> int:
        """
        Fetch new blockchain data and run the full detection pass.
        Returns the count of newly detected events.
        Called by the scheduler on each poll interval.
        """


class WalletScorer(ABC):
    """AI interface for wallet reputation scoring — Milestone 9."""

    @abstractmethod
    async def score_wallet(self, wallet_address: str) -> float:
        """Return a 0.0–1.0 reputation score."""

    @abstractmethod
    async def get_wallet_insights(self, wallet_address: str) -> list[str]:
        """Return human-readable observations about a wallet's history."""


class MarketInsightEngine(ABC):
    """AI interface for market-level pattern recognition — Milestone 9."""

    @abstractmethod
    async def explain_event(self, event: BaseEvent) -> str:
        """Return an AI-generated explanation enriching a detected event."""

    @abstractmethod
    async def get_token_sentiment(self, token_contract: str) -> str:
        """Return a brief AI-generated sentiment summary for a token."""
