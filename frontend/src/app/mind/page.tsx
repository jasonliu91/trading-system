"use client";

import { fetchMarketMind, fetchMarketMindHistory, updateMarketMind } from "@/lib/api";
import { MarketMindHistoryItem } from "@/lib/types";
import { useEffect, useMemo, useState } from "react";

function prettyJSON(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

export default function MarketMindPage() {
  const [marketMind, setMarketMind] = useState<Record<string, unknown> | null>(null);
  const [promptPreview, setPromptPreview] = useState<string>("");
  const [history, setHistory] = useState<MarketMindHistoryItem[]>([]);
  const [editorValue, setEditorValue] = useState<string>("");
  const [changeSummary, setChangeSummary] = useState("Updated from /mind page");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string>("");

  const sections = useMemo(() => {
    if (!marketMind) {
      return null;
    }
    return {
      marketBeliefs: (marketMind.market_beliefs as Record<string, unknown>) || {},
      strategyWeights: (marketMind.strategy_weights as Record<string, { weight?: number; reason?: string }>) || {},
      lessons: (marketMind.lessons_learned as Array<Record<string, unknown>>) || [],
      biases: (marketMind.bias_awareness as Array<Record<string, unknown>>) || []
    };
  }, [marketMind]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [mindPayload, historyPayload] = await Promise.all([
          fetchMarketMind(),
          fetchMarketMindHistory(30)
        ]);
        setMarketMind(mindPayload.market_mind);
        setPromptPreview(mindPayload.prompt_preview);
        setHistory(historyPayload);
        setEditorValue(prettyJSON(mindPayload.market_mind));
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load Market Mind");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccessMessage("");
    try {
      const parsed = JSON.parse(editorValue) as Record<string, unknown>;
      await updateMarketMind(parsed, "web_ui", changeSummary);
      const refreshed = await fetchMarketMind();
      setMarketMind(refreshed.market_mind);
      setPromptPreview(refreshed.prompt_preview);
      setEditorValue(prettyJSON(refreshed.market_mind));
      const historyPayload = await fetchMarketMindHistory(30);
      setHistory(historyPayload);
      setSuccessMessage("Saved successfully.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save Market Mind");
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 md:px-8 md:py-8">
      <header>
        <p className="text-xs uppercase tracking-[0.24em] text-muted">AI Cognitive State</p>
        <h1 className="mt-1 text-2xl font-semibold text-text md:text-4xl">Market Mind</h1>
      </header>

      {error && <section className="rounded-xl border border-bear/40 bg-bear/10 p-3 text-sm text-red-100">{error}</section>}
      {successMessage && (
        <section className="rounded-xl border border-bull/40 bg-bull/10 p-3 text-sm text-green-100">{successMessage}</section>
      )}

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-border bg-panel/70 p-5">
          <h2 className="text-sm uppercase tracking-[0.16em] text-muted">Market Beliefs</h2>
          <p className="mt-3 text-sm text-text">
            Regime: {(sections?.marketBeliefs?.regime as string) || "N/A"} (
            {String(sections?.marketBeliefs?.regime_confidence ?? "N/A")})
          </p>
          <p className="mt-2 text-sm leading-6 text-muted">{(sections?.marketBeliefs?.narrative as string) || "N/A"}</p>
        </article>

        <article className="rounded-2xl border border-border bg-panel/70 p-5">
          <h2 className="text-sm uppercase tracking-[0.16em] text-muted">Strategy Weights</h2>
          <div className="mt-3 space-y-2">
            {Object.entries(sections?.strategyWeights || {}).map(([name, config]) => (
              <div key={name} className="rounded-lg border border-border/70 bg-bg/35 p-3">
                <p className="text-sm font-medium text-text">{name}</p>
                <p className="text-xs text-muted">weight: {String(config.weight ?? "N/A")}</p>
                <p className="mt-1 text-xs leading-5 text-muted">{config.reason || "N/A"}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-border bg-panel/70 p-5">
          <h2 className="text-sm uppercase tracking-[0.16em] text-muted">Lessons Learned</h2>
          <div className="mt-3 space-y-2">
            {(sections?.lessons || []).map((item, index) => (
              <div key={`${item.lesson as string}-${index}`} className="rounded-lg border border-border/70 bg-bg/35 p-3">
                <p className="text-sm text-text">{(item.lesson as string) || "N/A"}</p>
                <p className="mt-1 text-xs text-muted">{(item.evidence as string) || "N/A"}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-border bg-panel/70 p-5">
          <h2 className="text-sm uppercase tracking-[0.16em] text-muted">Bias Awareness</h2>
          <div className="mt-3 space-y-2">
            {(sections?.biases || []).map((item, index) => (
              <div key={`${item.bias as string}-${index}`} className="rounded-lg border border-border/70 bg-bg/35 p-3">
                <p className="text-sm text-text">{(item.bias as string) || "N/A"}</p>
                <p className="mt-1 text-xs text-muted">{(item.mitigation as string) || "N/A"}</p>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="rounded-2xl border border-border bg-panel/70 p-5">
        <h2 className="text-sm uppercase tracking-[0.16em] text-muted">JSON Editor</h2>
        <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-4">
          <label className="text-xs uppercase tracking-[0.14em] text-muted lg:col-span-1">
            Change Summary
            <input
              value={changeSummary}
              onChange={(event) => setChangeSummary(event.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-bg/40 px-3 py-2 text-sm text-text outline-none focus:border-accent"
            />
          </label>

          <div className="lg:col-span-3 lg:text-right">
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={saving || loading}
              className="rounded-lg border border-accent px-3 py-2 text-xs uppercase tracking-[0.14em] text-accent disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Mind"}
            </button>
          </div>
        </div>

        <textarea
          value={editorValue}
          onChange={(event) => setEditorValue(event.target.value)}
          className="mt-3 h-[380px] w-full rounded-xl border border-border bg-bg/35 p-4 font-mono text-xs leading-6 text-text outline-none focus:border-accent"
          spellCheck={false}
        />
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-border bg-panel/70 p-5">
          <h2 className="text-sm uppercase tracking-[0.16em] text-muted">Prompt Preview</h2>
          <pre className="mt-3 max-h-[320px] overflow-auto whitespace-pre-wrap rounded-lg border border-border/70 bg-bg/35 p-3 text-xs leading-6 text-muted">
            {promptPreview || "No preview yet"}
          </pre>
        </article>

        <article className="rounded-2xl border border-border bg-panel/70 p-5">
          <h2 className="text-sm uppercase tracking-[0.16em] text-muted">History</h2>
          <div className="mt-3 max-h-[320px] space-y-2 overflow-auto">
            {history.map((item) => (
              <div key={item.id} className="rounded-lg border border-border/70 bg-bg/35 p-3">
                <p className="text-xs uppercase tracking-[0.12em] text-muted">{new Date(item.changed_at).toLocaleString()}</p>
                <p className="mt-1 text-sm text-text">{item.change_summary || "Market Mind updated"}</p>
                <p className="mt-1 text-xs text-muted">by {item.changed_by}</p>
              </div>
            ))}
            {!history.length && !loading && <p className="text-sm text-muted">No history records yet.</p>}
          </div>
        </article>
      </section>
    </main>
  );
}
