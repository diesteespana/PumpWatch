"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2, TrendingUp } from "lucide-react";
import toast from "react-hot-toast";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import {
  useCreatePortfolio,
  useDeletePortfolio,
  usePortfolios,
} from "@/hooks/usePaperTrading";
import type { PaperPortfolio } from "@/types/api";

function fmt(value: string) {
  return parseFloat(value).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
  });
}

export default function PaperTradingPage() {
  const router = useRouter();
  const { data: portfolios, isLoading } = usePortfolios();
  const createPortfolio = useCreatePortfolio();
  const deletePortfolio = useDeletePortfolio();

  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [balance, setBalance] = useState("10000");

  function handleCreate() {
    const bal = parseFloat(balance);
    if (!name.trim()) return toast.error("Portfolio name is required.");
    if (isNaN(bal) || bal <= 0) return toast.error("Starting balance must be positive.");
    createPortfolio.mutate(
      { name: name.trim(), starting_balance: balance },
      {
        onSuccess: () => {
          toast.success("Portfolio created!");
          setShowCreate(false);
          setName("");
          setBalance("10000");
        },
        onError: () => toast.error("Failed to create portfolio."),
      }
    );
  }

  function handleDelete(p: PaperPortfolio) {
    if (!confirm(`Delete portfolio "${p.name}"? This cannot be undone.`)) return;
    deletePortfolio.mutate(p.id, {
      onSuccess: () => toast.success("Portfolio deleted."),
      onError: () => toast.error("Failed to delete portfolio."),
    });
  }

  return (
    <>
      <Header
        title="Paper Trading"
        subtitle="Simulate trades with virtual money using live prices"
        actions={
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4" />
            New Portfolio
          </Button>
        }
      />

      <div className="p-6">
        {isLoading ? (
          <div className="flex justify-center py-20">
            <Spinner size="lg" />
          </div>
        ) : !portfolios?.length ? (
          <div className="flex flex-col items-center py-20 text-white/40">
            <TrendingUp className="mb-3 h-10 w-10" />
            <p className="text-sm">No portfolios yet. Create one to get started.</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {portfolios.map((p) => (
              <div
                key={p.id}
                className="flex flex-col gap-3 rounded-lg border border-surface-border bg-surface-card p-5 transition-colors hover:border-brand/40"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold text-white">{p.name}</p>
                    <p className="text-xs text-white/40">
                      Started {fmt(p.starting_balance)}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDelete(p)}
                    className="shrink-0 rounded p-1 text-white/30 transition-colors hover:text-danger"
                    title="Delete portfolio"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-white/50">Cash available</span>
                  <span className="font-mono text-white">
                    {fmt(p.current_cash)}
                  </span>
                </div>

                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full"
                  onClick={() =>
                    router.push(`/dashboard/paper-trading/${p.id}`)
                  }
                >
                  View Portfolio
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      <Modal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        title="New Paper Portfolio"
      >
        <div className="flex flex-col gap-4">
          <Input
            label="Portfolio Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Test Portfolio"
          />
          <Input
            label="Starting Balance (USD)"
            type="number"
            min="1"
            value={balance}
            onChange={(e) => setBalance(e.target.value)}
            placeholder="10000"
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              loading={createPortfolio.isPending}
            >
              Create
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
