"use client";
import type { Transaction } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/format";

interface Props {
  transactions: Transaction[];
}

export default function TransactionList({ transactions }: Props) {
  if (!transactions.length) {
    return (
      <div className="text-center py-8 text-[var(--muted)]">
        No transactions yet. Upload bank statements to import transactions.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {transactions.map((txn) => (
        <div
          key={txn.id}
          className="flex items-center justify-between p-3 rounded-lg border border-[var(--card-border)] hover:bg-white/5"
        >
          <div className="flex-1">
            <div className="font-medium text-sm">
              {txn.description || "Transaction"}
            </div>
            <div className="text-xs text-[var(--muted)] flex gap-2 mt-1">
              <span>{txn.bank_name}</span>
              {txn.category_name && (
                <>
                  <span>·</span>
                  <span>{txn.category_name}</span>
                </>
              )}
              <span>·</span>
              <span>{formatDate(txn.transaction_date)}</span>
            </div>
          </div>
          <div
            className={`font-medium ${
              txn.transaction_type === "credit"
                ? "text-[var(--accent-green)]"
                : "text-[var(--accent-red)]"
            }`}
          >
            {txn.transaction_type === "credit" ? "+" : "-"}
            {formatCurrency(txn.amount, txn.currency)}
          </div>
        </div>
      ))}
    </div>
  );
}
