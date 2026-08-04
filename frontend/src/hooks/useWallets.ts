"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";
import type { Wallet } from "@/types/api";

export function useWallets() {
  return useQuery({
    queryKey: ["wallets"],
    queryFn: () => apiGet<Wallet[]>("/wallets"),
  });
}

export function useAddWallet() {
  return useMutation({
    mutationFn: ({
      address,
      chain,
      custom_label,
      threshold_usd,
    }: {
      address: string;
      chain: string;
      custom_label?: string;
      threshold_usd?: string;
    }) =>
      apiPost<Wallet>("/wallets", {
        address,
        chain,
        custom_label,
        threshold_usd,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
      toast.success("Wallet added");
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to add wallet";
      toast.error(msg);
    },
  });
}

export function useRemoveWallet() {
  return useMutation({
    mutationFn: (address: string) => apiDelete(`/wallets/${address}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
      toast.success("Wallet removed");
    },
    onError: () => toast.error("Failed to remove wallet"),
  });
}
