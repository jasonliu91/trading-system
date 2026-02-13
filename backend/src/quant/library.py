from __future__ import annotations

import math
from typing import Any, Literal

import pandas as pd
from ta.trend import ADXIndicator, EMAIndicator
from ta.volatility import AverageTrueRange

SignalAction = Literal["buy", "sell", "hold"]

STRATEGY_WEIGHTS: dict[str, float] = {
    "ema_adx_daily": 0.45,
    "supertrend_daily": 0.35,
    "donchian_breakout_daily": 0.20,
}


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clip_strength(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _signal_value(signal: str) -> float:
    if signal == "buy":
        return 1.0
    if signal == "sell":
        return -1.0
    return 0.0


def _build_dataframe(klines: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in klines:
        open_time = pd.to_datetime(item.get("open_time"), utc=True, errors="coerce")
        if pd.isna(open_time):
            continue
        rows.append(
            {
                "open_time": open_time,
                "open": _safe_float(item.get("open")),
                "high": _safe_float(item.get("high")),
                "low": _safe_float(item.get("low")),
                "close": _safe_float(item.get("close")),
                "volume": _safe_float(item.get("volume")),
            }
        )
    if not rows:
        return pd.DataFrame(columns=["open_time", "open", "high", "low", "close", "volume"])

    return (
        pd.DataFrame(rows)
        .drop_duplicates(subset=["open_time"])
        .sort_values("open_time")
        .reset_index(drop=True)
    )


def _build_signal(
    strategy_name: str,
    symbol: str,
    timeframe: str,
    timestamp: str | None,
    signal: SignalAction,
    strength: float,
    indicators: dict[str, float],
    reasoning: str,
) -> dict[str, Any]:
    return {
        "strategy_name": strategy_name,
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": timestamp,
        "signal": signal,
        "strength": _clip_strength(strength),
        "indicators": indicators,
        "reasoning": reasoning,
    }


def _hold_signal(strategy_name: str, symbol: str, timeframe: str, reason: str) -> dict[str, Any]:
    return _build_signal(
        strategy_name=strategy_name,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=None,
        signal="hold",
        strength=0.0,
        indicators={},
        reasoning=reason,
    )


def _ema_adx_signal(symbol: str, timeframe: str, df: pd.DataFrame) -> dict[str, Any]:
    strategy = "ema_adx_daily"
    if len(df) < 60:
        return _hold_signal(strategy, symbol, timeframe, "insufficient_klines_for_ema_adx")

    close = df["close"]
    high = df["high"]
    low = df["low"]

    ema_fast = EMAIndicator(close=close, window=20).ema_indicator()
    ema_slow = EMAIndicator(close=close, window=50).ema_indicator()
    adx = ADXIndicator(high=high, low=low, close=close, window=14).adx()

    fast = _safe_float(ema_fast.iloc[-1])
    slow = _safe_float(ema_slow.iloc[-1])
    adx_latest = _safe_float(adx.iloc[-1])
    if fast <= 0 or slow <= 0:
        return _hold_signal(strategy, symbol, timeframe, "invalid_indicator_values")

    trend_gap = (fast - slow) / slow
    signal: SignalAction = "hold"
    if adx_latest >= 25 and trend_gap > 0:
        signal = "buy"
    elif adx_latest >= 25 and trend_gap < 0:
        signal = "sell"

    strength = abs(trend_gap) * 14 + max(0.0, adx_latest - 20) / 40
    reasoning = f"ema_fast={fast:.2f}, ema_slow={slow:.2f}, adx={adx_latest:.2f}, gap={trend_gap:.4f}"
    return _build_signal(
        strategy_name=strategy,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=df["open_time"].iloc[-1].isoformat(),
        signal=signal,
        strength=strength,
        indicators={
            "ema_fast": round(fast, 4),
            "ema_slow": round(slow, 4),
            "adx": round(adx_latest, 4),
            "trend_gap": round(trend_gap, 6),
        },
        reasoning=reasoning,
    )


def _compute_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> tuple[pd.Series, pd.Series]:
    atr = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=period).average_true_range()
    hl2 = (df["high"] + df["low"]) / 2
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    final_upper = upper.copy()
    final_lower = lower.copy()
    supertrend: list[float] = [math.nan] * len(df)
    direction: list[int] = [1] * len(df)

    if len(df) > 0 and not pd.isna(atr.iloc[0]):
        supertrend[0] = lower.iloc[0]

    for index in range(1, len(df)):
        if pd.isna(atr.iloc[index]):
            direction[index] = direction[index - 1]
            continue

        prev_close = _safe_float(df["close"].iloc[index - 1])

        prev_upper = final_upper.iloc[index - 1]
        prev_lower = final_lower.iloc[index - 1]
        if pd.isna(prev_upper):
            prev_upper = upper.iloc[index - 1]
        if pd.isna(prev_lower):
            prev_lower = lower.iloc[index - 1]

        current_upper = upper.iloc[index]
        current_lower = lower.iloc[index]

        final_upper.iloc[index] = current_upper if current_upper < prev_upper or prev_close > prev_upper else prev_upper
        final_lower.iloc[index] = current_lower if current_lower > prev_lower or prev_close < prev_lower else prev_lower

        prev_direction = direction[index - 1]
        close_price = _safe_float(df["close"].iloc[index])
        if prev_direction == -1 and close_price > _safe_float(final_upper.iloc[index]):
            direction[index] = 1
        elif prev_direction == 1 and close_price < _safe_float(final_lower.iloc[index]):
            direction[index] = -1
        else:
            direction[index] = prev_direction

        supertrend[index] = _safe_float(final_lower.iloc[index]) if direction[index] == 1 else _safe_float(final_upper.iloc[index])

    return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)


