"use client";

import { Treemap, ResponsiveContainer } from "recharts";

export interface HeatmapPosition {
  name: string;
  size: number;
  pnlPercent: number;
  [key: string]: string | number;
}

interface PortfolioHeatmapProps {
  positions: HeatmapPosition[];
}

interface CustomizedContentProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  pnlPercent?: number;
}

function CustomizedContent({
  x = 0,
  y = 0,
  width = 0,
  height = 0,
  name = "",
  pnlPercent = 0,
}: CustomizedContentProps) {
  const intensity = Math.min(Math.abs(pnlPercent) / 10, 1);
  const fill =
    pnlPercent >= 0
      ? `rgba(63, 185, 80, ${0.3 + intensity * 0.7})`
      : `rgba(248, 81, 73, ${0.3 + intensity * 0.7})`;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={fill}
        stroke="#30363d"
        strokeWidth={2}
      />
      {width > 40 && height > 20 && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 6}
            textAnchor="middle"
            dominantBaseline="central"
            fill="#e6edf3"
            fontSize={12}
            fontFamily="monospace"
          >
            {name}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 10}
            textAnchor="middle"
            dominantBaseline="central"
            fill="#e6edf3"
            fontSize={10}
            fontFamily="monospace"
          >
            {pnlPercent >= 0 ? "+" : ""}
            {pnlPercent.toFixed(1)}%
          </text>
        </>
      )}
    </g>
  );
}

export default function PortfolioHeatmap({ positions }: PortfolioHeatmapProps) {
  if (positions.length === 0) {
    return (
      <div className="rounded border border-border-default bg-surface-secondary p-4">
        <div className="flex h-[200px] items-center justify-center">
          <span className="text-sm text-text-muted">
            No positions to display
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded border border-border-default bg-surface-secondary p-4">
      <ResponsiveContainer width="100%" height={200}>
        <Treemap
          data={positions}
          dataKey="size"
          content={<CustomizedContent />}
          isAnimationActive={false}
        />
      </ResponsiveContainer>
    </div>
  );
}
