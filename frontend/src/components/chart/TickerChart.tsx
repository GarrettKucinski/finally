"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  LineSeries,
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type SeriesType,
} from "lightweight-charts";

interface TickerChartProps {
  ticker: string;
  data: { time: number; value: number }[];
}

export default function TickerChart({ ticker, data }: TickerChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<SeriesType> | null>(null);

  // Create chart when ticker changes (full re-create)
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#161b22" },
        textColor: "#8b949e",
      },
      grid: {
        vertLines: { color: "#21262d" },
        horzLines: { color: "#21262d" },
      },
      crosshair: {
        vertLine: { color: "#30363d", labelBackgroundColor: "#161b22" },
        horzLine: { color: "#30363d", labelBackgroundColor: "#161b22" },
      },
      timeScale: {
        borderColor: "#30363d",
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: "#30363d",
      },
      height: 300,
    });

    const series = chart.addSeries(LineSeries, {
      color: "#209dd7",
      lineWidth: 2,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);
    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [ticker]);

  // Update data when it changes
  useEffect(() => {
    if (!seriesRef.current || !chartRef.current) return;
    if (data.length === 0) return;

    seriesRef.current.setData(
      data.map((d) => ({ time: d.time as import("lightweight-charts").Time, value: d.value }))
    );
    chartRef.current.timeScale().fitContent();
  }, [data]);

  if (data.length === 0) {
    return (
      <div className="rounded border border-border-default bg-surface-secondary p-4">
        <h3 className="mb-2 font-mono text-sm text-text-secondary">{ticker}</h3>
        <div className="flex h-[300px] items-center justify-center">
          <span className="text-sm text-text-muted">
            Waiting for price data...
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded border border-border-default bg-surface-secondary p-4">
      <h3 className="mb-2 font-mono text-sm text-text-secondary">{ticker}</h3>
      <div ref={containerRef} />
    </div>
  );
}
