import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  PaperPortfolio,
  PaperTrade,
  PortfolioSummary,
} from "@/types/api";

const PORTFOLIOS_KEY = ["paper-trading", "portfolios"] as const;

const portfolioKey = (id: string) =>
  ["paper-trading", "portfolio", id] as const;

const tradesKey = (id: string) =>
  ["paper-trading", "trades", id] as const;

export function usePortfolios() {
  return useQuery<PaperPortfolio[]>({
    queryKey: PORTFOLIOS_KEY,
    queryFn: () => api.get("/paper-trading/portfolios").then((r) => r.data),
  });
}

export function usePortfolioSummary(portfolioId: string) {
  return useQuery<PortfolioSummary>({
    queryKey: portfolioKey(portfolioId),
    queryFn: () =>
      api.get(`/paper-trading/portfolios/${portfolioId}`).then((r) => r.data),
    refetchInterval: 30_000,
  });
}

export function useTradeHistory(portfolioId: string) {
  return useQuery<PaperTrade[]>({
    queryKey: tradesKey(portfolioId),
    queryFn: () =>
      api
        .get(`/paper-trading/portfolios/${portfolioId}/trades`, {
          params: { limit: 100 },
        })
        .then((r) => r.data),
  });
}

export function useCreatePortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; starting_balance: string }) =>
      api.post("/paper-trading/portfolios", data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: PORTFOLIOS_KEY }),
  });
}

export function useDeletePortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (portfolioId: string) =>
      api.delete(`/paper-trading/portfolios/${portfolioId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: PORTFOLIOS_KEY }),
  });
}

export function useExecuteTrade(portfolioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: {
      trade_type: "buy" | "sell";
      token_symbol: string;
      token_contract: string;
      chain: string;
      quantity: string;
      trigger?: "manual" | "signal";
    }) =>
      api
        .post(`/paper-trading/portfolios/${portfolioId}/trades`, req)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: portfolioKey(portfolioId) });
      qc.invalidateQueries({ queryKey: tradesKey(portfolioId) });
    },
  });
}
