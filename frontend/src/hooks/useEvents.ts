"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { OnChainEvent, PaginatedResponse } from "@/types/api";

interface EventFilters {
  page?: number;
  page_size?: number;
  event_type?: string;
  blockchain?: string;
  wallet_address?: string;
}

export function useEvents(filters: EventFilters = {}) {
  return useQuery({
    queryKey: ["events", filters],
    queryFn: () =>
      apiGet<PaginatedResponse<OnChainEvent>>("/events", {
        page: filters.page ?? 1,
        page_size: filters.page_size ?? 20,
        ...filters,
      }),
    refetchInterval: 15_000,
  });
}

export function useEvent(txHash: string) {
  return useQuery({
    queryKey: ["events", txHash],
    queryFn: () => apiGet<OnChainEvent>(`/events/${txHash}`),
    enabled: !!txHash,
  });
}
