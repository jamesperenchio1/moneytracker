"use client";

export type Period = "1D" | "1W" | "1M" | "3M" | "6M" | "1Y";

const PERIODS: Period[] = ["1D", "1W", "1M", "3M", "6M", "1Y"];

interface Props {
  value: Period;
  onChange: (period: Period) => void;
  className?: string;
}

export default function TimePeriodSelector({ value, onChange, className = "" }: Props) {
  return (
    <div className={`flex gap-0.5 bg-white/5 rounded-lg p-0.5 ${className}`}>
      {PERIODS.map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
            value === p
              ? "bg-[var(--accent)] text-white shadow-sm"
              : "text-[var(--muted)] hover:text-white"
          }`}
        >
          {p}
        </button>
      ))}
    </div>
  );
}
