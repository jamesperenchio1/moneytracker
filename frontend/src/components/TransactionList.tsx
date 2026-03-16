"use client";
import { useState, useEffect, useCallback } from "react";
import type { Transaction, Category, CategorySuggestion } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/format";
import { getCategories, updateTransaction, suggestCategory } from "@/lib/api";

interface Props {
  transactions: Transaction[];
  onTransactionUpdate?: (updated: Transaction) => void;
}

const BANK_COLORS: Record<string, string> = {
  kasikorn: "bg-green-500/15 text-green-400 border-green-500/30",
  scb: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  bangkok_bank: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  krungsri: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  krungthai: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  ttb: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  other: "bg-slate-500/15 text-slate-400 border-slate-500/30",
};

const CATEGORY_COLORS: Record<string, string> = {
  food: "bg-orange-500/15 text-orange-400",
  transportation: "bg-blue-500/15 text-blue-400",
  shopping: "bg-pink-500/15 text-pink-400",
  utilities: "bg-amber-500/15 text-amber-400",
  transfers: "bg-cyan-500/15 text-cyan-400",
  entertainment: "bg-purple-500/15 text-purple-400",
  healthcare: "bg-green-500/15 text-green-400",
  income: "bg-emerald-500/15 text-emerald-400",
  rent: "bg-red-500/15 text-red-400",
  subscriptions: "bg-indigo-500/15 text-indigo-400",
  education: "bg-teal-500/15 text-teal-400",
  investment: "bg-yellow-500/15 text-yellow-400",
  other: "bg-gray-500/15 text-gray-400",
};

function getBankBadgeClass(bankName?: string): string {
  if (!bankName) return "bg-gray-500/15 text-gray-400 border-gray-500/30";
  const key = bankName.toLowerCase().replace(/\s+/g, "_");
  for (const [k, v] of Object.entries(BANK_COLORS)) {
    if (key.includes(k)) return v;
  }
  return "bg-gray-500/15 text-gray-400 border-gray-500/30";
}

function getCategoryBadgeClass(categoryName?: string): string {
  if (!categoryName) return "bg-gray-500/15 text-gray-400";
  const key = categoryName.toLowerCase().replace(/[\s&/]+/g, "_");
  for (const [k, v] of Object.entries(CATEGORY_COLORS)) {
    if (key.includes(k)) return v;
  }
  return "bg-violet-500/15 text-violet-400";
}

function DetailRow({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-0.5">
        {label}
      </span>
      <span className="text-xs text-[var(--foreground)]">{value}</span>
    </div>
  );
}

