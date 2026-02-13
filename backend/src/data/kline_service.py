from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from backend.src.config import settings
from backend.src.data.binance_client import BinanceKlineClient
from backend.src.db.models import Kline

INITIAL_BACKFILL_LIMITS = {
    "1d": 90,
    "4h": 42,   # 7 days * 6
    "1h": 168,  # 7 days * 24
}


def _query_klines(db: Session, symbol: str, timeframe: str, limit: int) -> Select[tuple[Kline]]:
    return (
        select(Kline)
        .where(Kline.symbol == symbol, Kline.timeframe == timeframe)
        .order_by(Kline.open_time.desc())
        .limit(limit)
    )


def get_recent_klines(db: Session, symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]]:
    """查询最近N根K线数据，按时间正序返回。"""
    rows = db.execute(_query_klines(db=db, symbol=symbol, timeframe=timeframe, limit=limit)).scalars().all()
    rows = list(reversed(rows))
    return [
        {
            "symbol": row.symbol,
            "timeframe": row.timeframe,
            "open_time": row.open_time.isoformat(),
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": row.volume,
        }
        for row in rows
    ]


def upsert_klines(db: Session, klines: list[dict[str, Any]]) -> int:
    """批量插入或更新K线数据，通过(symbol, timeframe, open_time)去重。"""
    if not klines:
        return 0
    statement = sqlite_insert(Kline).values(klines)
    statement = statement.on_conflict_do_update(
        index_elements=["symbol", "timeframe", "open_time"],
        set_={
            "open": statement.excluded.open,
            "high": statement.excluded.high,
            "low": statement.excluded.low,
            "close": statement.excluded.close,
            "volume": statement.excluded.volume,
        },
    )
    result = db.execute(statement)
    db.commit()
    return result.rowcount or 0


def fetch_and_store_klines(
    db: Session,
    symbol: str,
    timeframe: str,
    limit: int,
    client: BinanceKlineClient | None = None,
) -> int:
    """从Binance获取K线数据并存入数据库，返回写入行数。"""
    client = client or BinanceKlineClient()
    klines = client.fetch_klines(symbol=symbol, timeframe=timeframe, limit=limit)
    return upsert_klines(db=db, klines=klines)


def maybe_backfill_initial_klines(db: Session, symbol: str | None = None) -> dict[str, int]:
    """检查各时间周期的K线数据量，不足时自动回填历史数据。"""
    symbol = symbol or settings.trading_pair
    inserted: dict[str, int] = {}

    for timeframe, limit in INITIAL_BACKFILL_LIMITS.items():
        existing_count = db.query(Kline).filter(Kline.symbol == symbol, Kline.timeframe == timeframe).count()
        if existing_count >= limit:
            inserted[timeframe] = 0
            continue
        inserted[timeframe] = fetch_and_store_klines(db=db, symbol=symbol, timeframe=timeframe, limit=limit)
    return inserted


def latest_price_from_db(db: Session, symbol: str | None = None) -> float | None:
    """从数据库获取最新价格，优先使用1h K线，回退到任意时间周期。"""
    symbol = symbol or settings.trading_pair
    row = (
        db.execute(
            select(Kline)
            .where(Kline.symbol == symbol, Kline.timeframe == "1h")
            .order_by(Kline.open_time.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if row is not None:
        return float(row.close)

    row = (
        db.execute(
            select(Kline)
            .where(Kline.symbol == symbol)
            .order_by(Kline.open_time.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if row is not None:
        return float(row.close)
    return None


def fallback_mock_klines(timeframe: str, limit: int, symbol: str | None = None) -> list[dict[str, Any]]:
    """生成模拟K线数据，用于数据库无数据时的前端展示降级。"""
    symbol = symbol or settings.trading_pair
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    step = {"1h": timedelta(hours=1), "4h": timedelta(hours=4), "1d": timedelta(days=1)}.get(timeframe, timedelta(hours=1))
    base_price = 3200.0
    items: list[dict[str, Any]] = []
    for index in range(limit):
        open_time = now - step * (limit - index)
        open_price = base_price + index * 1.8
        close_price = open_price + ((index % 5) - 2) * 1.2
        high_price = max(open_price, close_price) + 3.5
        low_price = min(open_price, close_price) - 3.5
        items.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "open_time": open_time.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": round(1100 + index * 9.5, 2),
            }
        )
    return items

