"use client";

import { DecisionItem, Kline } from "@/lib/types";
import {
  CandlestickData,
  ColorType,
  createChart,
  IChartApi,
  ISeriesApi,
  LineData,
  SeriesMarker,
  Time
} from "lightweight-charts";
import { useEffect, useMemo, useRef } from "react";

function isoToTime(value: string): Time {
  return Math.floor(new Date(value).getTime() / 1000) as Time;
}

function calculateMovingAverage(source: Kline[], period: number): LineData<Time>[] {
  const output: LineData<Time>[] = [];
  for (let index = period - 1; index < source.length; index += 1) {
    let sum = 0;
    for (let pointer = index - period + 1; pointer <= index; pointer += 1) {
      sum += source[pointer].close;
    }
    output.push({
      time: isoToTime(source[index].open_time),
      value: Number((sum / period).toFixed(2))
    });
  }
  return output;
}

export function PriceChart({ klines, decisions }: { klines: Kline[]; decisions: DecisionItem[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const ma20Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma50Ref = useRef<ISeriesApi<"Line"> | null>(null);

  const candleData = useMemo<CandlestickData<Time>[]>(
    () =>
      klines.map((row) => ({
        time: isoToTime(row.open_time),
        open: row.open,
        high: row.high,
        low: row.low,
        close: row.close
      })),
    [klines]
  );

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
      timeScale: { borderColor: "#1f2a3a", timeVisible: true, secondsVisible: false },
      crosshair: { mode: 1 }
    });
    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#17b26a",
      downColor: "#f04438",
      borderUpColor: "#17b26a",
      borderDownColor: "#f04438",
      wickUpColor: "#17b26a",
      wickDownColor: "#f04438"
    });
    candleRef.current = candleSeries;

    ma20Ref.current = chart.addLineSeries({ color: "#0ea5e9", lineWidth: 2, priceLineVisible: false });
    ma50Ref.current = chart.addLineSeries({ color: "#fbbf24", lineWidth: 2, priceLineVisible: false });

    return () => {
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      ma20Ref.current = null;
      ma50Ref.current = null;
    };
  }, []);

  useEffect(() => {
    if (!candleRef.current || !ma20Ref.current || !ma50Ref.current) {
      return;
    }
    candleRef.current.setData(candleData);
    ma20Ref.current.setData(calculateMovingAverage(klines, 20));
    ma50Ref.current.setData(calculateMovingAverage(klines, 50));

    const markers: SeriesMarker<Time>[] = decisions
      .filter((item) => item.decision !== "hold" && item.entry_price > 0)
      .map((item) => ({
        time: isoToTime(item.timestamp),
        position: item.decision === "sell" ? "aboveBar" : "belowBar",
        color: item.decision === "sell" ? "#f04438" : "#17b26a",
        shape: item.decision === "sell" ? "arrowDown" : "arrowUp",
        text: `${item.decision.toUpperCase()} ${item.position_size_pct.toFixed(1)}%`
      }));
    candleRef.current.setMarkers(markers);

    chartRef.current?.timeScale().fitContent();
  }, [candleData, decisions, klines]);

  return <div ref={containerRef} className="h-[420px] w-full rounded-2xl border border-border bg-panel/70" />;
}

