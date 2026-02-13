"use client";

import { PerformancePoint } from "@/lib/types";
import { AreaData, ColorType, IChartApi, ISeriesApi, Time, createChart } from "lightweight-charts";
import { useEffect, useMemo, useRef } from "react";

function toSeriesData(items: PerformancePoint[]): AreaData<Time>[] {
  return items.map((item) => ({
    time: Math.floor(new Date(item.date).getTime() / 1000) as Time,
    value: item.equity
  }));
}

export function EquityChart({ points }: { points: PerformancePoint[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const data = useMemo(() => toSeriesData(points), [points]);

  useEffect(() => {
    if (!containerRef.current || chartRef.current) {
      return;
    }

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#0f1723" },
        textColor: "#c0ccdf"
      },
      grid: {
        vertLines: { color: "rgba(160, 174, 192, 0.11)" },
        horzLines: { color: "rgba(160, 174, 192, 0.11)" }
      },
      rightPriceScale: { borderColor: "#1f2a3a" },
      timeScale: { borderColor: "#1f2a3a", timeVisible: true, secondsVisible: false }
    });

    chartRef.current = chart;
    const series = chart.addAreaSeries({
      lineColor: "#0ea5e9",
      topColor: "rgba(14, 165, 233, 0.32)",
      bottomColor: "rgba(14, 165, 233, 0.02)",
      lineWidth: 2
    });
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current) {
      return;
    }
    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} className="h-[360px] w-full rounded-2xl border border-border bg-panel/70" />;
}

