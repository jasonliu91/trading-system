const cards = [
  { label: "Trading Pair", value: "ETHUSDT", tone: "text-text" },
  { label: "Mode", value: "Paper Trading", tone: "text-accent" },
  { label: "Core API", value: "http://localhost:8000", tone: "text-text" },
  { label: "Market Mind", value: "/mind (coming)", tone: "text-text" }
];

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-8 px-6 py-10 md:px-10">
      <header className="space-y-3">
        <p className="text-sm uppercase tracking-[0.24em] text-muted">ETH AI Trading System</p>
        <h1 className="text-3xl font-semibold leading-tight text-text md:text-5xl">
          Deterministic backbone, AI Market Mind, one shared control surface.
        </h1>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {cards.map((card) => (
          <article
            key={card.label}
            className="rounded-2xl border border-border bg-panel/70 p-5 shadow-panel backdrop-blur"
          >
            <p className="text-xs uppercase tracking-[0.18em] text-muted">{card.label}</p>
            <p className={`mt-2 text-lg font-medium ${card.tone}`}>{card.value}</p>
          </article>
        ))}
      </section>

      <section className="rounded-2xl border border-border bg-panel/60 p-5">
        <h2 className="text-lg font-medium text-text">Next Steps</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Kline chart, decisions board, performance view, and Market Mind editor will be connected in Phase 1 tasks T014-T018.
        </p>
      </section>
    </main>
  );
}

