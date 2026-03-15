"use client";
import type { Holding } from "@/lib/types";
import { formatCurrency, formatPct } from "@/lib/format";

interface Props {
  holdings: Holding[];
}

export default function HoldingsTable({ holdings }: Props) {
  if (!holdings.length) {
    return (
      <div className="text-center py-8 text-[var(--muted)]">
        No holdings yet. Upload brokerage statements or add accounts to get started.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--card-border)] text-[var(--muted)]">
            <th className="text-left py-3 px-2">Symbol</th>
            <th className="text-left py-3 px-2">Platform</th>
            <th className="text-right py-3 px-2">Qty</th>
            <th className="text-right py-3 px-2">Avg Cost</th>
            <th className="text-right py-3 px-2">Price</th>
            <th className="text-right py-3 px-2">Value</th>
            <th className="text-right py-3 px-2">Gain/Loss</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => (
            <tr
              key={h.id}
              className="border-b border-[var(--card-border)] hover:bg-white/5"
            >
              <td className="py-3 px-2">
                <div className="font-medium">{h.asset_symbol}</div>
                <div className="text-xs text-[var(--muted)]">{h.asset_name}</div>
              </td>
              <td className="py-3 px-2 text-[var(--muted)]">{h.brokerage_name}</td>
              <td className="py-3 px-2 text-right">{h.quantity.toFixed(4)}</td>
              <td className="py-3 px-2 text-right">
                {formatCurrency(h.avg_cost_basis)}
              </td>
              <td className="py-3 px-2 text-right">
                {h.current_price ? formatCurrency(h.current_price) : "—"}
              </td>
              <td className="py-3 px-2 text-right font-medium">
                {h.market_value ? formatCurrency(h.market_value) : "—"}
              </td>
              <td className="py-3 px-2 text-right">
                {h.gain_loss !== null && h.gain_loss !== undefined ? (
                  <div>
                    <span
                      className={
                        h.gain_loss >= 0
                          ? "text-[var(--accent-green)]"
                          : "text-[var(--accent-red)]"
                      }
                    >
                      {formatCurrency(h.gain_loss)}
                    </span>
                    {h.gain_loss_pct !== null && h.gain_loss_pct !== undefined && (
                      <div
                        className={`text-xs ${
                          h.gain_loss_pct >= 0
                            ? "text-[var(--accent-green)]"
                            : "text-[var(--accent-red)]"
                        }`}
                      >
                        {formatPct(h.gain_loss_pct)}
                      </div>
                    )}
                  </div>
                ) : (
                  "—"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
