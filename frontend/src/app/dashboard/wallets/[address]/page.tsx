"use client";

import { use } from "react";
import Link from "next/link";
import { formatDistanceToNow, format } from "date-fns";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import { ArrowLeft, ExternalLink, Sparkles } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { ScoreGauge } from "@/components/ui/ScoreGauge";
import { EventTypeBadge, EVENT_META } from "@/components/events/EventTypeBadge";
import { useWalletAnalytics, useAIInsights } from "@/hooks/useAnalytics";
import type { EventType } from "@/types/api";

const ETHERSCAN_ADDR = "https://etherscan.io/address/";

const CHART_STYLE = {
  contentStyle: {
    background: "#161B22",
    border: "1px solid #30363D",
    borderRadius: 8,
    fontSize: 12,
    color: "#fff",
  },
  cursor: { fill: "#ffffff08" },
};

function formatUsd(v: number) {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="card">
      <p className="text-xs text-white/40">{label}</p>
      <p className="mt-0.5 text-lg font-bold text-white">{value}</p>
    </div>
  );
}

export default function WalletDetailPage({
  params,
}: {
  params: Promise<{ address: string }>;
}) {
  const { address } = use(params);
  const { data, isLoading } = useWalletAnalytics(address);
  const { data: aiData, isLoading: aiLoading, refetch: fetchAI, isFetched: aiFetched } =
    useAIInsights(address);

  const shortAddr = `${address.slice(0, 10)}…${address.slice(-8)}`;

  return (
    <>
      <Header
        title="Wallet Analytics"
        subtitle={shortAddr}
        actions={
          <Link
            href="/dashboard/wallets"
            className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back
          </Link>
        }
      />

      <div className="p-6">
        {isLoading ? (
          <div className="flex justify-center py-20">
            <Spinner size="lg" />
          </div>
        ) : !data ? (
          <div className="text-center py-16 text-white/40 text-sm">
            No analytics data found for this address.
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            {/* Top row: stats + score */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              <StatCard
                label="Total events"
                value={data.total_events.toLocaleString()}
              />
              <StatCard
                label="Total volume"
                value={formatUsd(data.total_volume_usd)}
              />
              <StatCard
                label="First seen"
                value={
                  data.first_seen
                    ? format(new Date(data.first_seen), "MMM d, yyyy")
                    : "—"
                }
              />
              <StatCard
                label="Last active"
                value={
                  data.last_seen
                    ? formatDistanceToNow(new Date(data.last_seen), {
                        addSuffix: true,
                      })
                    : "—"
                }
              />
              <div className="card flex flex-col items-center justify-center gap-1">
                <p className="text-xs text-white/40">Wallet Score</p>
                {data.score !== null ? (
                  <ScoreGauge score={data.score} size="lg" />
                ) : (
                  <span className="text-white/30 text-sm">—</span>
                )}
              </div>
            </div>

            {/* Address + Etherscan link */}
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-brand break-all">{address}</span>
              <a
                href={`${ETHERSCAN_ADDR}${address}`}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0 text-white/30 hover:text-brand transition-colors"
                aria-label="View on Etherscan"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              {/* Volume over time */}
              <div className="lg:col-span-2">
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/30">
                  Volume Over Time (30d)
                </h2>
                <div className="card">
                  {data.volume_over_time.length ? (
                    <ResponsiveContainer width="100%" height={200}>
                      <AreaChart
                        data={data.volume_over_time}
                        margin={{ top: 4, right: 4, bottom: 4, left: -16 }}
                      >
                        <defs>
                          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#00E5FF" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#00E5FF" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <XAxis
                          dataKey="date"
                          tick={{ fill: "#ffffff40", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                          tickFormatter={(v) => v.slice(5)}
                        />
                        <YAxis
                          tick={{ fill: "#ffffff40", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                          tickFormatter={(v) => formatUsd(v)}
                        />
                        <Tooltip
                          {...CHART_STYLE}
                          formatter={(v: number) => [formatUsd(v), "Volume"]}
                        />
                        <Area
                          type="monotone"
                          dataKey="volume"
                          stroke="#00E5FF"
                          strokeWidth={2}
                          fill="url(#grad)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex h-[200px] items-center justify-center text-sm text-white/30">
                      No activity in the last 30 days
                    </div>
                  )}
                </div>
              </div>

              {/* Event type breakdown */}
              <div>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/30">
                  Event Breakdown
                </h2>
                <div className="card h-fit">
                  {Object.keys(data.event_type_breakdown).length ? (
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart
                        data={Object.entries(data.event_type_breakdown)
                          .map(([type, count]) => ({
                            name:
                              EVENT_META[type as EventType]?.label ?? type,
                            count,
                          }))
                          .sort((a, b) => b.count - a.count)}
                        layout="vertical"
                        margin={{ top: 4, right: 8, bottom: 4, left: 8 }}
                      >
                        <XAxis
                          type="number"
                          tick={{ fill: "#ffffff40", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          tick={{ fill: "#ffffff60", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                          width={80}
                        />
                        <Tooltip {...CHART_STYLE} />
                        <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                          {Object.keys(data.event_type_breakdown).map(
                            (_, i) => (
                              <Cell
                                key={i}
                                fill="#00E5FF"
                                fillOpacity={0.7}
                              />
                            ),
                          )}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex h-[200px] items-center justify-center text-sm text-white/30">
                      No events recorded
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Score breakdown + insights */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {data.score_breakdown && (
                <div>
                  <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/30">
                    Score Breakdown
                  </h2>
                  <div className="card flex flex-col gap-3">
                    {Object.entries(data.score_breakdown).map(
                      ([key, value]) => {
                        const maxes: Record<string, number> = {
                          volume: 40,
                          activity: 30,
                          diversity: 20,
                          recency: 10,
                        };
                        const max = maxes[key] ?? 100;
                        const pct = (value / max) * 100;
                        return (
                          <div key={key}>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="capitalize text-white/60">
                                {key}
                              </span>
                              <span className="font-mono text-white">
                                {value.toFixed(1)} / {max}
                              </span>
                            </div>
                            <div className="h-1.5 rounded-full bg-surface-elevated overflow-hidden">
                              <div
                                className="h-full rounded-full bg-brand transition-all duration-700"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        );
                      },
                    )}
                  </div>
                </div>
              )}

              {data.insights.length > 0 && (
                <div>
                  <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/30">
                    Insights
                  </h2>
                  <div className="card flex flex-col gap-2">
                    {data.insights.map((insight, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span className="text-brand mt-0.5 shrink-0">→</span>
                        <p className="text-sm text-white/70">{insight}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* AI Insights */}
            <div>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-xs font-semibold uppercase tracking-widest text-white/30">
                  AI Insights
                </h2>
                {!aiFetched && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => fetchAI()}
                    disabled={aiLoading}
                    className="gap-1.5 text-brand"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    {aiLoading ? "Analysing…" : "Generate insights"}
                  </Button>
                )}
              </div>
              {aiLoading && (
                <div className="flex items-center gap-2 rounded-xl border border-surface-border bg-surface-card px-4 py-3 text-sm text-white/40">
                  <Spinner size="sm" />
                  Generating AI analysis…
                </div>
              )}
              {aiData && (
                <div className="card flex flex-col gap-2">
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="h-3.5 w-3.5 text-brand" />
                    <span className="text-xs text-white/40">
                      {aiData.ai_powered ? "Claude AI" : "Heuristic"} · Score:{" "}
                      <span className="text-white font-mono">
                        {Math.round(aiData.score * 100)}/100
                      </span>
                    </span>
                  </div>
                  {aiData.insights.map((insight, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-brand mt-0.5 shrink-0">→</span>
                      <p className="text-sm text-white/70">{insight}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Top tokens */}
            {data.top_tokens.length > 0 && (
              <div>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/30">
                  Top Tokens
                </h2>
                <div className="rounded-xl border border-surface-border bg-surface-card overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-surface-border">
                        <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                          Token
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                          Contract
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-white/40">
                          Volume
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-white/40">
                          Events
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.top_tokens.map((t) => (
                        <tr
                          key={t.contract}
                          className="border-b border-surface-border/50 last:border-0 hover:bg-surface-elevated"
                        >
                          <td className="px-4 py-3 font-semibold text-white">
                            {t.symbol}
                          </td>
                          <td className="px-4 py-3 font-mono text-xs text-brand">
                            {t.contract.slice(0, 8)}…{t.contract.slice(-6)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-xs text-white">
                            {formatUsd(t.volume)}
                          </td>
                          <td className="px-4 py-3 text-right text-xs text-white/60">
                            {t.count}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
