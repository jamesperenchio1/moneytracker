"use client";
import { useState, useRef, useCallback } from "react";
import { Brain, RefreshCw, Loader2, ChevronDown } from "lucide-react";
import { streamAiInsights } from "@/lib/api";

// Simple markdown renderer for the AI output
function renderMarkdown(text: string): JSX.Element[] {
  const lines = text.split("\n");
  const elements: JSX.Element[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // H2 headers (##)
    if (line.startsWith("## ")) {
      elements.push(
        <h2 key={i} className="text-base font-bold text-white mt-5 mb-2 flex items-center gap-2">
          <span className="w-1.5 h-4 bg-[var(--accent)] rounded-full inline-block" />
          {line.slice(3)}
        </h2>
      );
    }
    // H3 headers (###)
    else if (line.startsWith("### ")) {
      elements.push(
        <h3 key={i} className="text-sm font-semibold text-[var(--foreground)] mt-3 mb-1">
          {line.slice(4)}
        </h3>
      );
    }
    // H1 headers (#)
    else if (line.startsWith("# ")) {
      elements.push(
        <h1 key={i} className="text-lg font-bold text-white mt-4 mb-2">
          {line.slice(2)}
        </h1>
      );
    }
    // Bold bullet points (** at start of bullet)
    else if (line.startsWith("- **") || line.startsWith("* **")) {
      const content = line.slice(2);
      elements.push(
        <div key={i} className="flex items-start gap-2 my-1">
          <span className="w-1 h-1 rounded-full bg-[var(--accent)] mt-2 shrink-0" />
          <p className="text-sm text-[var(--foreground)]" dangerouslySetInnerHTML={{ __html: formatInline(content) }} />
        </div>
      );
    }
    // Regular bullet points
    else if (line.startsWith("- ") || line.startsWith("* ")) {
      elements.push(
        <div key={i} className="flex items-start gap-2 my-0.5">
          <span className="w-1 h-1 rounded-full bg-[var(--muted)] mt-2 shrink-0" />
          <p className="text-sm text-[var(--foreground)]" dangerouslySetInnerHTML={{ __html: formatInline(line.slice(2)) }} />
        </div>
      );
    }
    // Numbered list
    else if (/^\d+\.\s/.test(line)) {
      const match = line.match(/^(\d+)\.\s(.*)$/);
      if (match) {
        elements.push(
          <div key={i} className="flex items-start gap-2 my-1">
            <span className="w-5 h-5 rounded-full bg-[var(--accent)]/20 text-[var(--accent)] text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
              {match[1]}
            </span>
            <p className="text-sm text-[var(--foreground)]" dangerouslySetInnerHTML={{ __html: formatInline(match[2]) }} />
          </div>
        );
      }
    }
    // Horizontal rule
    else if (line === "---" || line === "***") {
      elements.push(<hr key={i} className="border-[var(--card-border)] my-3" />);
    }
    // Empty line
    else if (line.trim() === "") {
      elements.push(<div key={i} className="h-1" />);
    }
    // Regular paragraph
    else if (line.trim()) {
      elements.push(
        <p key={i} className="text-sm text-[var(--foreground)] my-1" dangerouslySetInnerHTML={{ __html: formatInline(line) }} />
      );
    }

    i++;
  }

  return elements;
}

function formatInline(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
    .replace(/\*(.+?)\*/g, '<em class="text-[var(--foreground)]">$1</em>')
    .replace(/`(.+?)`/g, '<code class="px-1 py-0.5 rounded bg-white/10 text-[var(--accent)] text-xs font-mono">$1</code>');
}

const PERIOD_OPTIONS = [
  { value: 1, label: "1 Month" },
  { value: 3, label: "3 Months" },
  { value: 6, label: "6 Months" },
];

export default function AiInsights() {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [months, setMonths] = useState(3);
  const abortRef = useRef<AbortController | null>(null);

  const startAnalysis = useCallback(async () => {
    // Cancel any in-progress stream
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setContent("");
    setError(null);
    setDone(false);
    setLoading(true);

    await streamAiInsights(
      months,
      (chunk) => setContent((prev) => prev + chunk),
      () => { setLoading(false); setDone(true); },
      (err) => { setError(err); setLoading(false); },
      abortRef.current.signal,
    );
  }, [months]);

  return (
    <div className="space-y-4">
      {/* Header controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-[var(--accent-purple)]" />
          <div>
            <h3 className="font-semibold text-sm">AI Financial Analysis</h3>
            <p className="text-xs text-[var(--muted)]">Powered by Claude · Analyzes your spending patterns</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Period selector */}
          <div className="relative">
            <select
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
              className="appearance-none pl-3 pr-8 py-1.5 rounded-lg bg-white/5 border border-[var(--card-border)] text-xs text-[var(--foreground)] focus:outline-none focus:border-[var(--accent)] cursor-pointer"
            >
              {PERIOD_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <ChevronDown className="w-3 h-3 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-[var(--muted)]" />
          </div>
          <button
            onClick={startAnalysis}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-[var(--accent-purple)]/15 text-[var(--accent-purple)] border border-[var(--accent-purple)]/30 text-xs font-medium hover:bg-[var(--accent-purple)]/25 transition-colors disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5" />
            )}
            {loading ? "Analyzing..." : done ? "Re-analyze" : "Analyze Now"}
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
          <strong>Error:</strong> {error}
          {error.includes("ANTHROPIC_API_KEY") && (
            <p className="mt-1 text-xs">Set the <code className="bg-red-500/20 px-1 rounded">ANTHROPIC_API_KEY</code> environment variable on the backend server.</p>
          )}
        </div>
      )}

      {/* Empty state */}
      {!content && !loading && !error && (
        <div className="rounded-xl border border-dashed border-[var(--card-border)] p-12 text-center">
          <Brain className="w-12 h-12 text-[var(--accent-purple)]/40 mx-auto mb-3" />
          <p className="text-sm font-medium text-[var(--muted)]">Get AI-powered insights</p>
          <p className="text-xs text-[var(--muted)] mt-1 max-w-xs mx-auto">
            Claude will analyze your spending patterns, find subscriptions, identify savings opportunities, and suggest improvements.
          </p>
          <button
            onClick={startAnalysis}
            className="mt-4 px-5 py-2 rounded-lg bg-[var(--accent-purple)]/15 text-[var(--accent-purple)] border border-[var(--accent-purple)]/30 text-sm font-medium hover:bg-[var(--accent-purple)]/25 transition-colors"
          >
            Start Analysis
          </button>
        </div>
      )}

      {/* Streaming content */}
      {(content || loading) && (
        <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-5">
          {loading && !content && (
            <div className="flex items-center gap-2 text-[var(--muted)] text-sm py-4">
              <Loader2 className="w-4 h-4 animate-spin" />
              Claude is analyzing your finances...
            </div>
          )}
          <div className="prose-sm max-w-none">
            {renderMarkdown(content)}
            {loading && (
              <span className="inline-block w-2 h-4 bg-[var(--accent-purple)] animate-pulse rounded-sm ml-0.5 align-middle" />
            )}
          </div>
          {done && (
            <div className="mt-4 pt-3 border-t border-[var(--card-border)] flex items-center justify-between text-xs text-[var(--muted)]">
              <span className="flex items-center gap-1.5">
                <Brain className="w-3.5 h-3.5 text-[var(--accent-purple)]" />
                Analysis complete · Based on last {months} month{months > 1 ? "s" : ""} of data
              </span>
              <button
                onClick={startAnalysis}
                className="text-[var(--accent)] hover:text-white transition-colors"
              >
                Refresh
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
