"use client";
import { formatCurrency } from "@/lib/format";

interface PlatformData {
  platform: string;
  value: number;
  cost: number;
}

interface Props {
  platforms: PlatformData[];
  totalValue: number;
}

export default function PlatformBreakdown({ platforms, totalValue }: Props) {
  if (!platforms.length) {
    return null;
  }

  return (
    <div className="space-y-3">
      {platforms.map((p) => {
        const pct = totalValue > 0 ? (p.value / totalValue) * 100 : 0;
        const gain = p.value - p.cost;

        return (
          <div key={p.platform} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="font-medium">{p.platform}</span>
              <span>{formatCurrency(p.value)}</span>
            </div>
            <div className="w-full bg-[var(--card-border)] rounded-full h-2">
              <div
                className="bg-[var(--accent)] h-2 rounded-full transition-all"
                style={{ width: `${Math.min(pct, 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-[var(--muted)]">
              <span>{pct.toFixed(1)}% of portfolio</span>
              <span
                className={
                  gain >= 0
                    ? "text-[var(--accent-green)]"
                    : "text-[var(--accent-red)]"
                }
              >
                {gain >= 0 ? "+" : ""}
                {formatCurrency(gain)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
