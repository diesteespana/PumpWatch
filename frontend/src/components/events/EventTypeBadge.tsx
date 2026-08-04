import { clsx } from "clsx";
import type { EventType } from "@/types/api";

const EVENT_META: Record<
  EventType,
  { label: string; color: string; emoji: string }
> = {
  whale_buy: {
    label: "Whale Buy",
    color: "text-success bg-success/10 border-success/30",
    emoji: "🐋",
  },
  whale_sell: {
    label: "Whale Sell",
    color: "text-danger bg-danger/10 border-danger/30",
    emoji: "🐋",
  },
  exchange_deposit: {
    label: "Exchange Deposit",
    color: "text-warning bg-warning/10 border-warning/30",
    emoji: "🏦",
  },
  exchange_withdrawal: {
    label: "Exchange Withdrawal",
    color: "text-brand bg-brand/10 border-brand/30",
    emoji: "🏦",
  },
  liquidity_added: {
    label: "LP Added",
    color: "text-success bg-success/10 border-success/30",
    emoji: "💧",
  },
  liquidity_removed: {
    label: "LP Removed",
    color: "text-danger bg-danger/10 border-danger/30",
    emoji: "💧",
  },
  contract_deployment: {
    label: "Contract Deploy",
    color: "text-brand bg-brand/10 border-brand/30",
    emoji: "📜",
  },
  token_mint: {
    label: "Token Mint",
    color: "text-success bg-success/10 border-success/30",
    emoji: "🪙",
  },
  token_burn: {
    label: "Token Burn",
    color: "text-danger bg-danger/10 border-danger/30",
    emoji: "🔥",
  },
  large_swap: {
    label: "Large Swap",
    color: "text-warning bg-warning/10 border-warning/30",
    emoji: "🔄",
  },
  smart_money_activity: {
    label: "Smart Money",
    color: "text-brand bg-brand/10 border-brand/30",
    emoji: "🧠",
  },
  wallet_accumulation: {
    label: "Accumulation",
    color: "text-success bg-success/10 border-success/30",
    emoji: "📈",
  },
  wallet_distribution: {
    label: "Distribution",
    color: "text-danger bg-danger/10 border-danger/30",
    emoji: "📉",
  },
};

interface EventTypeBadgeProps {
  type: EventType;
  showEmoji?: boolean;
}

export function EventTypeBadge({ type, showEmoji = true }: EventTypeBadgeProps) {
  const meta = EVENT_META[type] ?? {
    label: type,
    color: "text-white/60 bg-white/5 border-white/10",
    emoji: "•",
  };

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        meta.color,
      )}
    >
      {showEmoji && <span>{meta.emoji}</span>}
      {meta.label}
    </span>
  );
}

export { EVENT_META };
