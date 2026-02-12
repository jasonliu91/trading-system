from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "ETH AI Trading System API"
    app_version: str = "0.1.0"
    backend_dir: Path = Path(__file__).resolve().parents[1]
    project_root: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = Path(__file__).resolve().parents[1] / "data"
    database_path: Path = Path(__file__).resolve().parents[1] / "data" / "trading_system.db"
    market_mind_path: Path = Path(__file__).resolve().parents[1] / "data" / "market_mind.json"
    market_mind_template_path: Path = Path(__file__).resolve().parents[2] / "docs" / "market_mind_init.json"

    analysis_interval_hours: int = int(os.getenv("ANALYSIS_INTERVAL_HOURS", "4"))
    initial_balance: float = float(os.getenv("INITIAL_BALANCE", "10000"))

    @property
    def database_url(self) -> str:
        return os.getenv("DATABASE_URL", f"sqlite:///{self.database_path}")

    def ensure_runtime_paths(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()

