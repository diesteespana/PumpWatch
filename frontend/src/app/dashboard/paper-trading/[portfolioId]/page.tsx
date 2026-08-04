"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Bot,
  ChevronRight,
  Play,
  Plus,
  Shield,
  Trash2,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { clsx } from "clsx";
import toast from "react-hot-toast";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import {
  useExecuteTrade,
  usePortfolioSummary,
  useTradeHistory,
} from "@/hooks/usePaperTrading";
import {
  useCreateStrategy,
  useDeleteStrategy,
  usePortfolioRuns,
  useRiskProfile,
  useRunStrategy,
  useStrategies,
  useToggleStrategy,
  useUpsertRiskProfile,
} from "@/hooks/useStrategy";
import type { PaperPosition, PaperTrade, Strategy, StrategyRun } from "@/types/api";

// ─── Formatters ──────────────────────────────────────────────────────────────

function usd(v: string | number | null | undefined) {
  if (v == null) return "—";
  return parseFloat(String(v)).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
  });
}

function pct(v: string | null | undefined, sign = true) {
  if (v == null) return null;
  const n = parseFloat(v);
  const prefix = sign && n >= 0 ? "+" : "";
  return `${prefix}${n.toFixed(2)}%`;
}

function PnlCell({ value }: { value: string | null }) {
  if (value == null) return <span className="text-white/40">—</span>;
  const n = parseFloat(value);
  return (
    <span className={clsx("font-mono text-sm", n >= 0 ? "text-success" : "text-danger")}>
      {n >= 0 ? "+" : ""}
      {usd(value)}
    </span>
  );
}

// ─── Positions Table ─────────────────────────────────────────────────────────