function CategoryEditor({
  transaction,
  allCategories,
  onUpdate,
}: {
  transaction: Transaction;
  allCategories: Category[];
  onUpdate: (updated: Transaction) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<CategorySuggestion[]>([]);
  const [loading, setLoading] = useState(false);

  const loadSuggestions = useCallback(async () => {
    if (!transaction.description) return;
    try {
      const res = await suggestCategory(transaction.description);
      setSuggestions(res.data.suggestions || []);
    } catch {
      // ignore
    }
  }, [transaction.description]);

  const handleOpen = () => {
    setIsOpen(true);
    loadSuggestions();
  };

  const handleSelect = async (categoryId: number) => {
    setLoading(true);
    try {
      const res = await updateTransaction(transaction.id, {
        category_id: categoryId,
      });
      onUpdate(res.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
      setIsOpen(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={handleOpen}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium cursor-pointer hover:ring-1 hover:ring-white/20 transition-all ${getCategoryBadgeClass(transaction.category_name)}`}
      >
        {transaction.category_name || "Uncategorized"}
        <svg
          className="w-2.5 h-2.5 opacity-60"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
          />
        </svg>
      </button>
    );
  }

  return (
    <div className="relative">
      <div className="absolute z-50 top-0 left-0 w-56 max-h-64 overflow-y-auto rounded-lg border border-[var(--card-border)] bg-[var(--card)] text-[var(--foreground)] shadow-xl">
        {loading && (
          <div className="p-2 text-center text-xs text-[var(--muted)]">
            Updating...
          </div>
        )}
        {!loading && (
          <>
            {suggestions.length > 0 && (
              <div className="border-b border-[var(--card-border)]">
                <div className="px-3 py-1.5 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                  Suggestions
                </div>
                {suggestions.map((s) => {
                  const cat = allCategories.find(
                    (c) => c.name === s.category_name
                  );
                  if (!cat) return null;
                  return (
                    <button
                      key={s.category_name}
                      onClick={() => handleSelect(cat.id)}
                      className="w-full text-left px-3 py-1.5 text-xs hover:bg-white/5 transition-colors flex justify-between items-center"
                    >
                      <span>{s.display_name}</span>
                      <span className="text-[10px] text-[var(--muted)]">
                        {Math.round(s.confidence * 100)}%
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
            <div className="px-3 py-1.5 text-[10px] uppercase tracking-wider text-[var(--muted)]">
              All Categories
            </div>
            {allCategories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => handleSelect(cat.id)}
                className={`w-full text-left px-3 py-1.5 text-xs hover:bg-white/5 transition-colors ${
                  transaction.category_id === cat.id
                    ? "bg-white/10 font-medium"
                    : ""
                }`}
              >
                {cat.display_name}
              </button>
            ))}
            <button
              onClick={() => setIsOpen(false)}
              className="w-full text-center px-3 py-1.5 text-[10px] text-[var(--muted)] hover:bg-white/5 border-t border-[var(--card-border)]"
            >
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default function TransactionList({
  transactions,
  onTransactionUpdate,
}: Props) {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);

  useEffect(() => {
    getCategories()
      .then((res) => setCategories(res.data))
      .catch(() => {});
  }, []);

  if (!transactions.length) {
    return (
      <div className="text-center py-8 text-[var(--muted)]">
        No transactions yet. Upload bank statements to import transactions.
      </div>
    );
  }

  const handleUpdate = (updated: Transaction) => {
    onTransactionUpdate?.(updated);
  };

  return (
    <div className="space-y-1">
      {transactions.map((txn) => {
        const isExpanded = expandedId === txn.id;
        return (
          <div key={txn.id}>
            {/* Main row */}
            <div
              onClick={() => setExpandedId(isExpanded ? null : txn.id)}
              className={`flex items-center justify-between p-3 rounded-lg border border-[var(--card-border)] cursor-pointer transition-all ${
                isExpanded
                  ? "bg-white/5 border-white/10"
                  : "hover:bg-white/3"
              }`}
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                {/* Type indicator */}
                <div
                  className={`w-1 h-8 rounded-full shrink-0 ${
                    txn.transaction_type === "credit"
                      ? "bg-emerald-400"
                      : txn.transaction_type === "debit"
                      ? "bg-red-400"
                      : "bg-blue-400"
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">
                    {txn.description || "Transaction"}
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {txn.bank_name && (
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${getBankBadgeClass(txn.bank_name)}`}
                      >
                        {txn.bank_name}
                      </span>
                    )}
                    {txn.category_name && (
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${getCategoryBadgeClass(txn.category_name)}`}
                      >
                        {txn.category_name}
                      </span>
                    )}
                    {!txn.category_name && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-500/15 text-gray-500">
                        Uncategorized
                      </span>
                    )}
                    <span className="text-[10px] text-[var(--muted)] self-center">
                      {formatDate(txn.transaction_date)}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-3">
                <div
                  className={`font-semibold text-sm ${
                    txn.transaction_type === "credit"
                      ? "text-[var(--accent-green)]"
                      : "text-[var(--accent-red)]"
                  }`}
                >
                  {txn.transaction_type === "credit" ? "+" : "-"}
                  {formatCurrency(txn.amount, txn.currency)}
                </div>
                <svg
                  className={`w-4 h-4 text-[var(--muted)] transition-transform ${
                    isExpanded ? "rotate-180" : ""
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </div>
            </div>

            {/* Expanded detail panel */}
            {isExpanded && (
              <div className="mx-2 mb-1 p-4 rounded-b-lg border border-t-0 border-[var(--card-border)] bg-white/[0.02]">
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                  <DetailRow
                    label="Date & Time"
                    value={
                      txn.transaction_date
                        ? new Date(txn.transaction_date).toLocaleString(
                            "en-US",
                            {
                              year: "numeric",
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            }
                          )
                        : undefined
                    }
                  />
                  <DetailRow label="Type" value={txn.transaction_type?.toUpperCase()} />
                  <DetailRow
                    label="Amount"
                    value={`${formatCurrency(txn.amount, txn.currency)} ${txn.currency}`}
                  />
                  <DetailRow label="Bank" value={txn.bank_name} />
                  <DetailRow label="Description" value={txn.description} />
                  <DetailRow label="Sender" value={txn.sender} />
                  <DetailRow label="Receiver" value={txn.receiver} />
                  <DetailRow label="Reference" value={txn.reference} />
                  <DetailRow label="Source File" value={txn.statement_file_name} />
                  <DetailRow
                    label="Imported"
                    value={
                      txn.created_at
                        ? new Date(txn.created_at).toLocaleString("en-US", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })
                        : undefined
                    }
                  />
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-0.5">
                      Category
                    </span>
                    <CategoryEditor
                      transaction={txn}
                      allCategories={categories}
                      onUpdate={handleUpdate}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
