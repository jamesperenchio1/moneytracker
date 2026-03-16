"use client";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import type { SpendingBreakdown } from "@/lib/types";
import { formatCurrency } from "@/lib/format";

const COLORS = [
  "#3b82f6",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#f97316",
  "#14b8a6",
  "#6366f1",
  "#84cc16",
  "#e11d48",
];

interface Props {
  data: SpendingBreakdown[];
  currency?: string;
  onCategoryClick?: (categoryName: string) => void;
  selectedCategory?: string | null;
}

export default function SpendingChart({
  data,
  currency = "THB",
  onCategoryClick,
  selectedCategory,
}: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-[var(--muted)]">
        No spending data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          dataKey="total"
          nameKey="category"
          cx="50%"
          cy="50%"
          outerRadius={100}
          innerRadius={60}
          paddingAngle={2}
          style={{ cursor: onCategoryClick ? "pointer" : "default" }}
          onClick={(entry) => {
            if (onCategoryClick && entry?.category) {
              onCategoryClick(entry.category);
            }
          }}
        >
          {data.map((entry, index) => (
            <Cell
              key={index}
              fill={COLORS[index % COLORS.length]}
              opacity={
                selectedCategory
                  ? entry.category === selectedCategory
                    ? 1
                    : 0.25
                  : 0.85
              }
              stroke={
                entry.category === selectedCategory ? "#fff" : "#0a0a0a"
              }
              strokeWidth={entry.category === selectedCategory ? 2 : 1}
            />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: "#1a1a1a",
            border: "1px solid #333",
            borderRadius: "8px",
            color: "#ededed",
          }}
          formatter={(value: number) => formatCurrency(value, currency)}
        />
        <Legend
          onClick={(entry) => {
            if (onCategoryClick && entry?.value) {
              onCategoryClick(entry.value as string);
            }
          }}
          wrapperStyle={{ cursor: onCategoryClick ? "pointer" : "default" }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
