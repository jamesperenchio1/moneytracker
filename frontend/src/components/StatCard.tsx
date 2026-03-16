"use client";
import { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon?: ReactNode;
  trend?: number;
  gradient?: string;
  accentColor?: string;
  onClick?: () => void;
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  gradient,
  accentColor,
  onClick,
}: StatCardProps) {
  return (
    <div
      onClick={onClick}
      className={`rounded-xl border border-[var(--card-border)] p-6 transition-transform hover:scale-[1.02] ${onClick ? "cursor-pointer" : ""}`}
      style={{
        background: gradient || "var(--card)",
        borderLeft: accentColor ? `3px solid ${accentColor}` : undefined,
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-[var(--muted)]">{title}</span>
        {icon && (
          <span style={{ color: accentColor || "var(--muted)" }}>{icon}</span>
        )}
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