def _supertrend_signal(symbol: str, timeframe: str, df: pd.DataFrame) -> dict[str, Any]:
    strategy = "supertrend_daily"
    if len(df) < 30:
        return _hold_signal(strategy, symbol, timeframe, "insufficient_klines_for_supertrend")

    supertrend, direction = _compute_supertrend(df=df, period=10, multiplier=3.0)
    latest_supertrend = _safe_float(supertrend.iloc[-1])
    latest_close = _safe_float(df["close"].iloc[-1])
    latest_direction = int(direction.iloc[-1]) if len(direction) > 0 else 1

    if latest_supertrend <= 0 or latest_close <= 0:
        return _hold_signal(strategy, symbol, timeframe, "invalid_indicator_values")

    signal: SignalAction = "buy" if latest_direction == 1 else "sell"
    distance_ratio = abs((latest_close - latest_supertrend) / latest_close)
    strength = distance_ratio * 25
    reasoning = f"close={latest_close:.2f}, supertrend={latest_supertrend:.2f}, direction={latest_direction}"
    return _build_signal(
        strategy_name=strategy,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=df["open_time"].iloc[-1].isoformat(),
        signal=signal,
        strength=strength,
        indicators={
            "supertrend": round(latest_supertrend, 4),
            "direction": float(latest_direction),
            "distance_ratio": round(distance_ratio, 6),
        },
        reasoning=reasoning,
    )


def _donchian_signal(symbol: str, timeframe: str, df: pd.DataFrame) -> dict[str, Any]:
    strategy = "donchian_breakout_daily"
    if len(df) < 25:
        return _hold_signal(strategy, symbol, timeframe, "insufficient_klines_for_donchian")

    upper_prev = df["high"].rolling(window=20).max().shift(1)
    lower_prev = df["low"].rolling(window=20).min().shift(1)

    upper = _safe_float(upper_prev.iloc[-1])
    lower = _safe_float(lower_prev.iloc[-1])
    latest_close = _safe_float(df["close"].iloc[-1])

    if upper <= 0 or lower <= 0 or latest_close <= 0:
        return _hold_signal(strategy, symbol, timeframe, "invalid_indicator_values")

    signal: SignalAction = "hold"
    breakout_pct = 0.0
    if latest_close > upper:
        signal = "buy"
        breakout_pct = (latest_close - upper) / latest_close
    elif latest_close < lower:
        signal = "sell"
        breakout_pct = (lower - latest_close) / latest_close

    strength = breakout_pct * 35
    reasoning = f"close={latest_close:.2f}, upper_prev={upper:.2f}, lower_prev={lower:.2f}, breakout={breakout_pct:.4f}"
    return _build_signal(
        strategy_name=strategy,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=df["open_time"].iloc[-1].isoformat(),
        signal=signal,
        strength=strength,
        indicators={
            "donchian_upper_prev": round(upper, 4),
            "donchian_lower_prev": round(lower, 4),
            "breakout_pct": round(breakout_pct, 6),
        },
        reasoning=reasoning,
    )


def summarize_quant_signals(signals: list[dict[str, Any]]) -> dict[str, Any]:
    if not signals:
        return {
            "recommended_action": "hold",
            "composite_score": 0.0,
            "confidence": 0.45,
            "signal_count": 0,
            "active_signal_count": 0,
            "bullish_count": 0,
            "bearish_count": 0,
            "hold_count": 0,
        }

    weighted_score = 0.0
    total_weight = 0.0
    bullish = 0
    bearish = 0
    hold = 0
    active = 0

    for item in signals:
        signal = str(item.get("signal", "hold")).lower()
        strength = _clip_strength(_safe_float(item.get("strength", 0.0)))
        if signal == "buy":
            bullish += 1
            active += 1
        elif signal == "sell":
            bearish += 1
            active += 1
        else:
            hold += 1

        weight = _safe_float(STRATEGY_WEIGHTS.get(str(item.get("strategy_name")), 1.0))
        weighted_score += weight * _signal_value(signal) * strength
        total_weight += weight

    composite_score = weighted_score / total_weight if total_weight > 0 else 0.0
    if composite_score >= 0.20:
        action: SignalAction = "buy"
    elif composite_score <= -0.20:
        action = "sell"
    else:
        action = "hold"

    confidence = min(0.95, 0.45 + abs(composite_score) * 0.75 + max(0, active - 1) * 0.05)
    return {
        "recommended_action": action,
        "composite_score": round(composite_score, 6),
        "confidence": round(confidence, 3),
        "signal_count": len(signals),
        "active_signal_count": active,
        "bullish_count": bullish,
        "bearish_count": bearish,
        "hold_count": hold,
    }


def build_quant_snapshot(symbol: str, timeframe: str, klines: list[dict[str, Any]]) -> dict[str, Any]:
    df = _build_dataframe(klines)
    if df.empty:
        signals = [
            _hold_signal("ema_adx_daily", symbol, timeframe, "no_klines"),
            _hold_signal("supertrend_daily", symbol, timeframe, "no_klines"),
            _hold_signal("donchian_breakout_daily", symbol, timeframe, "no_klines"),
        ]
        return {"signals": signals, "summary": summarize_quant_signals(signals)}

    signals = [
        _ema_adx_signal(symbol=symbol, timeframe=timeframe, df=df),
        _supertrend_signal(symbol=symbol, timeframe=timeframe, df=df),
        _donchian_signal(symbol=symbol, timeframe=timeframe, df=df),
    ]
    return {"signals": signals, "summary": summarize_quant_signals(signals)}
