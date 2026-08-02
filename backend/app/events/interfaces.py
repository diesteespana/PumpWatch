"""
Detection engine interfaces.

Milestone 4 implements these. They are defined here so Milestone 3 DB models
and Milestone 5 notification engine can depend on them today.
"""
from abc import ABC, abstractmethod

from app.blockchain.interfaces import RawTransaction, TokenTransfer
from app.events.types import BaseEvent


class EventClassifier(ABC):
    """
    Classifies a raw blockchain event into a typed BaseEvent (or None).

    Each classifier handles exactly one event type (SRP).
    The detection engine runs all classifiers and collects results.
    """

    @abstractmethod
    def classify(
        self,
        transaction: RawTransaction | None,
        token_transfer: TokenTransfer | None,
        usd_value: float,
    ) -> BaseEvent | None:
        """Return a BaseEvent if this classifier fires, else None."""


class DetectionEngine(ABC):
    """
    Orchestrates all classifiers over a stream of blockchain data.

    Implementations run classifiers, deduplicate, and persist events.
    """

    @abstractmethod
    async def process_transactions(
        self,
        transactions: list[RawTransaction],
        token_transfers: list[TokenTransfer],
    ) -> list[BaseEvent]:
        """Process a batch and return all detected events."""

    @abstractmethod
    async def run_cycle(self) -> int:
        """
        Fetch latest blockchain data and process it.
        Returns the number of events detected.
        Called by the scheduler on each poll interval.
        """


class WalletScorer(ABC):
    """
    AI interface for wallet reputation scoring.

    Milestone 9 implementation. Defined here so Milestone 3 DB schema
    includes the wallet_scores table from day one.
    """

    @abstractmethod
    async def score_wallet(self, wallet_address: str) -> float:
        """Return a 0.0–1.0 reputation score for a wallet."""

    @abstractmethod
    async def get_wallet_insights(self, wallet_address: str) -> list[str]:
        """Return human-readable insights about a wallet's historical behaviour."""


class MarketInsightEngine(ABC):
    """
    AI interface for market-level pattern recognition.

    Milestone 9 implementation.
    """

    @abstractmethod
    async def explain_event(self, event: BaseEvent) -> str:
        """Return an AI-generated explanation enriching a detected event."""

    @abstractmethod
    async def get_token_sentiment(self, token_contract: str) -> str:
        """Return a brief AI-generated sentiment summary for a token."""
