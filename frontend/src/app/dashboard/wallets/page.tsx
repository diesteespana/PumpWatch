"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus, Trash2 } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { useWallets, useAddWallet, useRemoveWallet } from "@/hooks/useWallets";

function AddWalletModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [address, setAddress] = useState("");
  const [label, setLabel] = useState("");
  const [threshold, setThreshold] = useState("");
  const addWallet = useAddWallet();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    addWallet.mutate(
      {
        address,
        chain: "ethereum",
        custom_label: label || undefined,
        threshold_usd: threshold || undefined,
      },
      { onSuccess: onClose },
    );
  };

  return (
    <Modal open={open} onClose={onClose} title="Track Wallet">
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Input
          label="Wallet address"
          placeholder="0x..."
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          required
          className="font-mono"
        />
        <Input
          label="Label (optional)"
          placeholder="e.g. Vitalik"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
        />
        <Input
          label="Min USD threshold (optional)"
          placeholder="100000"
          type="number"
          min="0"
          value={threshold}
          onChange={(e) => setThreshold(e.target.value)}
        />
        <div className="flex gap-2 pt-1">
          <Button variant="secondary" className="flex-1" onClick={onClose} type="button">
            Cancel
          </Button>
          <Button type="submit" loading={addWallet.isPending} className="flex-1">
            Add Wallet
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default function WalletsPage() {
  const [open, setOpen] = useState(false);
  const { data: wallets, isLoading } = useWallets();
  const remove = useRemoveWallet();

  return (
    <>
      <Header
        title="Tracked Wallets"
        subtitle="Wallets monitored for on-chain activity"
        actions={
          <Button onClick={() => setOpen(true)} size="sm">
            <Plus className="h-4 w-4" />
            Add wallet
          </Button>
        }
      />

      <div className="p-6">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : !wallets?.length ? (
          <div className="rounded-xl border border-dashed border-surface-border bg-surface-card py-16 text-center">
            <p className="mb-2 text-sm font-medium text-white/60">
              No wallets tracked yet
            </p>
            <p className="mb-5 text-xs text-white/30">
              Add a wallet address to start receiving alerts.
            </p>
            <Button onClick={() => setOpen(true)} size="sm">
              <Plus className="h-4 w-4" />
              Add first wallet
            </Button>
          </div>
        ) : (
          <div className="rounded-xl border border-surface-border bg-surface-card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border">
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                    Address
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                    Label
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                    Threshold
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/40">
                    Chain
                  </th>
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody>
                {wallets.map((w) => (
                  <tr
                    key={w.id}
                    className="border-b border-surface-border/50 last:border-0 hover:bg-surface-elevated"
                  >
                    <td className="px-4 py-3 font-mono text-xs">
                      <Link
                        href={`/dashboard/wallets/${w.address}`}
                        className="text-brand hover:underline"
                      >
                        {w.address.slice(0, 8)}…{w.address.slice(-6)}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-white/70">
                      {w.custom_label ?? w.label ?? (
                        <span className="text-white/25">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-white/70">
                      {w.threshold_usd ? (
                        <span className="font-mono">
                          ${parseFloat(w.threshold_usd).toLocaleString()}
                        </span>
                      ) : (
                        <span className="text-white/25">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 capitalize text-white/50">
                      {w.chain}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => remove.mutate(w.address)}
                        disabled={remove.isPending}
                        className="text-white/20 transition-colors hover:text-danger"
                        aria-label="Remove wallet"
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

      <AddWalletModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}
