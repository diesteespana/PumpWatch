"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useEvents } from "@/hooks/useEvents";
import { EventCard } from "./EventCard";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import type { EventType } from "@/types/api";

const ALL_TYPES: { value: string; label: string }[] = [
  { value: "", label: "All events" },
  { value: "whale_buy", label: "Whale Buy" },
  { value: "whale_sell", label: "Whale Sell" },
  { value: "exchange_deposit", label: "Exchange Deposit" },
  { value: "exchange_withdrawal", label: "Exchange Withdrawal" },
  { value: "large_swap", label: "Large Swap" },
  { value: "smart_money_activity", label: "Smart Money" },
  { value: "wallet_accumulation", label: "Accumulation" },
  { value: "wallet_distribution", label: "Distribution" },
];

export function EventFeed() {
  const [eventType, setEventType] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isFetching, refetch } = useEvents({
    event_type: eventType || undefined,
    page,
    page_size: 20,
  });

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <select
          value={eventType}
          onChange={(e) => {
            setEventType(e.target.value);
            setPage(1);
          }}
          className="h-8 rounded-lg border border-surface-border bg-surface-elevated px-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-brand"
        >
          {ALL_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          className="gap-1.5"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : !data?.items.length ? (
        <div className="rounded-lg border border-surface-border bg-surface-card py-12 text-center text-sm text-white/40">
          No events yet. The detection engine will populate this feed automatically.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {data.items.map((event) => (
            <EventCard key={`${event.tx_hash}-${event.event_type}`} event={event} />
          ))}
        </div>
      )}

      {data && data.total > 20 && (
        <div className="flex items-center justify-between text-xs text-white/40">
          <span>
            {(page - 1) * 20 + 1}–{Math.min(page * 20, data.total)} of{" "}
            {data.total}
          </span>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={!data.has_next}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
