import { formatDistanceToNow } from "date-fns";
import { ExternalLink } from "lucide-react";
import type { OnChainEvent } from "@/types/api";
import { EventTypeBadge } from "./EventTypeBadge";

interface EventCardProps {
  event: OnChainEvent;
}

function shortAddr(addr: string) {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

function formatUsd(value: string) {
  const n = parseFloat(value);
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(2)}`;
}

const ETHERSCAN = "https://etherscan.io/tx/";

export function EventCard({ event }: EventCardProps) {
  return (
    <div className="group flex items-start gap-3 rounded-lg border border-surface-border bg-surface-card px-4 py-3 transition-colors hover:border-brand/30 hover:bg-surface-elevated">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <EventTypeBadge type={event.event_type} />
          <span className="font-mono text-sm font-semibold text-white">
            {formatUsd(event.usd_value)}
          </span>
          {event.token_symbol && (
            <span className="text-xs text-white/50">{event.token_symbol}</span>
          )}
        </div>

        <div className="mt-1.5 flex items-center gap-2 text-xs text-white/40">
          <span className="font-mono text-brand/80">
            {shortAddr(event.wallet_address)}
          </span>
          <span>·</span>
          <span>
            {formatDistanceToNow(new Date(event.timestamp), {
              addSuffix: true,
            })}
          </span>
          <span>·</span>
          <span className="capitalize">{event.blockchain}</span>
          <span>·</span>
          <span>{Math.round(event.confidence_score * 100)}% conf</span>
        </div>

        {event.explanation && (
          <p className="mt-1 text-xs text-white/50 line-clamp-1">
            {event.explanation}
          </p>
        )}
      </div>

      <a
        href={`${ETHERSCAN}${event.tx_hash}`}
        target="_blank"
        rel="noopener noreferrer"
        className="shrink-0 text-white/20 transition-colors hover:text-brand group-hover:text-white/40"
        aria-label="View on Etherscan"
      >
        <ExternalLink className="h-4 w-4" />
      </a>
    </div>
  );
}
