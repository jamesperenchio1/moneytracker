"use client";
import { useState } from "react";
import type { Holding, BrokerageAccount } from "@/lib/types";
import { formatCurrency, formatPct } from "@/lib/format";
import { createHolding, updateHolding, deleteHolding, logDividend } from "@/lib/api";
import { Pencil, Trash2, Plus, Check, X, DollarSign, Info } from "lucide-react";
import AssetInfoPanel from "@/components/AssetInfoPanel";

interface Props {
  holdings: Holding[];
  accounts: BrokerageAccount[];
  onRefresh: () => void;
}

interface EditState {
  id: number;
  quantity: string;
  avg_cost_basis: string;
  purchase_date: string;
}

interface AddState {
  brokerage_account_id: string;
  symbol: string;
  quantity: string;
  avg_cost_basis: string;
  asset_type: string;
  purchase_date: string;
}

interface DividendState {
  holding_id: number;
  symbol: string;
  amount: string;
  dividend_date: string;
  per_share: string;
}

const ASSET_TYPES = ["stock", "etf", "mutual_fund", "crypto", "bond", "other"];

export default function HoldingsTable({ holdings, accounts, onRefresh }: Props) {
  const [editing, setEditing] = useState<EditState | null>(null);
  const [adding, setAdding] = useState(false);
  const [addForm, setAddForm] = useState<AddState>({
    brokerage_account_id: accounts[0]?.id?.toString() ?? "",
    symbol: "",
    quantity: "",
    avg_cost_basis: "",
    asset_type: "stock",
    purchase_date: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dividendForm, setDividendForm] = useState<DividendState | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  const handleEdit = (h: Holding) => {
    setEditing({
      id: h.id,
      quantity: h.quantity.toString(),
      avg_cost_basis: h.avg_cost_basis.toString(),
      purchase_date: h.purchase_date ?? "",
    });
    setAdding(false);
    setError(null);
  };

  const handleSaveEdit = async () => {
    if (!editing) return;
    setSaving(true);
    setError(null);
    try {
      await updateHolding(editing.id, {
        quantity: parseFloat(editing.quantity),
        avg_cost_basis: parseFloat(editing.avg_cost_basis),
        purchase_date: editing.purchase_date || undefined,
      });
      setEditing(null);
      onRefresh();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to save";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number, symbol: string) => {
    if (!confirm(`Remove ${symbol} from your holdings?`)) return;
    try {
      await deleteHolding(id);
      onRefresh();
    } catch {
      setError("Failed to delete holding");
    }
  };

  const handleAdd = async () => {
    if (!addForm.symbol || !addForm.quantity || !addForm.avg_cost_basis || !addForm.brokerage_account_id) {
      setError("All fields are required");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createHolding({
        brokerage_account_id: parseInt(addForm.brokerage_account_id),
        symbol: addForm.symbol.toUpperCase(),
        quantity: parseFloat(addForm.quantity),
        avg_cost_basis: parseFloat(addForm.avg_cost_basis),
        asset_type: addForm.asset_type,
        purchase_date: addForm.purchase_date || undefined,
      });
      setAdding(false);
      setAddForm({ brokerage_account_id: accounts[0]?.id?.toString() ?? "", symbol: "", quantity: "", avg_cost_basis: "", asset_type: "stock", purchase_date: "" });
      onRefresh();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to add holding";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleLogDividend = async () => {
    if (!dividendForm || !dividendForm.amount || !dividendForm.dividend_date) return;
    setSaving(true);
    try {
      await logDividend({
        holding_id: dividendForm.holding_id,
        amount: parseFloat(dividendForm.amount),
        dividend_date: dividendForm.dividend_date,
        per_share: dividendForm.per_share ? parseFloat(dividendForm.per_share) : undefined,
      });
      setDividendForm(null);
    } catch {
      setError("Failed to log dividend");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      {error && (
        <div className="mb-3 px-3 py-2 rounded-lg bg-red-500/10 text-red-400 text-sm">{error}</div>
      )}

      {/* Dividend modal */}
      {dividendForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-6 w-80 space-y-4">
            <h3 className="font-medium">Log Dividend — {dividendForm.symbol}</h3>
            <div>
              <label className="block text-xs text-[var(--muted)] mb-1">Date</label>
              <input type="date" value={dividendForm.dividend_date}
                onChange={(e) => setDividendForm({ ...dividendForm, dividend_date: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]" />
            </div>
            <div>
              <label className="block text-xs text-[var(--muted)] mb-1">Total Amount (USD)</label>
              <input type="number" step="any" placeholder="0.00" value={dividendForm.amount}
                onChange={(e) => setDividendForm({ ...dividendForm, amount: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]" />
            </div>
            <div>
              <label className="block text-xs text-[var(--muted)] mb-1">Per Share (optional)</label>
              <input type="number" step="any" placeholder="0.00" value={dividendForm.per_share}
                onChange={(e) => setDividendForm({ ...dividendForm, per_share: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]" />
            </div>
            <div className="flex gap-2">
              <button onClick={handleLogDividend} disabled={saving}
                className="flex-1 px-3 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50">
                {saving ? "Saving..." : "Log Dividend"}
              </button>
              <button onClick={() => setDividendForm(null)}
                className="px-3 py-2 rounded-lg text-sm text-[var(--muted)] hover:text-white hover:bg-white/5">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

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
              <th className="text-right py-3 px-2 w-24"></th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => (
              <tr key={h.id} className="border-b border-[var(--card-border)] hover:bg-white/5 group">
                <td className="py-3 px-2">
                  <div className="font-medium">{h.asset_symbol}</div>
                  <div className="text-xs text-[var(--muted)]">{h.asset_name}</div>
                  {h.purchase_date && (
                    <div className="text-[10px] text-[var(--muted)] mt-0.5">
                      Since {new Date(h.purchase_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    </div>
                  )}
                </td>
                <td className="py-3 px-2 text-[var(--muted)]">{h.brokerage_name}</td>
                {editing?.id === h.id ? (
                  <>
                    <td className="py-2 px-2 text-right">
                      <input type="number" step="any" value={editing.quantity}
                        onChange={(e) => setEditing({ ...editing, quantity: e.target.value })}
                        className="w-24 text-right bg-[var(--input-bg)] border border-[var(--card-border)] rounded px-2 py-1" />
                    </td>
                    <td className="py-2 px-2 text-right">
                      <input type="number" step="any" value={editing.avg_cost_basis}
                        onChange={(e) => setEditing({ ...editing, avg_cost_basis: e.target.value })}
                        className="w-24 text-right bg-[var(--input-bg)] border border-[var(--card-border)] rounded px-2 py-1" />
                    </td>
                    <td className="py-2 px-2 text-right">
                      <input type="date" value={editing.purchase_date}
                        onChange={(e) => setEditing({ ...editing, purchase_date: e.target.value })}
                        className="w-32 bg-[var(--input-bg)] border border-[var(--card-border)] rounded px-2 py-1 text-xs" />
                    </td>
                    <td className="py-2 px-2 text-right text-[var(--muted)]">—</td>
                    <td className="py-2 px-2 text-right text-[var(--muted)]">—</td>
                    <td className="py-2 px-2 text-right">
                      <div className="flex justify-end gap-1">
                        <button onClick={handleSaveEdit} disabled={saving}
                          className="p-1.5 rounded hover:bg-green-500/20 text-green-400" title="Save">
                          <Check className="w-4 h-4" />
                        </button>
                        <button onClick={() => setEditing(null)}
                          className="p-1.5 rounded hover:bg-white/10 text-[var(--muted)]" title="Cancel">
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="py-3 px-2 text-right">{h.quantity.toFixed(4)}</td>
                    <td className="py-3 px-2 text-right">{formatCurrency(h.avg_cost_basis)}</td>
                    <td className="py-3 px-2 text-right">
                      {h.current_price ? formatCurrency(h.current_price) : "—"}
                    </td>
                    <td className="py-3 px-2 text-right font-medium">
                      {h.market_value ? formatCurrency(h.market_value) : "—"}
                    </td>
                    <td className="py-3 px-2 text-right">
                      {h.gain_loss !== null && h.gain_loss !== undefined ? (
                        <div>
                          <span className={h.gain_loss >= 0 ? "text-[var(--accent-green)]" : "text-[var(--accent-red)]"}>
                            {formatCurrency(h.gain_loss)}
                          </span>
                          {h.gain_loss_pct !== null && h.gain_loss_pct !== undefined && (
                            <div className={`text-xs ${h.gain_loss_pct >= 0 ? "text-[var(--accent-green)]" : "text-[var(--accent-red)]"}`}>
                              {formatPct(h.gain_loss_pct)}
                            </div>
                          )}
                        </div>
                      ) : "—"}
                    </td>
                    <td className="py-3 px-2 text-right">
                      <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100">
                        <button onClick={() => setSelectedSymbol(h.asset_symbol)}
                          className="p-1.5 rounded hover:bg-purple-500/20 text-purple-400" title="Stock info">
                          <Info className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => setDividendForm({ holding_id: h.id, symbol: h.asset_symbol, amount: "", dividend_date: new Date().toISOString().split("T")[0], per_share: "" })}
                          className="p-1.5 rounded hover:bg-yellow-500/20 text-yellow-400" title="Log dividend">
                          <DollarSign className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => handleEdit(h)}
                          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-400" title="Edit">
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => handleDelete(h.id, h.asset_symbol)}
                          className="p-1.5 rounded hover:bg-red-500/20 text-red-400" title="Delete">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}

            {/* Add new row */}
            {adding && (
              <tr className="border-b border-[var(--card-border)] bg-white/5">
                <td className="py-2 px-2">
                  <input type="text" placeholder="SYMBOL" value={addForm.symbol}
                    onChange={(e) => setAddForm({ ...addForm, symbol: e.target.value.toUpperCase() })}
                    className="w-20 bg-[var(--input-bg)] border border-[var(--card-border)] rounded px-2 py-1 text-sm font-medium uppercase"
                    autoFocus />
                </td>
                <td className="py-2 px-2">
                  <select value={addForm.brokerage_account_id}
                    onChange={(e) => setAddForm({ ...addForm, brokerage_account_id: e.target.value })}
                    className="w-32 bg-[var(--input-bg)] border border-[var(--card-border)] rounded px-2 py-1 text-sm">
                    {accounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.brokerage_name} {a.account_name ? `(${a.account_name})` : ""}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="py-2 px-2 text-right">
                  <input type="number" step="any" placeholder="Qty" value={addForm.quantity}
                    onChange={(e) => setAddForm({ ...addForm, quantity: e.target.value })}
                    className="w-20 text-right bg-[var(--input-bg)] border border-[var(--card-border)] rounded px-2 py-1 text-sm" />
                </td>
                <td className="py-2 px-2 text-right">
                  <input type="number" step="any" placeholder="Cost" value={addForm.avg_cost_basis}
                    onChange={(e) => setAddForm({ ...addForm, avg_cost_basis: e.target.value })}
                    className="w-24 text-right bg-[var(--input-bg)] border border-[var(--card-border)] rounded px-2 py-1 text-sm" />
                </td>
                <td className="py-2 px-2 text-right">
                  <div className="flex flex-col gap-1 items-end">
                    <select value={addForm.asset_type}
                      onChange={(e) => setAddForm({ ...addForm, asset_type: e.target.value })}
                      className="w-28 bg-[var(--input-bg)] border border-[var(--card-border)] rounded px-2 py-1 text-sm">
                      {ASSET_TYPES.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                    <input type="date" value={addForm.purchase_date} placeholder="Purchase date"
                      onChange={(e) => setAddForm({ ...addForm, purchase_date: e.target.value })}
                      className="w-32 bg-[var(--input-bg)] border border-[var(--card-border)] rounded px-2 py-1 text-xs" />
                  </div>
                </td>
                <td className="py-2 px-2" />
                <td className="py-2 px-2" />
                <td className="py-2 px-2 text-right">
                  <div className="flex justify-end gap-1">
                    <button onClick={handleAdd} disabled={saving}
                      className="p-1.5 rounded hover:bg-green-500/20 text-green-400" title="Add">
                      <Check className="w-4 h-4" />
                    </button>
                    <button onClick={() => { setAdding(false); setError(null); }}
                      className="p-1.5 rounded hover:bg-white/10 text-[var(--muted)]" title="Cancel">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            )}

            {holdings.length === 0 && !adding && (
              <tr>
                <td colSpan={8} className="py-8 text-center text-[var(--muted)]">
                  No holdings yet. Click &ldquo;Add Holding&rdquo; to add your positions manually.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {!adding && accounts.length > 0 && (
        <div className="mt-4">
          <button onClick={() => { setAdding(true); setEditing(null); setError(null); }}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 text-sm transition-colors">
            <Plus className="w-4 h-4" />
            Add Holding
          </button>
        </div>
      )}

      {accounts.length === 0 && (
        <div className="mt-3 text-sm text-[var(--muted)]">
          First create a brokerage account in Settings → Brokerage Accounts, then add holdings here.
        </div>
      )}

      {/* Asset info panel */}
      {selectedSymbol && (
        <AssetInfoPanel symbol={selectedSymbol} onClose={() => setSelectedSymbol(null)} />
      )}
    </div>
  );
}
