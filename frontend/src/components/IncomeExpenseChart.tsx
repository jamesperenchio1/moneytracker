"use client";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { MonthlyTrend } from "@/lib/types";
import { formatCurrency } from "@/lib/format";

interface Props {
  data: MonthlyTrend[];
  currency?: string;
}

export default function IncomeExpenseChart({
  data,
  currency = "THB",
}: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-[var(--muted)]">
        No trend data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="month" stroke="#737373" fontSize={12} />
        <YAxis stroke="#737373" fontSize={12} />
        <Tooltip
          contentStyle={{
            background: "#1a1a1a",
            border: "1px solid #333",
            borderRadius: "8px",
            color: "#ededed",
          }}
          formatter={(value: number) => formatCurrency(value, currency)}
        />
        <Legend />
        <Bar
          dataKey="income"
          fill="#22c55e"
          name="Income"
          radius={[4, 4, 0, 0]}
          opacity={0.85}
        />
        <Bar
          dataKey="expenses"
          fill="#ef4444"
          name="Expenses"
          radius={[4, 4, 0, 0]}
          opacity={0.85}
        />
        <Line
          type="monotone"
          dataKey="net"
          stroke="#3b82f6"
          strokeWidth={2}
          name="Net"
          dot={{ r: 4, fill: "#3b82f6" }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
