/**
 * Shared TypeScript types mirroring the backend Pydantic schemas.
 * Keep in sync with backend/app/schemas/*.py as milestones progress.
 */

export type EventType =
  | "whale_buy"
  | "whale_sell"
  | "exchange_deposit"
  | "exchange_withdrawal"
  | "liquidity_added"
  | "liquidity_removed"
  | "contract_deployment"
  | "token_mint"
  | "token_burn"
  | "large_swap"
  | "smart_money_activity"
  | "wallet_accumulation"
  | "wallet_distribution";

export interface OnChainEvent {
  id: string;
  event_type: EventType;
  blockchain: string;
  tx_hash: string;
  block_number: number;
  timestamp: string; // ISO 8601
  wallet_address: string;
  token_symbol: string;
  token_contract: string;
  usd_value: string; // Decimal serialised as string
  confidence_score: number;
  explanation: string;
}

export interface HealthStatus {
  status: "ok" | "degraded";
  environment: string;
  database: boolean;
  blockchain_provider: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}
