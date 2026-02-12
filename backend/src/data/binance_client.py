from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from backend.src.config import settings


class BinanceAPIError(RuntimeError):
    """Raised when Binance API request fails."""


@dataclass
class BinanceKlineClient:
    base_url: str = settings.binance_base_url
    timeout_sec: int = 10

    def fetch_klines(self, symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]]:
        params = urlencode({"symbol": symbol.upper(), "interval": timeframe, "limit": limit})
        url = f"{self.base_url}/api/v3/klines?{params}"
        try:
            with urlopen(url, timeout=self.timeout_sec) as response:
                payload = response.read().decode("utf-8")
        except URLError as exc:
            raise BinanceAPIError(f"Failed to fetch klines: {exc}") from exc

        raw = json.loads(payload)
        if not isinstance(raw, list):
            raise BinanceAPIError(f"Unexpected Binance response: {raw}")

        klines: list[dict[str, Any]] = []
        for row in raw:
            # Binance kline schema:
            # [open_time, open, high, low, close, volume, close_time, ...]
            open_time_ms = int(row[0])
            klines.append(
                {
                    "symbol": symbol.upper(),
                    "timeframe": timeframe,
                    "open_time": datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                }
            )
        return klines

