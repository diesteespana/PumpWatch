"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Activity, Bell, TrendingUp, Wallet } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { EventFeed } from "@/components/events/EventFeed";
import { SignalBadge } from "@/components/ui/SignalBadge";
import { useEvents } from "@/hooks/useEvents";
import { useWallets } from "@/hooks/useWallets";
import { useAlerts } from "@/hooks/useAlerts";
import { useMarketOverview } from "@/hooks/useAnalytics";
import { EVENT_META } from "@/components/events/EventTypeBadge";
import type { EventType } from "@/types/api";

function StatCard({
  label,
  value,
  icon: Icon,
  sub,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  sub?: string;
}) {
  return (
    <div className="card flex items-start gap-3">
      <div className="rounded-lg bg-brand/10 p-2">
        <Icon className="h-4 w-4 text-brand" />
      </div>
      <div>
        <p className="text-xs text-white/40">{label}</p>
        <p className="text-xl font-bold text-white">{value}</p>
        {sub && <p className="text-xs text-white/40">{sub}</p>}
      </div>
    </div>
  );
}

function EventTypeChart({ events }: { events: { event_type: EventType }[] }) {
  const counts: Record<string, number> = {};
  for (const e of events) {
    counts[e.event_type] = (counts[e.event_type] ?? 0) + 1;
  }
  const data = Object.entries(counts)
    .map(([type, count]) => ({
      name: EVENT_META[type as EventType]?.label ?? type,
      count,
      type,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
        <XAxis
          dataKey="name"
          tick={{ fill: "#ffffff40", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          angle={-20}
          textAnchor="end"
          height={40}
        />
        <YAxis
          tick={{ fill: "#ffffff40", fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
        />
        <Tooltip
          contentStyle={{
            background: "#161B22",
            border: "1px solid #30363D",
            borderRadius: 8,
            fontSize: 12,
            color: "#fff",
          }}
          cursor={{ fill: "#ffffff08" }}
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((entry) => (
            <Cell key={entry.type} fill="#00E5FF" fillOpacity={0.8} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function OverviewPage() {
  const { data: events } = useEvents({ page_size: 50 });
  const { data: wallets } = useWallets();
  const { data: alerts } = useAlerts();
  const { data: market } = useMarketOverview();

  const totalUsd = events?.items
    .reduce((sum, e) => sum + parseFloat(e.usd_value), 0)
    .toFixed(0);

  const formatUsd = (v: string | undefined) => {
    if (!v) return "$0";
    const n = parseInt(v, 10);
    if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
    return `$${n}`;
  };

  return (
    <>
      <Header
        title="Overview"
        subtitle="Live on-chain intelligence"
      />

      <div className="flex flex-col gap-6 p-6">
        {/* Stats row */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard
            label="Events (50)"
            value={events?.total ?? "—"}
            icon={Activity}
            sub="all time"
          />
          <StatCard
            label="Volume (50)"
            value={formatUsd(totalUsd)}
            icon={TrendingUp}
            sub="last 50 events"
          />
          <StatCard
            label="Tracked wallets"
            value={wallets?.length ?? "—"}
            icon={Wallet}
          />
          <StatCard
            label="Active alerts"
            value={alerts?.items.filter((a) => a.is_active).length ?? "—"}
            icon={Bell}
          />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Event feed */}
          <div className="lg:col-span-2">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/30">
              Live Event Feed
            </h2>
            <EventFeed />
          </div>

          {/* Right column: chart + market overview */}
          <div className="flex flex-col gap-4">
            <div>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/30">
                Event Distribution
              </h2>
              <div className="card">
                {events?.items.length ? (
                  <EventTypeChart events={events.items} />
                ) : (
                  <div className="flex h-[180px] items-center justify-center text-sm text-white/30">
                    No data yet
                  </div>
                )}
              </div>
            </div>

            {market && (
              <div>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/30">
                  Market Signal
                </h2>
                <div className="card flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-white/50">24h trend</span>
                    <SignalBadge direction={market.dominant_direction} size="sm" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-white/50">Volume (24h)</span>
                    <span className="font-mono text-xs text-white">
                      {market.total_volume_24h >= 1_000_000
                        ? `$${(market.total_volume_24h / 1_000_000).toFixed(1)}M`
                        : `$${(market.total_volume_24h / 1_000).toFixed(0)}K`}
                    </span>
                  </div>
                  <p className="text-xs text-white/40 border-t border-surface-border pt-2">
                    {market.summary}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
