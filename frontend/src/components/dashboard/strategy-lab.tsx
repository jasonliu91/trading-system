"use client";

import { QuantSignalItem, QuantSignalSummary, QuantStrategyDefinition } from "@/lib/types";

function signalTone(signal: string): string {
  if (signal === "buy") {
    return "text-bull";
  }
  if (signal === "sell") {
    return "text-bear";
  }
  return "text-muted";
}

interface StrategyLabProps {
  strategies: QuantStrategyDefinition[];
  signals: QuantSignalItem[];
  summary: QuantSignalSummary | null;
  activeStrategies: string[];
  showQuantSignals: boolean;
  showAIDecisions: boolean;
  minDecisionConfidence: number;
  onToggleStrategy: (strategyName: string) => void;
  onToggleQuantSignals: () => void;
  onToggleAIDecisions: () => void;
  onDecisionConfidenceChange: (value: number) => void;
}

export function StrategyLab({
  strategies,
  signals,
  summary,
  activeStrategies,
  showQuantSignals,
  showAIDecisions,
  minDecisionConfidence,
  onToggleStrategy,
  onToggleQuantSignals,
  onToggleAIDecisions,
  onDecisionConfidenceChange
}: StrategyLabProps) {
  const signalMap = new Map(signals.map((item) => [item.strategy_name, item]));

  return (
    <section className="space-y-4">
      <article className="rounded-2xl border border-border bg-panel/70 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-muted">AI Agent Filter</p>
            <p className="mt-1 text-sm text-text">
              Action: <span className={signalTone(summary?.recommended_action ?? "hold")}>{(summary?.recommended_action ?? "hold").toUpperCase()}</span>
              <span className="ml-3 text-muted">Score: {(summary?.composite_score ?? 0).toFixed(3)}</span>
              <span className="ml-3 text-muted">Confidence: {((summary?.confidence ?? 0) * 100).toFixed(1)}%</span>
            </p>
          </div>

          <div className="grid grid-cols-1 gap-2 text-xs text-muted md:grid-cols-3 md:items-end">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={showQuantSignals} onChange={onToggleQuantSignals} />
              Show Quant Signals
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={showAIDecisions} onChange={onToggleAIDecisions} />
              Show AI Decisions
            </label>
            <label className="space-y-1">
              <span>AI Min Confidence: {(minDecisionConfidence * 100).toFixed(0)}%</span>
              <input
                type="range"
                min={0}
                max={95}
                step={5}
                value={Math.round(minDecisionConfidence * 100)}
                onChange={(event) => onDecisionConfidenceChange(Number(event.target.value) / 100)}
                className="w-full"
              />
            </label>
          </div>
        </div>
      </article>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        {strategies.map((strategy) => {
          const signal = signalMap.get(strategy.strategy_name);
          const checked = activeStrategies.includes(strategy.strategy_name);
          return (
            <article key={strategy.strategy_name} className="rounded-2xl border border-border bg-panel/70 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-text">{strategy.display_name}</h3>
                  <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted">{strategy.category}</p>
                </div>
                <label className="flex items-center gap-2 text-xs text-muted">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => onToggleStrategy(strategy.strategy_name)}
                  />
                  Chart
                </label>
              </div>

              <p className="mt-3 text-sm leading-6 text-muted">{strategy.description}</p>

              <div className="mt-3 rounded-lg border border-border/70 bg-bg/35 p-3">
                <p className="text-xs uppercase tracking-[0.12em] text-muted">Latest Signal</p>
                <p className={`mt-1 text-sm font-semibold ${signalTone(signal?.signal ?? "hold")}`}>
                  {(signal?.signal ?? "hold").toUpperCase()} {(signal?.strength ?? 0).toFixed(3)}
                </p>
                <p className="mt-1 text-xs text-muted">{signal?.reasoning || "No signal reasoning"}</p>
              </div>

              <div className="mt-3 rounded-lg border border-border/70 bg-bg/35 p-3">
                <p className="text-xs uppercase tracking-[0.12em] text-muted">Logic Summary</p>
                <ul className="mt-2 space-y-1 text-xs leading-5 text-muted">
                  {strategy.logic_summary.map((item) => (
                    <li key={`${strategy.strategy_name}-${item}`}>- {item}</li>
                  ))}
                </ul>
              </div>

              <div className="mt-3 rounded-lg border border-border/70 bg-bg/35 p-3">
                <p className="text-xs uppercase tracking-[0.12em] text-muted">Script (Pine style)</p>
                <pre className="mt-2 max-h-[260px] overflow-auto whitespace-pre-wrap text-[11px] leading-5 text-text">
                  {strategy.pine_script}
                </pre>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
