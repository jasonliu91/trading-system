"use client";

import { PriceChart } from "@/components/dashboard/price-chart";
import { SummaryCards } from "@/components/dashboard/summary-cards";
import { TimeframeSwitcher } from "@/components/dashboard/timeframe-switcher";
import { useDashboardData } from "@/hooks/use-dashboard-data";
import { useLiveFeed } from "@/hooks/use-live-feed";
import { useDashboardStore } from "@/stores/dashboard-store";

export default function HomePage() {
  const { timeframe, setTimeframe, autoRefresh, toggleAutoRefresh } = useDashboardStore();
  const { klines, decisions, portfolio, loading, error, lastUpdated, refresh } = useDashboardData(timeframe, autoRefresh);
  const live = useLiveFeed(true);
  const latestDecision = decisions[0] ?? null;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 md:px-8 md:py-8">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted">ETH AI Trading System</p>
          <h1 className="mt-1 text-2xl font-semibold text-text md:text-4xl">Dashboard</h1>
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
        <section className="flex items-center justify-between rounded-2xl border border-bear/50 bg-bear/10 p-4 text-sm text-red-100">
          <span>API error: {error}. Confirm backend service is reachable.</span>
          <button
            type="button"
            onClick={() => void refresh()}
            className="ml-3 shrink-0 rounded-lg border border-bear/40 px-3 py-1 text-xs uppercase tracking-[0.12em] hover:bg-bear/20"
          >
            Retry
          </button>
        </section>
      )}

      <section className="rounded-2xl border border-border bg-panel/75 p-4 shadow-panel">
        {loading && klines.length === 0 ? (
          <div className="flex h-[420px] animate-pulse items-center justify-center rounded-xl bg-border/10 md:h-[480px]">
            <p className="text-sm text-muted">Loading chart data...</p>
          </div>
        ) : (
          <PriceChart klines={klines} decisions={decisions} />
        )}
      </section>

      <SummaryCards
        portfolio={portfolio}
        latestDecision={latestDecision}
        lastUpdated={lastUpdated}
        loading={loading}
        livePrice={live.latest?.price ?? null}
        liveStatus={live.status}
      />
    </main>
  );
}
