import { clsx } from "clsx";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import type { SignalDirection } from "@/types/api";

interface SignalBadgeProps {
  direction: SignalDirection;
  confidence?: number;
  size?: "sm" | "md";
}

const CONFIG: Record<
  SignalDirection,
  { label: string; color: string; Icon: React.ElementType }
> = {
  bullish: {
    label: "Bullish",
    color: "text-success bg-success/10 border-success/30",
    Icon: TrendingUp,
  },
  bearish: {
    label: "Bearish",
    color: "text-danger bg-danger/10 border-danger/30",
    Icon: TrendingDown,
  },
  neutral: {
    label: "Neutral",
    color: "text-white/50 bg-white/5 border-white/10",
    Icon: Minus,
  },
};

export function SignalBadge({ direction, confidence, size = "md" }: SignalBadgeProps) {
  const { label, color, Icon } = CONFIG[direction];
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border font-medium",
        color,
        size === "sm" ? "px-1.5 py-0.5 text-xs" : "px-2.5 py-1 text-sm",
      )}
    >
      <Icon className={size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5"} />
      {label}
      {confidence !== undefined && confidence > 0 && (
        <span className="opacity-60">
          {Math.round(confidence * 100)}%
        </span>
      )}
    </span>
  );
}
