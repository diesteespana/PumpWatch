"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";
import type { Alert, AlertCreate, AlertUpdate, PaginatedResponse } from "@/types/api";

export function useAlerts(page = 1) {
  return useQuery({
    queryKey: ["alerts", page],
    queryFn: () =>
      apiGet<PaginatedResponse<Alert>>("/alerts", { page, page_size: 20 }),
  });
}

export function useCreateAlert() {
  return useMutation({
    mutationFn: (data: AlertCreate) => apiPost<Alert>("/alerts", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      toast.success("Alert created");
    },
    onError: () => toast.error("Failed to create alert"),
  });
}

export function useUpdateAlert() {
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AlertUpdate }) =>
      apiPut<Alert>(`/alerts/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      toast.success("Alert updated");
    },
    onError: () => toast.error("Failed to update alert"),
  });
}

export function useDeleteAlert() {
  return useMutation({
    mutationFn: (id: string) => apiDelete(`/alerts/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      toast.success("Alert deleted");
    },
    onError: () => toast.error("Failed to delete alert"),
  });
}

export function useToggleAlert() {
  return useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      apiPut<Alert>(`/alerts/${id}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
    onError: () => toast.error("Failed to toggle alert"),
  });
}
