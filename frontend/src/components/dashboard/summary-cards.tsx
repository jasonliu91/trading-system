"use client";

import { DecisionItem, PortfolioSnapshot } from "@/lib/types";

export function SummaryCards({
  portfolio,
  latestDecision,
  lastUpdated,
  loading
}: {
  portfolio: PortfolioSnapshot | null;
  latestDecision: DecisionItem | null;
  lastUpdated: string | null;
  loading: boolean;
}) {
  const priceText = portfolio ? portfolio.mark_price.toFixed(2) : "--";
  const equityText = portfolio ? portfolio.equity.toFixed(2) : "--";
  const exposureText = portfolio ? `${portfolio.exposure_pct.toFixed(2)}%` : "--";
  const decisionText = latestDecision ? latestDecision.decision.toUpperCase() : "--";
  const confidenceText = latestDecision ? `${(latestDecision.confidence * 100).toFixed(1)}%` : "--";

  return (
    <section className="grid grid-cols-1 gap-4 lg:grid-cols-4">
      <article className="rounded-2xl border border-border bg-panel/70 p-4 shadow-panel">
        <p className="text-xs uppercase tracking-[0.16em] text-muted">Mark Price</p>
        <p className="mt-2 text-2xl font-semibold text-text">{priceText}</p>
      </article>

      <article className="rounded-2xl border border-border bg-panel/70 p-4 shadow-panel">
        <p className="text-xs uppercase tracking-[0.16em] text-muted">Equity</p>
        <p className="mt-2 text-2xl font-semibold text-text">{equityText}</p>
      </article>

      <article className="rounded-2xl border border-border bg-panel/70 p-4 shadow-panel">
        <p className="text-xs uppercase tracking-[0.16em] text-muted">Exposure</p>
        <p className="mt-2 text-2xl font-semibold text-text">{exposureText}</p>
      </article>

      <article className="rounded-2xl border border-border bg-panel/70 p-4 shadow-panel">
        <p className="text-xs uppercase tracking-[0.16em] text-muted">Latest Decision</p>
        <p className="mt-2 text-2xl font-semibold text-accent">{decisionText}</p>
        <p className="text-sm text-muted">Confidence: {confidenceText}</p>
      </article>

      <article className="rounded-2xl border border-border bg-panel/65 p-4 lg:col-span-2">
        <p className="text-xs uppercase tracking-[0.16em] text-muted">Mind Alignment</p>
        <p className="mt-2 text-sm leading-6 text-text">
          {latestDecision?.reasoning?.mind_alignment ?? "No decision yet"}
        </p>
      </article>

      <article className="rounded-2xl border border-border bg-panel/65 p-4 lg:col-span-2">
        <p className="text-xs uppercase tracking-[0.16em] text-muted">Bias Check</p>
        <p className="mt-2 text-sm leading-6 text-text">{latestDecision?.reasoning?.bias_check ?? "No decision yet"}</p>
      </article>

      <article className="rounded-2xl border border-border bg-panel/65 p-4 lg:col-span-4">
        <p className="text-xs uppercase tracking-[0.16em] text-muted">Refresh Status</p>
        <p className="mt-2 text-sm text-muted">
          {loading ? "Loading..." : `Updated at ${lastUpdated ?? "unknown"}`}
        </p>
      </article>
    </section>
  );
}

