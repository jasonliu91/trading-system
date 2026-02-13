"use client";

import { Timeframe } from "@/lib/types";

const options: Timeframe[] = ["1h", "4h", "1d"];

export function TimeframeSwitcher({
  value,
  onChange
}: {
  value: Timeframe;
  onChange: (timeframe: Timeframe) => void;
}) {
  return (
    <div className="inline-flex rounded-xl border border-border bg-panel/80 p-1">
      {options.map((timeframe) => {
        const active = timeframe === value;
        return (
          <button
            key={timeframe}
            type="button"
            onClick={() => onChange(timeframe)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium uppercase tracking-[0.16em] transition ${
              active ? "bg-accent/25 text-accent" : "text-muted hover:text-text"
            }`}
          >
            {timeframe}
          </button>
        );
      })}
    </div>
  );
}

