"use client";
import { Treemap, ResponsiveContainer, Tooltip } from "recharts";
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

interface TreemapContentProps {
  x: number;
  y: number;
  width: number;
  height: number;
  index: number;
  name: string;
  value: number;
  percentage: number;
}

function CustomContent(
  props: TreemapContentProps & {
    onCategoryClick?: (name: string) => void;
    selectedCategory?: string | null;
  }
) {
  const {
    x,
    y,
    width,
    height,
    index,
    name,
    value,
    percentage,
    onCategoryClick,
    selectedCategory,
  } = props;
  if (width < 40 || height < 30) return null;

  const isSelected = selectedCategory === name;
  const isDimmed = selectedCategory && !isSelected;

  return (
    <g
      onClick={() => onCategoryClick?.(name)}
      style={{ cursor: onCategoryClick ? "pointer" : "default" }}
    >
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={6}
        fill={COLORS[index % COLORS.length]}
        opacity={isDimmed ? 0.25 : 0.85}
        stroke={isSelected ? "#fff" : "#0a0a0a"}
        strokeWidth={isSelected ? 3 : 2}
      />
      {width > 60 && height > 40 && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 8}
            textAnchor="middle"
            fill="#fff"
            fontSize={12}
            fontWeight={600}
            opacity={isDimmed ? 0.4 : 1}
          >
            {name}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 10}
            textAnchor="middle"
            fill="rgba(255,255,255,0.7)"
            fontSize={10}
            opacity={isDimmed ? 0.4 : 1}
          >
            {formatCurrency(value, "THB")} ({percentage.toFixed(0)}%)
          </text>
        </>
      )}
    </g>
  );
}

export default function CategoryTreemap({
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

  const treemapData = data.map((d, i) => ({
    name: d.category,
    value: d.total,
    percentage: d.percentage,
    fill: COLORS[i % COLORS.length],
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <Treemap
        data={treemapData}
        dataKey="value"
        nameKey="name"
        content={
          <CustomContent
            x={0}
            y={0}
            width={0}
            height={0}
            index={0}
            name=""
            value={0}
            percentage={0}
            onCategoryClick={onCategoryClick}
            selectedCategory={selectedCategory}
          />
        }
      >
        <Tooltip
          contentStyle={{
            background: "#1a1a1a",
            border: "1px solid #333",
            borderRadius: "8px",
            color: "#ededed",
          }}
          formatter={(value: number) => formatCurrency(value, currency)}
        />
      </Treemap>
    </ResponsiveContainer>
  );
}
