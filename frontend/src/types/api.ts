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
  timestamp: string;
  wallet_address: string;
  token_symbol: string;
  token_contract: string;
  usd_value: string;
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

export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_verified: boolean;
  subscription_tier: string;
  created_at: string;
  updated_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface Wallet {
  id: string;
  address: string;
  chain: string;
  label: string;
  is_exchange: boolean;
  exchange_name: string | null;
  custom_label: string | null;
  threshold_usd: string | null;
  created_at: string;
}

export interface Token {
  id: string;
  contract_address: string;
  chain: string;
  symbol: string;
  name: string | null;
  threshold_usd: string | null;
  created_at: string;
}

export type AlertEventType = EventType;

export interface Alert {
  id: string;
  name: string;
  is_active: boolean;
  event_types: AlertEventType[];
  wallet_addresses: string[];
  token_contracts: string[];
  min_usd_value: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlertCreate {
  name: string;
  event_types: AlertEventType[];
  wallet_addresses?: string[];
  token_contracts?: string[];
  min_usd_value?: string | null;
}

export interface AlertUpdate {
  name?: string;
  is_active?: boolean;
  event_types?: AlertEventType[];
  wallet_addresses?: string[];
  token_contracts?: string[];
  min_usd_value?: string | null;
}

export type NotificationChannel = "telegram" | "discord" | "email";

// ── Analytics (M8) ────────────────────────────────────────────────────────────

export interface VolumeDataPoint {
  date: string;  // YYYY-MM-DD
  volume: number;
}

export interface TopToken {
  symbol: string;
  contract: string;
  volume: number;
  count: number;
}

export interface ScoreBreakdown {
  volume: number;
  activity: number;
  diversity: number;
  recency: number;
}

export interface WalletAnalytics {
  address: string;
  chain: string;
  total_events: number;
  total_volume_usd: number;
  event_type_breakdown: Record<string, number>;
  top_tokens: TopToken[];
  first_seen: string | null;
  last_seen: string | null;
  volume_over_time: VolumeDataPoint[];
  score: number | null;
  score_breakdown: ScoreBreakdown | null;
  insights: string[];
}

export interface WalletRankingItem {
  rank: number;
  address: string;
  label: string;
  score: number;
  trade_count: number;
  total_volume_usd: number;
  last_seen: string | null;
}

export interface RankingsResponse {
  items: WalletRankingItem[];
  total: number;
}

// ── AI / Predictions (M9) ────────────────────────────────────────────────────

export type SignalDirection = "bullish" | "bearish" | "neutral";

export interface TokenSignal {
  token_contract: string;
  token_symbol: string;
  direction: SignalDirection;
  confidence: number;
  reasoning: string;
  buy_pressure: number;
  sell_pressure: number;
  net_flow_usd: number;
}

export interface TokenSentiment {
  token_contract: string;
  sentiment: string;
}

export interface AIInsights {
  address: string;
  score: number;
  insights: string[];
  ai_powered: boolean;
}

export interface MarketOverview {
  chain: string;
  dominant_direction: SignalDirection;
  total_volume_24h: number;
  top_events: Array<{ address: string; volume: number; events: number }>;
  summary: string;
}

// ── Paper Trading ────────────────────────────────────────────────────────────

export interface PaperPortfolio {
  id: string;
  name: string;
  starting_balance: string;
  current_cash: string;
  is_active: boolean;
  created_at: string;
}

export interface PaperPosition {
  id: string;
  portfolio_id: string;
  token_symbol: string;
  token_contract: string;
  chain: string;
  quantity: string;
  avg_entry_price: string;
  current_price: string | null;
  current_value: string | null;
  unrealized_pnl: string | null;
  unrealized_pnl_pct: string | null;
}

export interface PaperTrade {
  id: string;
  portfolio_id: string;
  trade_type: "buy" | "sell";
  token_symbol: string;
  token_contract: string;
  chain: string;
  quantity: string;
  price_at_execution: string;
  total_value: string;
  realized_pnl: string | null;
  trigger: "manual" | "signal";
  executed_at: string;
}

export interface PortfolioSummary {
  portfolio: PaperPortfolio;
  positions: PaperPosition[];
  total_position_value: string;
  total_equity: string;
  total_return: string;
  total_return_pct: string;
  realized_pnl: string;
}

// ── Strategy & Risk ──────────────────────────────────────────────────────────

export interface RiskProfile {
  id: string;
  portfolio_id: string;
  stop_loss_pct: string;
  take_profit_pct: string;
  max_position_pct: string;
  max_drawdown_pct: string;
  updated_at: string;
}

export type SignalDirectionFilter = "bullish" | "bearish" | "any";

export interface Strategy {
  id: string;
  portfolio_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  token_contract: string;
  token_symbol: string;
  chain: string;
  signal_direction: SignalDirectionFilter;
  min_confidence: string;
  action: "buy" | "sell";
  size_pct: string;
  created_at: string;
}

export interface StrategyRun {
  id: string;
  strategy_id: string;
  triggered: boolean;
  signal_direction: string | null;
  signal_confidence: string | null;
  trade_id: string | null;
  reason: string | null;
  evaluated_at: string;
}

export interface NotificationSetting {
  id: string;
  channel: NotificationChannel;
  is_active: boolean;
  config: Record<string, string>;
  created_at: string;
  updated_at: string;
}
