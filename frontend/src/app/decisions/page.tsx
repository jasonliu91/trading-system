"use client";

import { fetchDecisions } from "@/lib/api";
import { DecisionItem } from "@/lib/types";
import { useEffect, useMemo, useState } from "react";

function decisionTone(value: DecisionItem["decision"]): string {
  if (value === "buy") {
    return "text-bull";
  }
  if (value === "sell") {
    return "text-bear";
  }
  return "text-muted";
}

export default function DecisionsPage() {
  const [items, setItems] = useState<DecisionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const payload = await fetchDecisions(100);
        setItems(payload);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load decisions");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const filtered = useMemo(() => {
    if (!query.trim()) {
      return items;
    }
    const keyword = query.trim().toLowerCase();
    return items.filter((item) => {
      return (
        item.decision.toLowerCase().includes(keyword) ||
        (item.reasoning.mind_alignment || "").toLowerCase().includes(keyword) ||
        (item.reasoning.bias_check || "").toLowerCase().includes(keyword)
      );
    });
  }, [items, query]);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 md:px-8 md:py-8">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted">Audit Trail</p>
          <h1 className="mt-1 text-2xl font-semibold text-text md:text-4xl">Decision History</h1>
        </div>

        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter by keyword..."
          className="w-full rounded-xl border border-border bg-panel/70 px-3 py-2 text-sm text-text outline-none focus:border-accent md:w-80"
        />
      </header>

      {error && <section className="rounded-xl border border-bear/40 bg-bear/10 p-3 text-sm text-red-100">{error}</section>}

      <section className="rounded-2xl border border-border bg-panel/70 p-4">
        <div className="grid grid-cols-6 gap-2 border-b border-border px-3 py-2 text-xs uppercase tracking-[0.14em] text-muted">
          <p>Time</p>
          <p>Action</p>
          <p>Size</p>
          <p>Entry</p>
          <p>Confidence</p>
          <p>Model</p>
        </div>

        <div className="space-y-2 py-2">
          {filtered.map((item) => (
            <details key={item.id} className="rounded-xl border border-border/70 bg-bg/35 p-3">
              <summary className="grid cursor-pointer list-none grid-cols-6 gap-2 text-sm">
                <p className="text-muted">{new Date(item.timestamp).toLocaleString()}</p>
                <p className={`font-medium ${decisionTone(item.decision)}`}>{item.decision.toUpperCase()}</p>
                <p className="text-text">{item.position_size_pct.toFixed(2)}%</p>
                <p className="text-text">{item.entry_price.toFixed(2)}</p>
                <p className="text-text">{(item.confidence * 100).toFixed(1)}%</p>
                <p className="truncate text-muted">{item.model_used}</p>
              </summary>

              <div className="mt-3 grid grid-cols-1 gap-3 border-t border-border/70 pt-3 lg:grid-cols-2">
                <article className="rounded-lg border border-border/70 bg-panel/50 p-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-muted">Mind Alignment</p>
                  <p className="mt-2 text-sm text-text">{item.reasoning.mind_alignment || "N/A"}</p>
                </article>

                <article className="rounded-lg border border-border/70 bg-panel/50 p-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-muted">Bias Check</p>
                  <p className="mt-2 text-sm text-text">{item.reasoning.bias_check || "N/A"}</p>
                </article>

                <article className="rounded-lg border border-border/70 bg-panel/50 p-3 lg:col-span-2">
                  <p className="text-xs uppercase tracking-[0.14em] text-muted">Full Reasoning</p>
                  <pre className="mt-2 overflow-auto whitespace-pre-wrap text-xs leading-6 text-muted">
                    {JSON.stringify(item.reasoning, null, 2)}
                  </pre>
                </article>
              </div>
            </details>
          ))}
        </div>

        {!loading && !filtered.length && <p className="px-3 py-4 text-sm text-muted">No decisions found.</p>}
        {loading && <p className="px-3 py-4 text-sm text-muted">Loading decisions...</p>}
      </section>
    </main>
  );
}

