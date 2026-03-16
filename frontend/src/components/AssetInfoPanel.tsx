"use client";
import { useState, useEffect } from "react";
import { X, TrendingUp, TrendingDown, Calendar, Users, BarChart3, Loader2 } from "lucide-react";
import { getAssetInfo } from "@/lib/api";
import type { AssetInfo } from "@/lib/types";
import { formatCurrency } from "@/lib/format";

interface Props {
  symbol: string;
  onClose: () => void;
}

export default function AssetInfoPanel({ symbol, onClose }: Props) {
  const [info, setInfo] = useState<AssetInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getAssetInfo(symbol)
      .then((res) => setInfo(res.data))
      .catch(() => setError("Failed to load asset info"))
      .finally(() => setLoading(false));
  }, [symbol]);

  const totalAnalyst = (info?.analyst_buy ?? 0) + (info?.analyst_hold ?? 0) + (info?.analyst_sell ?? 0);
  const buyPct = totalAnalyst > 0 ? Math.round((info!.analyst_buy / totalAnalyst) * 100) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end" onClick={onClose}>
      <div
        className="h-full w-full max-w-md bg-[var(--card)] border-l border-[var(--card-border)] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-[var(--card)] border-b border-[var(--card-border)] px-5 py-4 flex items-center justify-between">
          <div>
            <div className="font-bold text-lg">{symbol}</div>
            {info?.name && <div className="text-sm text-[var(--muted)]">{info.name}</div>}
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/10 text-[var(--muted)] hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-20 text-[var(--muted)]">
            <Loader2 className="w-6 h-6 animate-spin mr-3" /> Loading...
          </div>
        )}

        {error && (
          <div className="m-5 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {info && !loading && (
          <div className="p-5 space-y-5">
            {/* Price */}
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-white/5 p-3">
                <div className="text-xs text-[var(--muted)] mb-1">Current Price</div>
                <div className="font-semibold text-lg">{info.current_price ? formatCurrency(info.current_price) : "—"}</div>
              </div>
              <div className="rounded-lg bg-white/5 p-3">
                <div className="text-xs text-[var(--muted)] mb-1">Market Cap</div>
                <div className="font-semibold text-lg">
                  {info.market_cap ? `$${(info.market_cap / 1e9).toFixed(1)}B` : "—"}
                </div>
              </div>
            </div>

            {/* 52-week range */}
            {(info.week_52_high || info.week_52_low) && (
              <div className="rounded-lg bg-white/5 p-3">
                <div className="text-xs text-[var(--muted)] mb-2 flex items-center gap-1.5">
                  <BarChart3 className="w-3.5 h-3.5" /> 52-Week Range
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[var(--accent-red)]">{info.week_52_low ? formatCurrency(info.week_52_low) : "—"}</span>
                  <div className="flex-1 mx-3 h-1.5 bg-white/10 rounded-full relative">
                    {info.current_price && info.week_52_low && info.week_52_high && (
                      <div
                        className="absolute top-0 h-full bg-[var(--accent)] rounded-full"
                        style={{ width: `${Math.min(100, ((info.current_price - info.week_52_low) / (info.week_52_high - info.week_52_low)) * 100)}%` }}
                      />
                    )}
                  </div>
                  <span className="text-[var(--accent-green)]">{info.week_52_high ? formatCurrency(info.week_52_high) : "—"}</span>
                </div>
              </div>
            )}

            {/* Dividend & Earnings */}
            <div className="rounded-lg bg-white/5 p-3 space-y-2">
              <div className="text-xs text-[var(--muted)] mb-1 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" /> Dates & Dividends
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-[var(--muted)] text-xs">Dividend Yield</span>
                  <div className="font-medium">
                    {info.dividend_yield ? `${(info.dividend_yield * 100).toFixed(2)}%` : "—"}
                  </div>
                </div>
                <div>
                  <span className="text-[var(--muted)] text-xs">Ex-Dividend Date</span>
                  <div className="font-medium">{info.ex_dividend_date || "—"}</div>
                </div>
                <div>
                  <span className="text-[var(--muted)] text-xs">Next Earnings</span>
                  <div className="font-medium">{info.next_earnings_date || "—"}</div>
                </div>
              </div>
            </div>

            {/* Analyst ratings */}
            {totalAnalyst > 0 && (
              <div className="rounded-lg bg-white/5 p-3">
                <div className="text-xs text-[var(--muted)] mb-3 flex items-center gap-1.5">
                  <BarChart3 className="w-3.5 h-3.5" /> Analyst Consensus
                  <span className="ml-auto font-medium text-white">{buyPct}% Buy</span>
                </div>
                <div className="flex h-2.5 rounded-full overflow-hidden gap-px">
                  {info.analyst_buy > 0 && (
                    <div className="bg-emerald-500 rounded-l-full" style={{ width: `${(info.analyst_buy / totalAnalyst) * 100}%` }} />
                  )}
                  {info.analyst_hold > 0 && (
                    <div className="bg-amber-500" style={{ width: `${(info.analyst_hold / totalAnalyst) * 100}%` }} />
                  )}
                  {info.analyst_sell > 0 && (
                    <div className="bg-red-500 rounded-r-full" style={{ width: `${(info.analyst_sell / totalAnalyst) * 100}%` }} />
                  )}
                </div>
                <div className="flex justify-between text-xs text-[var(--muted)] mt-2">
                  <span className="text-emerald-400">Buy {info.analyst_buy}</span>
                  <span className="text-amber-400">Hold {info.analyst_hold}</span>
                  <span className="text-red-400">Sell {info.analyst_sell}</span>
                </div>
              </div>
            )}

            {/* Insider transactions */}
            {info.insider_transactions.length > 0 && (
              <div>
                <div className="text-xs text-[var(--muted)] mb-3 flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5" /> Recent Insider Transactions
                </div>
                <div className="space-y-2">
                  {info.insider_transactions.map((txn, i) => {
                    const isBuy = txn.transaction.toLowerCase().includes("buy") || txn.transaction.toLowerCase().includes("purchase");
                    return (
                      <div key={i} className="rounded-lg bg-white/5 p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="font-medium text-sm truncate">{txn.name}</div>
                            <div className="text-xs text-[var(--muted)] truncate">{txn.title}</div>
                          </div>
                          <div className="text-right shrink-0">
                            <div className={`text-xs font-medium flex items-center gap-1 ${isBuy ? "text-emerald-400" : "text-red-400"}`}>
                              {isBuy ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                              {txn.transaction}
                            </div>
                            <div className="text-xs text-[var(--muted)]">{txn.date}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 mt-1.5 text-xs text-[var(--muted)]">
                          {txn.shares !== 0 && <span>{txn.shares.toLocaleString()} shares</span>}
                          {txn.value && <span>{formatCurrency(txn.value)}</span>}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {info.insider_transactions.length === 0 && !loading && (
              <div className="text-center text-sm text-[var(--muted)] py-4">
                No recent insider transactions available (crypto assets or data unavailable)
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
