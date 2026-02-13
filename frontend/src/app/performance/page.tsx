"use client";

import { EquityChart } from "@/components/performance/equity-chart";
import { fetchPerformance } from "@/lib/api";
import { PerformanceResponse } from "@/lib/types";
import { useEffect, useState } from "react";

export default function PerformancePage() {
  const [data, setData] = useState<PerformanceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const payload = await fetchPerformance();
        setData(payload);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load performance data");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const metrics = data?.metrics;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 md:px-8 md:py-8">
      <header>
        <p className="text-xs uppercase tracking-[0.24em] text-muted">Capital View</p>
        <h1 className="mt-1 text-2xl font-semibold text-text md:text-4xl">Performance</h1>
      </header>

      {error && <section className="rounded-xl border border-bear/40 bg-bear/10 p-3 text-sm text-red-100">{error}</section>}

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <article className="rounded-2xl border border-border bg-panel/70 p-4">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Total Return</p>
          <p className="mt-2 text-2xl font-semibold text-text">
            {metrics ? `${metrics.total_return_pct.toFixed(2)}%` : "--"}
          </p>
        </article>
        <article className="rounded-2xl border border-border bg-panel/70 p-4">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Max Drawdown</p>
          <p className="mt-2 text-2xl font-semibold text-text">
            {metrics ? `${metrics.max_drawdown_pct.toFixed(2)}%` : "--"}
          </p>
        </article>
        <article className="rounded-2xl border border-border bg-panel/70 p-4">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Win Rate</p>
          <p className="mt-2 text-2xl font-semibold text-text">{metrics ? `${(metrics.win_rate * 100).toFixed(1)}%` : "--"}</p>
        </article>
        <article className="rounded-2xl border border-border bg-panel/70 p-4">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Profit Factor</p>
          <p className="mt-2 text-2xl font-semibold text-text">{metrics ? metrics.profit_factor.toFixed(2) : "--"}</p>
        </article>
      </section>

      <section className="rounded-2xl border border-border bg-panel/70 p-4 shadow-panel">
        <h2 className="mb-3 text-sm uppercase tracking-[0.14em] text-muted">Equity Curve</h2>
        {!loading && data && <EquityChart points={data.equity_curve} />}
        {loading && <p className="text-sm text-muted">Loading performance data...</p>}
      </section>

      <section className="rounded-2xl border border-border bg-panel/70 p-4">
        <h2 className="text-sm uppercase tracking-[0.14em] text-muted">Equity Data</h2>
        <div className="mt-3 space-y-2">
          {(data?.equity_curve || []).map((point) => (
            <div key={point.date} className="flex items-center justify-between rounded-lg border border-border/70 bg-bg/35 px-3 py-2">
              <p className="text-sm text-muted">{point.date}</p>
              <p className="text-sm font-medium text-text">{point.equity.toFixed(2)}</p>
            </div>
          ))}
          {!loading && !(data?.equity_curve || []).length && <p className="text-sm text-muted">No performance points yet.</p>}
        </div>
      </section>
    </main>
  );
}

