"use client";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { NetWorthSnapshot } from "@/lib/types";
import { formatCurrency } from "@/lib/format";

interface Props {
  data: NetWorthSnapshot[];
}

export default function NetWorthChart({ data }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-[var(--muted)]">
        No net worth history yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={350}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="gradNetWorth" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradInvestments" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradCash" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="date" stroke="#737373" fontSize={12} />
        <YAxis stroke="#737373" fontSize={12} />
        <Tooltip
          contentStyle={{
            background: "#1a1a1a",
            border: "1px solid #333",
            borderRadius: "8px",
            color: "#ededed",
          }}
          formatter={(value: number, name: string) => [
            formatCurrency(value, name === "total_cash" ? "THB" : "USD"),
            name === "net_worth"
              ? "Net Worth"
              : name === "total_investments"
                ? "Investments"
                : "Cash",
          ]}
        />
        <Legend
          formatter={(value: string) =>
            value === "net_worth"
              ? "Net Worth"
              : value === "total_investments"
                ? "Investments"
                : "Cash"
          }
        />
        <Area
          type="monotone"
          dataKey="net_worth"
          stroke="#3b82f6"
          fill="url(#gradNetWorth)"
          strokeWidth={2}
        />
        <Area
          type="monotone"
          dataKey="total_investments"
          stroke="#8b5cf6"
          fill="url(#gradInvestments)"
          strokeWidth={2}
        />
        <Area
          type="monotone"
          dataKey="total_cash"
          stroke="#06b6d4"
          fill="url(#gradCash)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
