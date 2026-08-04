interface ScoreGaugeProps {
  score: number;  // 0.0 – 1.0
  size?: "sm" | "md" | "lg";
}

function scoreColor(score: number) {
  if (score >= 0.7) return "#00C853";   // success
  if (score >= 0.4) return "#FFD600";   // warning
  return "#FF3D00";                      // danger
}

function scoreLabel(score: number) {
  if (score >= 0.8) return "Exceptional";
  if (score >= 0.6) return "Strong";
  if (score >= 0.4) return "Average";
  if (score >= 0.2) return "Weak";
  return "New";
}

export function ScoreGauge({ score, size = "md" }: ScoreGaugeProps) {
  const pct = Math.round(score * 100);
  const color = scoreColor(score);
  const label = scoreLabel(score);

  const dim = size === "sm" ? 56 : size === "lg" ? 96 : 72;
  const stroke = size === "sm" ? 5 : size === "lg" ? 8 : 6;
  const r = (dim - stroke * 2) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - score);
  const fontSize = size === "sm" ? 12 : size === "lg" ? 20 : 16;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={dim} height={dim} className="-rotate-90">
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={r}
          fill="none"
          stroke="#30363D"
          strokeWidth={stroke}
        />
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="central"
          fill="white"
          fontSize={fontSize}
          fontWeight="bold"
          className="rotate-90 origin-center"
          style={{ transform: `rotate(90deg)`, transformOrigin: `${dim / 2}px ${dim / 2}px` }}
        >
          {pct}
        </text>
      </svg>
      <span className="text-xs font-medium" style={{ color }}>
        {label}
      </span>
    </div>
  );
}
