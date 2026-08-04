import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { RiskProfile, Strategy, StrategyRun } from "@/types/api";

const riskKey = (portfolioId: string) =>
  ["strategy", portfolioId, "risk-profile"] as const;

const strategiesKey = (portfolioId: string) =>
  ["strategy", portfolioId, "strategies"] as const;

const runsKey = (portfolioId: string) =>
  ["strategy", portfolioId, "runs"] as const;

const base = (portfolioId: string) =>
  `/paper-trading/portfolios/${portfolioId}`;

export function useRiskProfile(portfolioId: string) {
  return useQuery<RiskProfile | null>({
    queryKey: riskKey(portfolioId),
    queryFn: () =>
      api.get(`${base(portfolioId)}/risk-profile`).then((r) => r.data),
  });
}

export function useUpsertRiskProfile(portfolioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      stop_loss_pct: string;
      take_profit_pct: string;
      max_position_pct: string;
      max_drawdown_pct: string;
    }) =>
      api
        .put(`${base(portfolioId)}/risk-profile`, data)
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: riskKey(portfolioId) }),
  });
}

export function useStrategies(portfolioId: string) {
  return useQuery<Strategy[]>({
    queryKey: strategiesKey(portfolioId),
    queryFn: () =>
      api.get(`${base(portfolioId)}/strategies`).then((r) => r.data),
  });
}

export function useCreateStrategy(portfolioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      name: string;
      description?: string;
      token_contract: string;
      token_symbol: string;
      chain: string;
      signal_direction: string;
      min_confidence: string;
      action: string;
      size_pct: string;
    }) =>
      api.post(`${base(portfolioId)}/strategies`, data).then((r) => r.data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: strategiesKey(portfolioId) }),
  });
}

export function useToggleStrategy(portfolioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      strategyId,
      is_active,
    }: {
      strategyId: string;
      is_active: boolean;
    }) =>
      api
        .patch(`${base(portfolioId)}/strategies/${strategyId}`, { is_active })
        .then((r) => r.data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: strategiesKey(portfolioId) }),
  });
}

export function useDeleteStrategy(portfolioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (strategyId: string) =>
      api.delete(`${base(portfolioId)}/strategies/${strategyId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: strategiesKey(portfolioId) }),
  });
}

export function useRunStrategy(portfolioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (strategyId: string) =>
      api
        .post(`${base(portfolioId)}/strategies/${strategyId}/run`, {})
        .then((r) => r.data as { triggered: boolean }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: runsKey(portfolioId) });
      qc.invalidateQueries({
        queryKey: ["paper-trading", "portfolio", portfolioId],
      });
    },
  });
}

export function usePortfolioRuns(portfolioId: string) {
  return useQuery<StrategyRun[]>({
    queryKey: runsKey(portfolioId),
    queryFn: () =>
      api.get(`${base(portfolioId)}/strategy-runs`).then((r) => r.data),
    refetchInterval: 30_000,
  });
}
