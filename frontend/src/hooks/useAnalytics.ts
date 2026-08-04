"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type {
  AIInsights,
  MarketOverview,
  RankingsResponse,
  TokenSignal,
  TokenSentiment,
  WalletAnalytics,
} from "@/types/api";

export function useWalletAnalytics(
  address: string,
  chain = "ethereum",
  historyDays = 30,
) {
  return useQuery({
    queryKey: ["analytics", "wallet", address, chain, historyDays],
    queryFn: () =>
      apiGet<WalletAnalytics>(`/analytics/wallets/${address}`, {
        chain,
        history_days: historyDays,
      }),
    enabled: !!address,
    staleTime: 60_000,
  });
}

export function useRankings(chain = "ethereum", limit = 50) {
  return useQuery({
    queryKey: ["analytics", "rankings", chain, limit],
    queryFn: () =>
      apiGet<RankingsResponse>(`/analytics/rankings`, { chain, limit }),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
}

export function useAIInsights(address: string) {
  return useQuery({
    queryKey: ["analytics", "ai-insights", address],
    queryFn: () => apiGet<AIInsights>(`/analytics/wallets/${address}/ai-insights`),
    enabled: !!address,
    staleTime: 60 * 60_000, // 1 hour — matches server-side cache
  });
}

export function useTokenSignal(contract: string, chain = "ethereum") {
  return useQuery({
    queryKey: ["analytics", "signal", contract, chain],
    queryFn: () =>
      apiGet<TokenSignal>(`/analytics/tokens/${contract}/signal`, { chain }),
    enabled: !!contract,
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
}

export function useTokenSentiment(contract: string) {
  return useQuery({
    queryKey: ["analytics", "sentiment", contract],
    queryFn: () =>
      apiGet<TokenSentiment>(`/analytics/tokens/${contract}/sentiment`),
    enabled: !!contract,
    staleTime: 30 * 60_000,
  });
}

export function useMarketOverview(chain = "ethereum") {
  return useQuery({
    queryKey: ["analytics", "market-overview", chain],
    queryFn: () => apiGet<MarketOverview>(`/analytics/market/overview`, { chain }),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
}
