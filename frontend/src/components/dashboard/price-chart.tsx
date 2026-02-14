"use client";

import { DecisionItem, Kline, QuantSignalMarker } from "@/lib/types";
import {
  CandlestickData,
  ColorType,
  createChart,
  HistogramData,
  IChartApi,
  ISeriesApi,
  LineData,
  SeriesMarker,
  Time
} from "lightweight-charts";
import { useEffect, useMemo, useRef } from "react";

function toUnixSecond(value: string): number | null {
  const milliseconds = Date.parse(value);
  if (Number.isNaN(milliseconds)) {
    return null;
  }
  return Math.floor(milliseconds / 1000);
}

function isoToTime(value: string): Time {
  return (toUnixSecond(value) ?? 0) as Time;
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

function strategyColor(strategyName: string, signal: "buy" | "sell"): string {
  const palette: Record<string, string> = {
    ema_adx_daily: signal === "buy" ? "#22c55e" : "#ef4444",
    supertrend_daily: signal === "buy" ? "#06b6d4" : "#f97316",
    donchian_breakout_daily: signal === "buy" ? "#a3e635" : "#fb7185"
  };
  return palette[strategyName] ?? (signal === "buy" ? "#22c55e" : "#ef4444");
}

function compactStrategyName(name: string): string {
  if (!name) {
    return "STRAT";
  }
  return name
    .split(" ")
    .map((item) => item.charAt(0).toUpperCase())
    .join("")
    .slice(0, 5);
}

interface PriceChartProps {
  klines: Kline[];
  decisions: DecisionItem[];
  quantMarkers: QuantSignalMarker[];
  showAIDecisions: boolean;
  showQuantSignals: boolean;
  minDecisionConfidence: number;
  activeStrategies: string[];
}

export function PriceChart({
  klines,
  decisions,
  quantMarkers,
  showAIDecisions,
  showQuantSignals,
  minDecisionConfidence,
  activeStrategies
}: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const ma20Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma50Ref = useRef<ISeriesApi<"Line"> | null>(null);

  const sortedKlines = useMemo(
    () =>
      [...klines].sort((a, b) => {
        const left = toUnixSecond(a.open_time) ?? 0;
        const right = toUnixSecond(b.open_time) ?? 0;
        return left - right;
      }),
    [klines]
  );

  const candleData = useMemo<CandlestickData<Time>[]>(
    () =>
      sortedKlines.map((row) => ({
        time: isoToTime(row.open_time),
        open: row.open,
        high: row.high,
        low: row.low,
        close: row.close
      })),
    [sortedKlines]
  );

  const volumeData = useMemo<HistogramData<Time>[]>(
    () =>
      sortedKlines.map((row) => ({
        time: isoToTime(row.open_time),
        value: row.volume,
        color: row.close >= row.open ? "rgba(23, 178, 106, 0.35)" : "rgba(240, 68, 56, 0.35)"
      })),
    [sortedKlines]
  );

  const aiMarkers = useMemo<SeriesMarker<Time>[]>(() => {
    if (!showAIDecisions) {
      return [];
    }

    return decisions
      .filter(
        (item) =>
          item.decision !== "hold" &&
          item.entry_price > 0 &&
          Number(item.confidence) >= minDecisionConfidence
      )
      .reduce<SeriesMarker<Time>[]>((output, item) => {
        const markerTime = toUnixSecond(item.timestamp);
        if (markerTime === null) {
          return output;
        }
        output.push({
          time: markerTime as Time,
          position: item.decision === "sell" ? "aboveBar" : "belowBar",
          color: item.decision === "sell" ? "#dc2626" : "#16a34a",
          shape: item.decision === "sell" ? "arrowDown" : "arrowUp",
          text: `AI ${item.decision.toUpperCase()} ${(item.confidence * 100).toFixed(0)}%`
        });
        return output;
      }, []);
  }, [decisions, minDecisionConfidence, showAIDecisions]);

  const quantSignalMarkers = useMemo<SeriesMarker<Time>[]>(() => {
    if (!showQuantSignals) {
      return [];
    }

    const selected = new Set(activeStrategies);
    return quantMarkers
      .filter((item) => selected.size === 0 || selected.has(item.strategy_name))
      .reduce<SeriesMarker<Time>[]>((output, item) => {
        const markerTime = toUnixSecond(item.timestamp);
        if (markerTime === null) {
          return output;
        }
        output.push({
          time: markerTime as Time,
          position: item.signal === "sell" ? "aboveBar" : "belowBar",
          color: strategyColor(item.strategy_name, item.signal),
          shape: item.signal === "buy" ? "circle" : "square",
          text: `Q ${compactStrategyName(item.display_name)} ${item.signal.toUpperCase()}`
        });
        return output;
      }, []);
  }, [activeStrategies, quantMarkers, showQuantSignals]);

  const markers = useMemo(
    () =>
      [...quantSignalMarkers, ...aiMarkers].sort((a, b) => {
        if (Number(a.time) === Number(b.time)) {
          return String(a.text ?? "").localeCompare(String(b.text ?? ""));
        }
        return Number(a.time) - Number(b.time);
      }),
    [aiMarkers, quantSignalMarkers]
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

    // Volume histogram on a separate price scale
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume"
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 }
    });
    volumeRef.current = volumeSeries;

    ma20Ref.current = chart.addLineSeries({ color: "#0ea5e9", lineWidth: 2, priceLineVisible: false });
    ma50Ref.current = chart.addLineSeries({ color: "#fbbf24", lineWidth: 2, priceLineVisible: false });

    return () => {
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      volumeRef.current = null;
      ma20Ref.current = null;
      ma50Ref.current = null;
    };
  }, []);

  useEffect(() => {
    if (!candleRef.current || !ma20Ref.current || !ma50Ref.current || !volumeRef.current) {
      return;
    }
    candleRef.current.setData(candleData);
    volumeRef.current.setData(volumeData);
    ma20Ref.current.setData(calculateMovingAverage(sortedKlines, 20));
    ma50Ref.current.setData(calculateMovingAverage(sortedKlines, 50));
    candleRef.current.setMarkers(markers);

    chartRef.current?.timeScale().fitContent();
  }, [candleData, volumeData, markers, sortedKlines]);

  return <div ref={containerRef} className="h-[420px] w-full rounded-2xl border border-border bg-panel/70 md:h-[480px]" />;
}