function PositionsTable({ positions }: { positions: PaperPosition[] }) {
  if (!positions.length)
    return <p className="py-6 text-center text-sm text-white/40">No open positions.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-surface-border text-left text-xs text-white/40">
            <th className="pb-2 pr-4">Token</th>
            <th className="pb-2 pr-4">Qty</th>
            <th className="pb-2 pr-4">Avg Entry</th>
            <th className="pb-2 pr-4">Current</th>
            <th className="pb-2 pr-4">Value</th>
            <th className="pb-2">Unrealized P&amp;L</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-border">
          {positions.map((pos) => (
            <tr key={pos.id}>
              <td className="py-2.5 pr-4">
                <span className="font-mono font-semibold text-white">{pos.token_symbol}</span>
                <span className="ml-1 text-xs text-white/30">{pos.chain}</span>
              </td>
              <td className="py-2.5 pr-4 font-mono text-white/80">
                {parseFloat(pos.quantity).toFixed(4)}
              </td>
              <td className="py-2.5 pr-4 font-mono text-white/80">{usd(pos.avg_entry_price)}</td>
              <td className="py-2.5 pr-4 font-mono text-white/80">{usd(pos.current_price)}</td>
              <td className="py-2.5 pr-4 font-mono text-white/80">{usd(pos.current_value)}</td>
              <td className="py-2.5">
                <PnlCell value={pos.unrealized_pnl} />
                {pos.unrealized_pnl_pct && (
                  <span
                    className={clsx(
                      "ml-1 text-xs",
                      parseFloat(pos.unrealized_pnl_pct) >= 0 ? "text-success/70" : "text-danger/70"
                    )}
                  >
                    {pct(pos.unrealized_pnl_pct)}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Trade History Table ──────────────────────────────────────────────────────

function TradeHistoryTable({ trades }: { trades: PaperTrade[] }) {
  if (!trades.length)
    return <p className="py-6 text-center text-sm text-white/40">No trades yet.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-surface-border text-left text-xs text-white/40">
            <th className="pb-2 pr-4">Time</th>
            <th className="pb-2 pr-4">Type</th>
            <th className="pb-2 pr-4">Token</th>
            <th className="pb-2 pr-4">Qty</th>
            <th className="pb-2 pr-4">Price</th>
            <th className="pb-2 pr-4">Total</th>
            <th className="pb-2">Realized P&amp;L</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-border">
          {trades.map((t) => (
            <tr key={t.id}>
              <td className="py-2.5 pr-4 text-xs text-white/40">
                {new Date(t.executed_at).toLocaleString()}
              </td>
              <td className="py-2.5 pr-4">
                <span
                  className={clsx(
                    "rounded px-1.5 py-0.5 text-xs font-semibold uppercase",
                    t.trade_type === "buy"
                      ? "bg-success/10 text-success"
                      : "bg-danger/10 text-danger"
                  )}
                >
                  {t.trade_type}
                </span>
                {t.trigger === "signal" && (
                  <span className="ml-1 text-xs text-brand/70">auto</span>
                )}
              </td>
              <td className="py-2.5 pr-4 font-mono font-semibold text-white">{t.token_symbol}</td>
              <td className="py-2.5 pr-4 font-mono text-white/80">
                {parseFloat(t.quantity).toFixed(4)}
              </td>
              <td className="py-2.5 pr-4 font-mono text-white/80">
                {usd(t.price_at_execution)}
              </td>
              <td className="py-2.5 pr-4 font-mono text-white/80">{usd(t.total_value)}</td>
              <td className="py-2.5">
                <PnlCell value={t.realized_pnl} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Strategies Tab ───────────────────────────────────────────────────────────

const CHAINS = ["ethereum", "bsc", "polygon", "arbitrum", "optimism"];

function StrategiesTab({ portfolioId }: { portfolioId: string }) {
  const { data: strategies = [], isLoading } = useStrategies(portfolioId);
  const { data: runs = [] } = usePortfolioRuns(portfolioId);
  const createStrategy = useCreateStrategy(portfolioId);
  const toggleStrategy = useToggleStrategy(portfolioId);
  const deleteStrategy = useDeleteStrategy(portfolioId);
  const runStrategy = useRunStrategy(portfolioId);

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    token_symbol: "",
    token_contract: "",
    chain: "ethereum",
    signal_direction: "bullish",
    min_confidence: "0.60",
    action: "buy",
    size_pct: "10",
  });

  function field(k: keyof typeof form) {
    return {
      value: form[k],
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
        setForm((f) => ({ ...f, [k]: e.target.value })),
    };
  }

  function handleCreate() {
    if (!form.name.trim()) return toast.error("Strategy name is required.");
    if (form.token_contract.length !== 42 || !form.token_contract.startsWith("0x"))
      return toast.error("Contract must be a valid 0x address.");
    if (!form.token_symbol.trim()) return toast.error("Token symbol is required.");

    createStrategy.mutate(
      { ...form },
      {
        onSuccess: () => {
          toast.success("Strategy created!");
          setShowCreate(false);
          setForm({
            name: "", description: "", token_symbol: "", token_contract: "",
            chain: "ethereum", signal_direction: "bullish", min_confidence: "0.60",
            action: "buy", size_pct: "10",
          });
        },
        onError: () => toast.error("Failed to create strategy."),
      }
    );
  }

  function handleRun(s: Strategy) {
    runStrategy.mutate(s.id, {
      onSuccess: (res) => {
        if (res.triggered) toast.success(`Strategy "${s.name}" fired a trade!`);
        else toast(`Strategy "${s.name}" evaluated — no trade (conditions not met).`);
      },
      onError: () => toast.error("Evaluation failed."),
    });
  }

  const runsById = runs.reduce<Record<string, StrategyRun[]>>((acc, r) => {
    (acc[r.strategy_id] = acc[r.strategy_id] ?? []).push(r);
    return acc;
  }, {});

  const SelectField = ({
    label, k, options,
  }: { label: string; k: keyof typeof form; options: string[] }) => (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-white/60">{label}</label>
      <select
        {...field(k)}
        className="rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white focus:border-brand focus:outline-none"
      >
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/50">
          Strategies auto-run every 5 min. A trade fires when the prediction signal matches
          your configured direction + confidence.
        </p>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4" />
          New Strategy
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-10"><Spinner /></div>
      ) : !strategies.length ? (
        <div className="flex flex-col items-center py-10 text-white/40">
          <Bot className="mb-2 h-8 w-8" />
          <p className="text-sm">No strategies yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {strategies.map((s) => {
            const lastRun = runsById[s.id]?.[0];
            return (
              <div
                key={s.id}
                className={clsx(
                  "rounded-lg border p-4 transition-colors",
                  s.is_active
                    ? "border-surface-border bg-surface-card"
                    : "border-surface-border/40 bg-surface-card/50 opacity-60"
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-white">{s.name}</p>
                      <span
                        className={clsx(
                          "rounded px-1.5 py-0.5 text-xs font-semibold uppercase",
                          s.action === "buy"
                            ? "bg-success/10 text-success"
                            : "bg-danger/10 text-danger"
                        )}
                      >
                        {s.action}
                      </span>
                      <span className="rounded bg-brand/10 px-1.5 py-0.5 text-xs text-brand">
                        {s.signal_direction}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-white/40">
                      {s.token_symbol} · {s.chain} · {s.size_pct}% of{" "}
                      {s.action === "buy" ? "cash" : "position"} ·
                      min confidence {(parseFloat(s.min_confidence) * 100).toFixed(0)}%
                    </p>
                    {lastRun && (
                      <p className="mt-1 text-xs text-white/30">
                        Last run:{" "}
                        <span
                          className={lastRun.triggered ? "text-success" : "text-white/30"}
                        >
                          {lastRun.triggered ? "Fired" : "No trade"}
                        </span>{" "}
                        — {new Date(lastRun.evaluated_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      onClick={() => handleRun(s)}
                      title="Run now"
                      className="rounded p-1.5 text-white/30 transition-colors hover:bg-brand/10 hover:text-brand"
                    >
                      <Play className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() =>
                        toggleStrategy.mutate({ strategyId: s.id, is_active: !s.is_active })
                      }
                      className={clsx(
                        "rounded-full px-2 py-0.5 text-xs font-medium transition-colors",
                        s.is_active
                          ? "bg-success/10 text-success hover:bg-danger/10 hover:text-danger"
                          : "bg-surface-elevated text-white/30 hover:text-white"
                      )}
                    >
                      {s.is_active ? "Active" : "Paused"}
                    </button>
                    <button
                      onClick={() => {
                        if (!confirm(`Delete strategy "${s.name}"?`)) return;
                        deleteStrategy.mutate(s.id, {
                          onSuccess: () => toast.success("Strategy deleted."),
                        });
                      }}
                      className="rounded p-1.5 text-white/20 transition-colors hover:text-danger"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Execution log */}
      {runs.length > 0 && (
        <section>
          <h3 className="mb-3 text-sm font-semibold text-white">Execution Log</h3>
          <div className="overflow-x-auto rounded-lg border border-surface-border">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-surface-border text-left text-white/40">
                  <th className="px-3 py-2">Time</th>
                  <th className="px-3 py-2">Strategy</th>
                  <th className="px-3 py-2">Signal</th>
                  <th className="px-3 py-2">Result</th>
                  <th className="px-3 py-2">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {runs.slice(0, 20).map((r) => {
                  const strategyName =
                    strategies.find((s) => s.id === r.strategy_id)?.name ?? r.strategy_id.slice(0, 8);
                  return (
                    <tr key={r.id} className="hover:bg-surface-elevated/30">
                      <td className="px-3 py-2 text-white/40">
                        {new Date(r.evaluated_at).toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-white/70">{strategyName}</td>
                      <td className="px-3 py-2">
                        {r.signal_direction ? (
                          <span
                            className={clsx(
                              "rounded px-1 py-0.5 uppercase",
                              r.signal_direction === "bullish"
                                ? "bg-success/10 text-success"
                                : r.signal_direction === "bearish"
                                ? "bg-danger/10 text-danger"
                                : "text-white/40"
                            )}
                          >
                            {r.signal_direction}
                          </span>
                        ) : (
                          "—"
                        )}
                        {r.signal_confidence && (
                          <span className="ml-1 text-white/30">
                            {(parseFloat(r.signal_confidence) * 100).toFixed(0)}%
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={r.triggered ? "text-success" : "text-white/30"}
                        >
                          {r.triggered ? "Fired" : "Skipped"}
                        </span>
                      </td>
                      <td className="max-w-xs truncate px-3 py-2 text-white/30">
                        {r.reason ?? "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Create strategy modal */}
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="New Strategy">
        <div className="flex flex-col gap-3">
          <Input label="Strategy Name" {...field("name")} placeholder="WETH Bullish Accumulator" />
          <Input label="Token Symbol" {...field("token_symbol")} placeholder="WETH" />
          <Input
            label="Contract Address (0x…)"
            {...field("token_contract")}
            placeholder={"0x" + "0".repeat(40)}
          />
          <SelectField label="Chain" k="chain" options={CHAINS} />
          <SelectField
            label="Signal Direction"
            k="signal_direction"
            options={["bullish", "bearish", "any"]}
          />
          <Input
            label="Min Confidence (0–1)"
            type="number"
            min="0"
            max="1"
            step="0.05"
            {...field("min_confidence")}
          />
          <SelectField label="Action" k="action" options={["buy", "sell"]} />
          <Input
            label="Size % (of cash or position)"
            type="number"
            min="1"
            max="100"
            {...field("size_pct")}
          />
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={createStrategy.isPending}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

// ─── Risk Profile Tab ─────────────────────────────────────────────────────────

function RiskProfileTab({ portfolioId }: { portfolioId: string }) {
  const { data: profile } = useRiskProfile(portfolioId);
  const upsert = useUpsertRiskProfile(portfolioId);

  const [form, setForm] = useState({
    stop_loss_pct: "",
    take_profit_pct: "",
    max_position_pct: "",
    max_drawdown_pct: "",
  });
  const [initialized, setInitialized] = useState(false);

  if (profile && !initialized) {
    setForm({
      stop_loss_pct: profile.stop_loss_pct,
      take_profit_pct: profile.take_profit_pct,
      max_position_pct: profile.max_position_pct,
      max_drawdown_pct: profile.max_drawdown_pct,
    });
    setInitialized(true);
  }

  if (!initialized && !profile) {
    setForm({
      stop_loss_pct: "10",
      take_profit_pct: "50",
      max_position_pct: "25",
      max_drawdown_pct: "30",
    });
    setInitialized(true);
  }

  function handleSave() {
    upsert.mutate(form, {
      onSuccess: () => toast.success("Risk profile saved."),
      onError: () => toast.error("Failed to save."),
    });
  }

  const RiskInput = ({
    label,
    k,
    hint,
  }: { label: string; k: keyof typeof form; hint: string }) => (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-white">{label}</label>
      <p className="text-xs text-white/40">{hint}</p>
      <div className="flex items-center gap-2">
        <input
          type="number"
          min="0"
          step="1"
          value={form[k]}
          onChange={(e) => setForm((f) => ({ ...f, [k]: e.target.value }))}
          className="w-28 rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white focus:border-brand focus:outline-none"
        />
        <span className="text-sm text-white/40">%</span>
      </div>
    </div>
  );

  return (
    <div className="max-w-md space-y-6">
      <p className="text-sm text-white/50">
        These rules apply to all auto-trades in this portfolio. Stop-loss and take-profit
        trigger automatic sells; max drawdown pauses all strategies.
      </p>

      <div className="space-y-4 rounded-lg border border-surface-border bg-surface-card p-5">
        <RiskInput
          label="Stop-Loss"
          k="stop_loss_pct"
          hint="Auto-sell if position drops this % below avg entry price."
        />
        <RiskInput
          label="Take-Profit"
          k="take_profit_pct"
          hint="Auto-sell if position rises this % above avg entry price."
        />
        <RiskInput
          label="Max Position Size"
          k="max_position_pct"
          hint="Strategy buys capped at this % of total equity (per trade)."
        />
        <RiskInput
          label="Max Drawdown"
          k="max_drawdown_pct"
          hint="Pause all strategies if portfolio drops this % below starting balance."
        />
      </div>

      <Button onClick={handleSave} loading={upsert.isPending}>
        Save Risk Profile
      </Button>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

type Tab = "positions" | "trades" | "strategies" | "risk";

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: "positions", label: "Positions", icon: TrendingUp },
  { id: "trades", label: "Trade History", icon: ChevronRight },
  { id: "strategies", label: "Strategies", icon: Bot },
  { id: "risk", label: "Risk Profile", icon: Shield },
];

const CHAINS_MODAL = ["ethereum", "bsc", "polygon", "arbitrum", "optimism"];

export default function PortfolioDetailPage() {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const { data: summary, isLoading } = usePortfolioSummary(portfolioId);
  const { data: trades } = useTradeHistory(portfolioId);
  const executeTrade = useExecuteTrade(portfolioId);

  const [tab, setTab] = useState<Tab>("positions");
  const [showTrade, setShowTrade] = useState(false);
  const [tradeType, setTradeType] = useState<"buy" | "sell">("buy");
  const [symbol, setSymbol] = useState("");
  const [contract, setContract] = useState("");
  const [chain, setChain] = useState("ethereum");
  const [qty, setQty] = useState("");

  function handleTrade() {
    if (!symbol.trim()) return toast.error("Token symbol is required.");
    if (contract.length !== 42 || !contract.startsWith("0x"))
      return toast.error("Contract must be a valid 42-char 0x address.");
    const q = parseFloat(qty);
    if (isNaN(q) || q <= 0) return toast.error("Quantity must be positive.");

    executeTrade.mutate(
      {
        trade_type: tradeType,
        token_symbol: symbol.toUpperCase(),
        token_contract: contract.toLowerCase(),
        chain,
        quantity: qty,
      },
      {
        onSuccess: () => {
          toast.success(`${tradeType === "buy" ? "Bought" : "Sold"} ${symbol.toUpperCase()}!`);
          setShowTrade(false);
          setSymbol("");
          setContract("");
          setQty("");
        },
        onError: (err: unknown) => {
          const msg =
            (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
            "Trade failed.";
          toast.error(msg);
        },
      }
    );
  }

  if (isLoading)
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );

  if (!summary) return null;

  const { portfolio, positions } = summary;
  const totalReturn = parseFloat(summary.total_return);

  return (
    <>
      <Header
        title={portfolio.name}
        subtitle="Paper portfolio — live prices, simulated execution"
        actions={
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => { setTradeType("sell"); setShowTrade(true); }}
            >
              <TrendingDown className="h-4 w-4" />
              Sell
            </Button>
            <Button
              size="sm"
              onClick={() => { setTradeType("buy"); setShowTrade(true); }}
            >
              <TrendingUp className="h-4 w-4" />
              Buy
            </Button>
          </div>
        }
      />

      <div className="p-6 space-y-6">
        <Link
          href="/dashboard/paper-trading"
          className="inline-flex items-center gap-1.5 text-xs text-white/40 hover:text-white"
        >
          <ArrowLeft className="h-3 w-3" />
          All portfolios
        </Link>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Cash", value: usd(portfolio.current_cash) },
            { label: "Positions Value", value: usd(summary.total_position_value) },
            { label: "Total Equity", value: usd(summary.total_equity) },
            {
              label: "Total Return",
              value: (
                <span className={clsx("font-mono", totalReturn >= 0 ? "text-success" : "text-danger")}>
                  {totalReturn >= 0 ? "+" : ""}
                  {usd(summary.total_return)}{" "}
                  <span className="text-sm">({pct(summary.total_return_pct)})</span>
                </span>
              ),
            },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-lg border border-surface-border bg-surface-card p-4">
              <p className="mb-1 text-xs text-white/40">{label}</p>
              <p className="text-lg font-semibold text-white">{value}</p>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="border-b border-surface-border">
          <nav className="flex gap-6">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={clsx(
                  "flex items-center gap-1.5 border-b-2 pb-2 text-sm font-medium transition-colors",
                  tab === id
                    ? "border-brand text-brand"
                    : "border-transparent text-white/40 hover:text-white"
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </button>
            ))}
          </nav>
        </div>

        {tab === "positions" && (
          <section className="rounded-lg border border-surface-border bg-surface-card p-5">
            <PositionsTable positions={positions} />
          </section>
        )}

        {tab === "trades" && (
          <section className="rounded-lg border border-surface-border bg-surface-card p-5">
            <TradeHistoryTable trades={trades ?? []} />
          </section>
        )}

        {tab === "strategies" && <StrategiesTab portfolioId={portfolioId} />}

        {tab === "risk" && <RiskProfileTab portfolioId={portfolioId} />}
      </div>

      {/* Trade modal */}
      <Modal
        isOpen={showTrade}
        onClose={() => setShowTrade(false)}
        title={tradeType === "buy" ? "Buy Token" : "Sell Token"}
      >
        <div className="flex flex-col gap-4">
          <div className="flex gap-2">
            {(["buy", "sell"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTradeType(t)}
                className={clsx(
                  "flex-1 rounded-lg py-2 text-sm font-semibold capitalize transition-colors",
                  tradeType === t
                    ? t === "buy"
                      ? "bg-success/10 text-success"
                      : "bg-danger/10 text-danger"
                    : "text-white/40 hover:text-white"
                )}
              >
                {t}
              </button>
            ))}
          </div>

          <Input label="Token Symbol" value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="WETH" />
          <Input
            label="Contract Address (0x…)"
            value={contract}
            onChange={(e) => setContract(e.target.value)}
            placeholder={"0x" + "0".repeat(40)}
          />
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-white/60">Chain</label>
            <select
              value={chain}
              onChange={(e) => setChain(e.target.value)}
              className="rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white focus:border-brand focus:outline-none"
            >
              {CHAINS_MODAL.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <Input label="Quantity" type="number" min="0" step="any" value={qty} onChange={(e) => setQty(e.target.value)} placeholder="1.0" />
          <p className="text-xs text-white/40">Price will be fetched live from CoinGecko at execution time.</p>

          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" onClick={() => setShowTrade(false)}>Cancel</Button>
            <Button
              variant={tradeType === "buy" ? "primary" : "danger"}
              onClick={handleTrade}
              loading={executeTrade.isPending}
            >
              {tradeType === "buy" ? "Buy" : "Sell"}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
