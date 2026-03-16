"use client";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { formatCurrency } from "@/lib/format";

interface DataPoint {
  date: string;
  value: number;
}

interface Props {
  data: DataPoint[];
  currency?: string;
}

export default function PortfolioChart({ data, currency = "USD" }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-[var(--muted)]">
        No portfolio history yet. Upload statements to see historical performance.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
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
          formatter={(value: number) => formatCurrency(value, currency)}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke="#3b82f6"
          fill="url(#colorValue)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
