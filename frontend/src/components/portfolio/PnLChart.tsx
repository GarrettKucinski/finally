"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { SnapshotPoint } from "@/types/api";

interface PnLChartProps {
  data: SnapshotPoint[];
}

export default function PnLChart({ data }: PnLChartProps) {
  if (data.length === 0) {
    return (
      <div className="rounded border border-border-default bg-surface-secondary p-4">
        <div className="flex h-[200px] items-center justify-center">
          <span className="text-sm text-text-muted">
            No portfolio history yet
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded border border-border-default bg-surface-secondary p-4">
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart
          data={data}
          margin={{ top: 5, right: 5, left: 5, bottom: 5 }}
        >
          <defs>
            <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#209dd7" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#209dd7" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="recorded_at"
            tick={{ fill: "#6e7681", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "#30363d" }}
            tickFormatter={(v: string) =>
              new Date(v).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })
            }
          />
          <YAxis
            tick={{ fill: "#6e7681", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "#30363d" }}
            tickFormatter={(v: number) => "$" + v.toLocaleString()}
            domain={["dataMin - 100", "dataMax + 100"]}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#161b22",
              border: "1px solid #30363d",
              color: "#e6edf3",
            }}
            labelFormatter={(v) => new Date(String(v)).toLocaleString()}
            formatter={(v) => ["$" + Number(v).toFixed(2), "Portfolio Value"]}
          />
          <Area
            type="monotone"
            dataKey="total_value"
            stroke="#209dd7"
            fill="url(#pnlGradient)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
