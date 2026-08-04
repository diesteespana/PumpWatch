"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";
import { SignalBadge } from "@/components/ui/SignalBadge";
import { useTokenSignal } from "@/hooks/useAnalytics";
import type { Token } from "@/types/api";

function TokenSignalCell({ contract }: { contract: string }) {
  const { data, isLoading } = useTokenSignal(contract);
  if (isLoading) return <span className="text-white/20 text-xs">…</span>;
  if (!data) return <span className="text-white/20 text-xs">—</span>;
  return <SignalBadge direction={data.direction} confidence={data.confidence} size="sm" />;
}

function useTokens() {
  return useQuery({
    queryKey: ["tokens"],
    queryFn: () => apiGet<Token[]>("/tokens"),
  });
}

function useAddToken() {
  return useMutation({
    mutationFn: (data: {
      contract_address: string;
      chain: string;
      symbol: string;
      threshold_usd?: string;
    }) => apiPost<Token>("/tokens", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tokens"] });
      toast.success("Token added");
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to add token";
      toast.error(msg);
    },
  });
}

function useRemoveToken() {
  return useMutation({
    mutationFn: (contractAddress: string) =>
      apiDelete(`/tokens/${contractAddress}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tokens"] });
      toast.success("Token removed");
    },
    onError: () => toast.error("Failed to remove token"),
  });
}

function AddTokenModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [contract, setContract] = useState("");
  const [symbol, setSymbol] = useState("");
  const [threshold, setThreshold] = useState("");
  const add = useAddToken();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    add.mutate(
      {
        contract_address: contract,
        chain: "ethereum",
        symbol: symbol.toUpperCase(),
        threshold_usd: threshold || undefined,
      },
      { onSuccess: onClose },
    );
  };

  return (
    <Modal open={open} onClose={onClose} title="Track Token">
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Input
          label="Contract address"
          placeholder="0x..."
          value={contract}
          onChange={(e) => setContract(e.target.value)}
          required
          className="font-mono"
        />
        <Input
          label="Symbol"
          placeholder="e.g. USDC"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          required
        />
        <Input
          label="Min USD threshold (optional)"
          placeholder="e.g. 50000"
          type="number"
          min="0"
          value={threshold}
          onChange={(e) => setThreshold(e.target.value)}
        />
        <div className="flex gap-2 pt-1">
          <Button variant="secondary" className="flex-1" onClick={onClose} type="button">
            Cancel
          </Button>
          <Button type="submit" loading={add.isPending} className="flex-1">
            Add Token
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default function TokensPage() {
  const [open, setOpen] = useState(false);
  const { data: tokens, isLoading } = useTokens();
  const remove = useRemoveToken();

  return (
    <>
      <Header
        title="Tracked Tokens"
        subtitle="ERC-20 tokens monitored for whale activity"
        actions={
          <Button onClick={() => setOpen(true)} size="sm">
            <Plus className="h-4 w-4" />
            Add token
          </Button>
        }
      />

      <div className="p-6">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : !tokens?.length ? (
          <div className="rounded-xl border border-dashed border-surface-border bg-surface-card py-16 text-center">
            <p className="mb-2 text-sm font-medium text-white/60">
              No tokens tracked yet
            </p>
            <p className="mb-5 text-xs text-white/30">
              Add a token contract to monitor large transfers.
            </p>
            <Button onClick={() => setOpen(true)} size="sm">
              <Plus className="h-4 w-4" />
              Add first token
            </Button>
          </div>
        ) : (
          <div className="rounded-xl border border-surface-border bg-surface-card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border">
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                    Symbol
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                    Contract
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                    Threshold
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                    Signal
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                    Chain
                  </th>
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody>
                {tokens.map((t) => (
                  <tr
                    key={t.id}
                    className="border-b border-surface-border/50 last:border-0 hover:bg-surface-elevated"
                  >
                    <td className="px-4 py-3 font-semibold text-white">
                      {t.symbol}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-brand">
                      {t.contract_address.slice(0, 8)}…
                      {t.contract_address.slice(-6)}
                    </td>
                    <td className="px-4 py-3 text-white/70">
                      {t.threshold_usd ? (
                        <span className="font-mono">
                          ${parseFloat(t.threshold_usd).toLocaleString()}
                        </span>
                      ) : (
                        <span className="text-white/25">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <TokenSignalCell contract={t.contract_address} />
                    </td>
                    <td className="px-4 py-3 capitalize text-white/50">
                      {t.chain}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => remove.mutate(t.contract_address)}
                        disabled={remove.isPending}
                        className="text-white/20 transition-colors hover:text-danger"
                        aria-label="Remove token"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <AddTokenModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}
