from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from backend.src.config import settings

logger = logging.getLogger(__name__)


class BinanceAPIError(RuntimeError):
    """Binance API请求失败时抛出的异常。"""


@dataclass
class BinanceKlineClient:
    """Binance REST API K线数据客户端，支持重试和超时控制。"""

    base_url: str = settings.binance_base_url
    timeout_sec: int = 10
    max_retries: int = 3

    def fetch_klines(self, symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]]:
        """
        从Binance获取K线数据，支持自动重试。

        失败时按指数退避重试最多max_retries次，每次等待2^attempt秒。
        """
        params = urlencode({"symbol": symbol.upper(), "interval": timeframe, "limit": limit})
        url = f"{self.base_url}/api/v3/klines?{params}"

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(url, timeout=self.timeout_sec) as response:
                    payload = response.read().decode("utf-8")
                break
            except URLError as exc:
                last_error = exc
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    logger.warning(
                        "Binance API请求失败 (尝试 %d/%d), %d秒后重试: %s",
                        attempt + 1, self.max_retries + 1, wait, exc,
                    )
                    time.sleep(wait)
        else:
            raise BinanceAPIError(f"Binance API请求在{self.max_retries + 1}次尝试后仍然失败: {last_error}") from last_error

        raw = json.loads(payload)
        if not isinstance(raw, list):
            raise BinanceAPIError(f"Binance返回了意外的响应格式: {raw}")

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
