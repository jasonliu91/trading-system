from __future__ import annotations

from backend.src.config import settings
from backend.src.db.database import Base, engine
from backend.src.db.models import Decision, Kline, MarketMindHistory, Performance, Trade


def init_db() -> None:
    _ = (Kline, Decision, Trade, Performance, MarketMindHistory)
    settings.ensure_runtime_paths()
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {settings.database_path}")

