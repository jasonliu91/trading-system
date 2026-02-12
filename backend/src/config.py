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

    trading_pair: str = os.getenv("TRADING_PAIR", "ETHUSDT")
    analysis_interval_hours: int = int(os.getenv("ANALYSIS_INTERVAL_HOURS", "4"))
    initial_balance: float = float(os.getenv("INITIAL_BALANCE", "10000"))
    max_position_pct: float = float(os.getenv("MAX_POSITION_PCT", "0.20"))
    max_exposure_pct: float = float(os.getenv("MAX_EXPOSURE_PCT", "0.60"))
    max_daily_loss_pct: float = float(os.getenv("MAX_DAILY_LOSS_PCT", "0.05"))
    max_stop_loss_pct: float = float(os.getenv("MAX_STOP_LOSS_PCT", "0.08"))
    trading_fee_pct: float = float(os.getenv("TRADING_FEE_PCT", "0.001"))
    slippage_pct: float = float(os.getenv("SLIPPAGE_PCT", "0.0005"))
    ai_model: str = os.getenv("AI_MODEL", "claude-sonnet-4-5-20250929")

    binance_base_url: str = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    scheduler_enabled: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"

    @property
    def database_url(self) -> str:
        return os.getenv("DATABASE_URL", f"sqlite:///{self.database_path}")

    def ensure_runtime_paths(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
