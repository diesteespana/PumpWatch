"""
Contract deployment classifier.

Deterministic: when a transaction has an empty 'to' field, Ethereum
interprets this as a contract creation. Confidence is 1.0.
"""
from app.blockchain.chain_service import EnrichedTransfer
from app.core.constants import ZERO_ADDRESS
from app.events.interfaces import EventClassifier
from app.events.types import BaseEvent, EventType


class ContractDeploymentClassifier(EventClassifier):
    @property
    def event_type(self) -> str:
        return EventType.CONTRACT_DEPLOYMENT

    def classify(self, transfer: EnrichedTransfer) -> BaseEvent | None:
        if not transfer.is_contract_creation:
            return None

        return BaseEvent(
            event_type=EventType.CONTRACT_DEPLOYMENT,
            blockchain=transfer.chain,
            tx_hash=transfer.tx_hash,
            block_number=transfer.block_number,
            timestamp=transfer.timestamp,
            wallet_address=transfer.from_address,
            token_symbol="ETH",
            token_contract=ZERO_ADDRESS,
            usd_value=transfer.usd_value,
            confidence_score=1.0,
            explanation=(
                f"Smart contract deployed by {transfer.from_address[:10]}… "
                f"in tx {transfer.tx_hash[:12]}…"
            ),
            raw_value=transfer.token_amount,
            metadata={"deployer": transfer.from_address, "input_length": len(transfer.input_data)},
        )
