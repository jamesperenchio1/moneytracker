"use client";
import { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon?: ReactNode;
  trend?: number;
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon,
  trend,
}: StatCardProps) {
  return (
    <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-[var(--muted)]">{title}</span>
        {icon && <span className="text-[var(--muted)]">{icon}</span>}
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {(subtitle || trend !== undefined) && (
        <div className="mt-1 text-sm">
          {trend !== undefined && (
            <span
              className={
                trend >= 0
                  ? "text-[var(--accent-green)]"
                  : "text-[var(--accent-red)]"
              }
            >
              {trend >= 0 ? "+" : ""}
              {trend.toFixed(2)}%
            </span>
          )}
          {subtitle && (
            <span className="text-[var(--muted)] ml-2">{subtitle}</span>
          )}
        </div>
      )}
    </div>
  );
}
