"use client";
import { useEffect, useRef, useState } from "react";
import {
  CheckCircle,
  AlertCircle,
  Info,
  Loader,
  ChevronDown,
  ChevronRight,
  CreditCard,
} from "lucide-react";
import { getStatement } from "@/lib/api";
import type { AuditEntry, Statement } from "@/lib/types";
import { formatCurrency } from "@/lib/format";

interface Props {
  statementId: number;
  onComplete?: (stmt: Statement) => void;
}

const STEP_LABELS: Record<string, string> = {
  file_received: "File received",
  parser_detected: "Parser detected",
  parse_complete: "File parsed",
  account_resolved: "Account resolved",
  new_asset: "New asset",
  row: "Transaction",
  cc_payment_detected: "CC payoff found",
  cc_payment_received: "CC payment received",
  cc_statement_summary: "CC statement summary",
  cc_payment_summary: "Monthly CC payoff",
  summary: "Complete",
  error: "Error",
};

function EntryIcon({ level }: { level: string }) {
  if (level === "error") return <AlertCircle className="w-4 h-4 text-[var(--accent-red)] shrink-0" />;
  if (level === "warn") return <AlertCircle className="w-4 h-4 text-yellow-400 shrink-0" />;
  return <Info className="w-4 h-4 text-[var(--muted)] shrink-0" />;
}

function RowEntry({ entry }: { entry: AuditEntry }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetail =
    entry.date || entry.amount !== undefined || entry.description || entry.category;

  const isCCStep =
    entry.step === "cc_payment_detected" ||
    entry.step === "cc_payment_received" ||
    entry.step === "cc_payment_summary" ||
    entry.step === "cc_statement_summary";

  return (
    <div
      className={`text-xs rounded-lg px-3 py-2 ${
        isCCStep
          ? "bg-yellow-500/10 border border-yellow-500/30"
          : entry.level === "error"
          ? "bg-red-500/10 border border-red-500/20"
          : "bg-[var(--background)] border border-[var(--card-border)]"
      }`}
    >
      <div className="flex items-start gap-2">
        {isCCStep ? (
          <CreditCard className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />
        ) : (
          <EntryIcon level={entry.level} />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-[var(--muted)] uppercase tracking-wide text-[10px]">
              {STEP_LABELS[entry.step] ?? entry.step}
            </span>
            {entry.index !== undefined && (
              <span className="text-[var(--muted)] opacity-60">#{entry.index}</span>
            )}
            {hasDetail && (
              <button
                onClick={() => setExpanded((x) => !x)}
                className="ml-auto text-[var(--muted)] opacity-60 hover:opacity-100"
              >
                {expanded ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
              </button>
            )}
          </div>
          <p className="text-white/80 mt-0.5 break-words">{entry.detail}</p>

          {expanded && hasDetail && (
            <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[var(--muted)]">
              {entry.date && (
                <>
                  <span>Date</span>
                  <span className="text-white/70">{entry.date}</span>
                </>
              )}
              {entry.amount !== undefined && (
                <>
                  <span>Amount</span>
                  <span className="text-white/70">
                    {formatCurrency(entry.amount, "THB")}
                  </span>
                </>
              )}
              {entry.txn_type && (
                <>
                  <span>Type</span>
                  <span className="text-white/70 capitalize">{entry.txn_type}</span>
                </>
              )}
              {entry.description && (
                <>
                  <span>Description</span>
                  <span className="text-white/70 truncate">{entry.description}</span>
                </>
              )}
              {entry.category && (
                <>
                  <span>Category</span>
                  <span className="text-white/70 capitalize">
                    {entry.category.replace(/_/g, " ")}
                  </span>
                </>
              )}
              {entry.symbol && (
                <>
                  <span>Symbol</span>
                  <span className="text-white/70">{entry.symbol}</span>
                </>
              )}
              {entry.quantity !== undefined && (
                <>
                  <span>Quantity</span>
                  <span className="text-white/70">{entry.quantity}</span>
                </>
              )}
              {entry.price !== undefined && (
                <>
                  <span>Price</span>
                  <span className="text-white/70">${entry.price}</span>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Top-level steps shown always expanded (not individual rows)
const TOP_LEVEL_STEPS = new Set([
  "file_received",
  "parser_detected",
  "parse_complete",
  "account_resolved",
  "summary",
  "error",
  "cc_payment_summary",
  "cc_statement_summary",
]);

export default function AuditTrail({ statementId, onComplete }: Props) {
  const [stmt, setStmt] = useState<Statement | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await getStatement(statementId);
        const data: Statement = res.data;
        setStmt(data);
        if (data.status === "completed" || data.status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          onCompleteRef.current?.(data);
        }
      } catch {
        // ignore transient errors
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [statementId]);

  const isProcessing = !stmt || stmt.status === "pending" || stmt.status === "processing";
  const isFailed = stmt?.status === "failed";
  const isComplete = stmt?.status === "completed";

  const topEntries = (stmt?.audit_log ?? []).filter((e) => TOP_LEVEL_STEPS.has(e.step));
  const rowEntries = (stmt?.audit_log ?? []).filter((e) => !TOP_LEVEL_STEPS.has(e.step));

  return (
    <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-white/5"
        onClick={() => setCollapsed((x) => !x)}
      >
        <div className="flex items-center gap-2">
          {isProcessing && <Loader className="w-4 h-4 animate-spin text-[var(--accent)]" />}
          {isComplete && <CheckCircle className="w-4 h-4 text-[var(--accent-green)]" />}
          {isFailed && <AlertCircle className="w-4 h-4 text-[var(--accent-red)]" />}
          <span className="text-sm font-medium">
            {stmt?.file_name ?? "Processing…"}
          </span>
          {stmt && (
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                isComplete
                  ? "bg-green-500/20 text-green-400"
                  : isFailed
                  ? "bg-red-500/20 text-red-400"
                  : "bg-yellow-500/20 text-yellow-400"
              }`}
            >
              {stmt.status}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
          {stmt && isComplete && (
            <span>{stmt.records_processed} record(s)</span>
          )}
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </div>
      </div>

      {!collapsed && (
        <div className="px-4 pb-4 space-y-4 border-t border-[var(--card-border)]">
          {/* Always-visible summary steps */}
          {topEntries.length > 0 && (
            <div className="pt-3 space-y-2">
              {topEntries.map((e, i) => (
                <RowEntry key={i} entry={e} />
              ))}
            </div>
          )}

          {/* Expandable per-row section */}
          {rowEntries.length > 0 && (
            <details className="group">
              <summary className="list-none flex items-center gap-2 cursor-pointer text-xs text-[var(--muted)] hover:text-white select-none">
                <ChevronRight className="w-3 h-3 group-open:rotate-90 transition-transform" />
                Show {rowEntries.length} transaction row(s)
              </summary>
              <div className="mt-2 space-y-1 max-h-96 overflow-y-auto pr-1">
                {rowEntries.map((e, i) => (
                  <RowEntry key={i} entry={e} />
                ))}
              </div>
            </details>
          )}

          {isProcessing && (
            <p className="text-xs text-[var(--muted)] text-center pt-2">
              Processing in background — refreshing every 2s…
            </p>
          )}

          {isFailed && stmt?.error_message && (
            <div className="text-xs bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-[var(--accent-red)]">
              {stmt.error_message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
