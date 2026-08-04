"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { Trophy } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Spinner } from "@/components/ui/Spinner";
import { ScoreGauge } from "@/components/ui/ScoreGauge";
import { useRankings } from "@/hooks/useAnalytics";

function formatUsd(v: number) {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

function shortAddr(addr: string) {
  return `${addr.slice(0, 8)}…${addr.slice(-6)}`;
}

export default function RankingsPage() {
  const { data, isLoading } = useRankings();

  return (
    <>
      <Header
        title="Wallet Rankings"
        subtitle="Top wallets by heuristic activity score"
      />

      <div className="p-6">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : !data?.items.length ? (
          <div className="rounded-xl border border-dashed border-surface-border bg-surface-card py-16 text-center">
            <Trophy className="mx-auto mb-3 h-8 w-8 text-white/20" />
            <p className="text-sm font-medium text-white/60">No data yet</p>
            <p className="mt-1 text-xs text-white/30">
              Rankings populate as the detection engine records on-chain events.
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-surface-border bg-surface-card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border">
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/40 w-12">
                    Rank
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                    Wallet
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                    Score
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-white/40">
                    Volume
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-white/40">
                    Events
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-white/40">
                    Last active
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr
                    key={item.address}
                    className="border-b border-surface-border/50 last:border-0 hover:bg-surface-elevated transition-colors"
                  >
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs font-bold text-white/40">
                        #{item.rank}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/dashboard/wallets/${item.address}`}
                        className="group flex flex-col"
                      >
                        <span className="font-mono text-xs text-brand group-hover:underline">
                          {shortAddr(item.address)}
                        </span>
                        {item.label && (
                          <span className="text-xs text-white/40">{item.label}</span>
                        )}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <ScoreGauge score={item.score} size="sm" />
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-white">
                      {formatUsd(item.total_volume_usd)}
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-white/60">
                      {item.trade_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-white/40">
                      {item.last_seen
                        ? formatDistanceToNow(new Date(item.last_seen), {
                            addSuffix: true,
                          })
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && (
          <p className="mt-3 text-xs text-white/30 text-right">
            {data.total} wallets · refreshes every 5 minutes
          </p>
        )}
      </div>
    </>
  );
}
