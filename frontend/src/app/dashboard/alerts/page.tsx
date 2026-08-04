"use client";

import { useState } from "react";
import { Plus, Trash2, ToggleLeft, ToggleRight } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { EventTypeBadge } from "@/components/events/EventTypeBadge";
import {
  useAlerts,
  useCreateAlert,
  useDeleteAlert,
  useToggleAlert,
} from "@/hooks/useAlerts";
import type { AlertEventType } from "@/types/api";

const ALL_EVENT_TYPES: AlertEventType[] = [
  "whale_buy",
  "whale_sell",
  "exchange_deposit",
  "exchange_withdrawal",
  "liquidity_added",
  "liquidity_removed",
  "large_swap",
  "smart_money_activity",
  "wallet_accumulation",
  "wallet_distribution",
  "token_mint",
  "token_burn",
  "contract_deployment",
];

function CreateAlertModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [name, setName] = useState("");
  const [selected, setSelected] = useState<AlertEventType[]>([]);
  const [minUsd, setMinUsd] = useState("");
  const create = useCreateAlert();

  const toggle = (t: AlertEventType) =>
    setSelected((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t],
    );

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    create.mutate(
      {
        name,
        event_types: selected,
        min_usd_value: minUsd || null,
      },
      { onSuccess: onClose },
    );
  };

  return (
    <Modal open={open} onClose={onClose} title="Create Alert" className="max-w-lg">
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Input
          label="Alert name"
          placeholder="e.g. Whale buys > $500K"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />

        <div>
          <p className="mb-2 text-sm font-medium text-white/70">Event types</p>
          <div className="flex flex-wrap gap-1.5">
            {ALL_EVENT_TYPES.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => toggle(t)}
                className={`rounded-full border px-2 py-0.5 text-xs transition-opacity ${
                  selected.includes(t) ? "opacity-100" : "opacity-30 hover:opacity-60"
                }`}
              >
                <EventTypeBadge type={t} showEmoji={false} />
              </button>
            ))}
          </div>
        </div>

        <Input
          label="Min USD value (optional)"
          placeholder="e.g. 100000"
          type="number"
          min="0"
          value={minUsd}
          onChange={(e) => setMinUsd(e.target.value)}
        />

        <div className="flex gap-2 pt-1">
          <Button
            variant="secondary"
            className="flex-1"
            onClick={onClose}
            type="button"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            loading={create.isPending}
            disabled={!name || !selected.length}
            className="flex-1"
          >
            Create
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default function AlertsPage() {
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(1);
  const { data, isLoading } = useAlerts(page);
  const deleteAlert = useDeleteAlert();
  const toggleAlert = useToggleAlert();

  return (
    <>
      <Header
        title="Alerts"
        subtitle="Notification rules triggered by on-chain events"
        actions={
          <Button onClick={() => setOpen(true)} size="sm">
            <Plus className="h-4 w-4" />
            New alert
          </Button>
        }
      />

      <div className="p-6">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : !data?.items.length ? (
          <div className="rounded-xl border border-dashed border-surface-border bg-surface-card py-16 text-center">
            <p className="mb-2 text-sm font-medium text-white/60">
              No alerts configured
            </p>
            <p className="mb-5 text-xs text-white/30">
              Create an alert to get notified when events match your criteria.
            </p>
            <Button onClick={() => setOpen(true)} size="sm">
              <Plus className="h-4 w-4" />
              Create first alert
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {data.items.map((alert) => (
              <div
                key={alert.id}
                className="card flex items-start gap-4"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <p className="font-medium text-white truncate">{alert.name}</p>
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded-full ${
                        alert.is_active
                          ? "bg-success/10 text-success"
                          : "bg-white/5 text-white/30"
                      }`}
                    >
                      {alert.is_active ? "Active" : "Paused"}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {alert.event_types.map((t) => (
                      <EventTypeBadge key={t} type={t} showEmoji={false} />
                    ))}
                  </div>
                  {alert.min_usd_value && (
                    <p className="mt-1.5 text-xs text-white/40">
                      Min value: ${parseFloat(alert.min_usd_value).toLocaleString()}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() =>
                      toggleAlert.mutate({
                        id: alert.id,
                        is_active: !alert.is_active,
                      })
                    }
                    className="text-white/30 transition-colors hover:text-brand"
                    aria-label={alert.is_active ? "Pause alert" : "Activate alert"}
                  >
                    {alert.is_active ? (
                      <ToggleRight className="h-5 w-5 text-brand" />
                    ) : (
                      <ToggleLeft className="h-5 w-5" />
                    )}
                  </button>
                  <button
                    onClick={() => deleteAlert.mutate(alert.id)}
                    disabled={deleteAlert.isPending}
                    className="text-white/20 transition-colors hover:text-danger"
                    aria-label="Delete alert"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}

            {data.total > 20 && (
              <div className="flex items-center justify-end gap-2 pt-1">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={page === 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={!data.has_next}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      <CreateAlertModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}
