"use client";

import { PriceChart } from "@/components/dashboard/price-chart";
import { StrategyLab } from "@/components/dashboard/strategy-lab";
import { SummaryCards } from "@/components/dashboard/summary-cards";
import { TimeframeSwitcher } from "@/components/dashboard/timeframe-switcher";
import { useDashboardData } from "@/hooks/use-dashboard-data";
import { useLiveFeed } from "@/hooks/use-live-feed";
import { useDashboardStore } from "@/stores/dashboard-store";
import { useEffect, useMemo, useState } from "react";

export default function HomePage() {
  const { timeframe, setTimeframe, autoRefresh, toggleAutoRefresh } = useDashboardStore();
  const { klines, decisions, signals, portfolio, loading, error, lastUpdated, refresh } = useDashboardData(timeframe, autoRefresh);
  const live = useLiveFeed(true);
  const latestDecision = decisions[0] ?? null;

  const [showQuantSignals, setShowQuantSignals] = useState(true);
  const [showAIDecisions, setShowAIDecisions] = useState(true);
  const [minDecisionConfidence, setMinDecisionConfidence] = useState(0.45);
  const [activeStrategies, setActiveStrategies] = useState<string[]>([]);

  const strategies = useMemo(() => signals?.strategies ?? [], [signals]);
  const quantSignals = useMemo(() => signals?.items ?? [], [signals]);
  const quantSummary = useMemo(() => signals?.summary ?? null, [signals]);
  const quantMarkers = useMemo(() => signals?.markers ?? [], [signals]);

  useEffect(() => {
    if (!strategies.length) {
      setActiveStrategies([]);
      return;
    }
    setActiveStrategies((current) => {
      if (!current.length) {
        return strategies.map((item) => item.strategy_name);
      }
      const existing = new Set(strategies.map((item) => item.strategy_name));
      const next = current.filter((name) => existing.has(name));
      return next.length ? next : strategies.map((item) => item.strategy_name);
    });
  }, [strategies]);

  const toggleStrategy = (strategyName: string) => {
    setActiveStrategies((current) => {
      if (current.includes(strategyName)) {
        return current.filter((item) => item !== strategyName);
      }
      return [...current, strategyName];
    });
  };

  const quantSource = useMemo(() => signals?.source || "unknown", [signals]);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 md:px-8 md:py-8">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted">ETH AI Trading System</p>
          <h1 className="mt-1 text-2xl font-semibold text-text md:text-4xl">Dashboard</h1>
          <p className="mt-1 text-xs text-muted">Quant source: {quantSource}</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <TimeframeSwitcher value={timeframe} onChange={setTimeframe} />
          <button
            type="button"
            onClick={toggleAutoRefresh}
            className={`rounded-xl border px-3 py-2 text-xs uppercase tracking-[0.14em] ${
              autoRefresh ? "border-accent text-accent" : "border-border text-muted"
            }`}
          >
            Auto Refresh: {autoRefresh ? "On" : "Off"}
          </button>
          <button
            type="button"
            onClick={() => void refresh()}
            className="rounded-xl border border-border px-3 py-2 text-xs uppercase tracking-[0.14em] text-text hover:border-accent/60"
          >
            Refresh Now
          </button>
        </div>
      </header>

      {error && (
        <section className="rounded-2xl border border-bear/50 bg-bear/10 p-4 text-sm text-red-100">
          API error: {error}. Confirm backend service is reachable at `NEXT_PUBLIC_API_BASE_URL`.
        </section>
      )}

      <section className="rounded-2xl border border-border bg-panel/75 p-4 shadow-panel">
        <PriceChart
          klines={klines}
          decisions={decisions}
          quantMarkers={quantMarkers}
          showAIDecisions={showAIDecisions}
          showQuantSignals={showQuantSignals}
          minDecisionConfidence={minDecisionConfidence}
          activeStrategies={activeStrategies}
        />
      </section>

      <SummaryCards
        portfolio={portfolio}
        latestDecision={latestDecision}
        lastUpdated={lastUpdated}
        loading={loading}
        livePrice={live.latest?.price ?? null}
        liveStatus={live.status}
      />

      <StrategyLab
        strategies={strategies}
        signals={quantSignals}
        summary={quantSummary}
        activeStrategies={activeStrategies}
        showQuantSignals={showQuantSignals}
        showAIDecisions={showAIDecisions}
        minDecisionConfidence={minDecisionConfidence}
        onToggleStrategy={toggleStrategy}
        onToggleQuantSignals={() => setShowQuantSignals((value) => !value)}
        onToggleAIDecisions={() => setShowAIDecisions((value) => !value)}
        onDecisionConfidenceChange={setMinDecisionConfidence}
      />
    </main>
  );
}
