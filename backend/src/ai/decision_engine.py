from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from backend.src.config import settings
from backend.src.mind.market_mind import inject_to_prompt
from backend.src.quant.library import STRATEGY_WEIGHTS, summarize_quant_signals


@dataclass
class DecisionContext:
    """AI决策所需的完整上下文，包含市场数据、持仓和认知状态。"""

    market_mind: dict[str, Any]
    daily_klines: list[dict[str, Any]]
    hourly_klines: list[dict[str, Any]]
    quant_signals: list[dict[str, Any]]
    portfolio: dict[str, Any]
    recent_decisions: list[dict[str, Any]]


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全地将任意值转换为浮点数，转换失败时返回默认值。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _close_series(klines: list[dict[str, Any]]) -> list[float]:
    """从K线数据中提取收盘价序列，过滤无效值。"""
    closes: list[float] = []
    for row in klines:
        close = _safe_float(row.get("close"))
        if close > 0:
            closes.append(close)
    return closes


def _mean(values: list[float]) -> float:
    """计算数值列表的算术平均值。"""
    return sum(values) / len(values) if values else 0.0


def _fallback_trend_decision(daily_closes: list[float]) -> tuple[str, float, float, float]:
    short_ma = _mean(daily_closes[-7:]) if len(daily_closes) >= 7 else _mean(daily_closes)
    long_ma = _mean(daily_closes[-21:]) if len(daily_closes) >= 21 else _mean(daily_closes)
    trend_score = ((short_ma - long_ma) / long_ma) if long_ma > 0 else 0.0

    if trend_score > 0.01:
        decision = "buy"
    elif trend_score < -0.01:
        decision = "sell"
    else:
        decision = "hold"
    return decision, trend_score, short_ma, long_ma


def build_prompt(context: DecisionContext) -> str:
    """根据决策上下文构建LLM提示词，注入Market Mind认知状态和市场数据。"""
    mind_prompt = inject_to_prompt(context.market_mind)
    payload = {
        "daily_klines": context.daily_klines[-30:],
        "hourly_klines": context.hourly_klines[-24:],
        "quant_signals": context.quant_signals,
        "portfolio": context.portfolio,
        "recent_decisions": context.recent_decisions[-5:],
        "output_required_fields": [
            "decision",
            "position_size_pct",
            "entry_price",
            "stop_loss",
            "take_profit",
            "confidence",
            "reasoning.mind_alignment",
            "reasoning.bias_check",
        ],
    }
    return f"{mind_prompt}\n## 任务输入\n{json.dumps(payload, ensure_ascii=False)}"


def _infer_bias_check(market_mind: dict[str, Any]) -> str:
    """从Market Mind的偏误警觉列表推断当前偏误检查文本。"""
    items = market_mind.get("bias_awareness", [])
    if not items:
        return "未配置偏误警觉项，默认执行保守仓位规则。"
    first = items[0]
    bias = first.get("bias", "未知偏误")
    mitigation = first.get("mitigation", "执行双重信号确认")
    return f"检查偏误: {bias}；缓解措施: {mitigation}。"


def _infer_mind_alignment(market_mind: dict[str, Any], signal: str) -> str:
    """判断当前交易信号与Market Mind认知状态的一致性。"""
    regime = market_mind.get("market_beliefs", {}).get("regime", "")
    if signal == "buy":
        return f"当前信号偏多，与Market Mind的市场阶段判断({regime or '未定义'})一致。"
    if signal == "sell":
        return f"当前信号转弱，与Market Mind的风险优先原则保持一致。"
    return "趋势不明确，符合Market Mind中降低噪音交易的原则。"


def _extract_weight(value: Any) -> float | None:
    if isinstance(value, dict):
        return _extract_weight(value.get("weight"))
    parsed = _safe_float(value, default=-1)
    if parsed < 0:
        return None
    return parsed


def _mind_weight_map(market_mind: dict[str, Any]) -> dict[str, float]:
    raw = market_mind.get("strategy_weights", {})
    if not isinstance(raw, dict):
        return {}

    result: dict[str, float] = {}
    for key, value in raw.items():
        weight = _extract_weight(value)
        if weight is None:
            continue
        normalized = max(0.0, min(2.0, weight))
        result[str(key)] = round(normalized, 4)
    return result


def _regime_multiplier(regime: str, category: str) -> float:
    normalized = regime.lower()
    trend_tokens = ("trend", "bull", "bear", "up", "down", "breakout", "趋势", "牛", "熊")
    range_tokens = ("range", "sideway", "consolidat", "chop", "震荡", "区间")

    if any(token in normalized for token in trend_tokens):
        if category == "trend_following":
            return 1.15
        if category == "breakout":
            return 1.05
        if category == "mean_reversion":
            return 0.85
        return 1.0

    if any(token in normalized for token in range_tokens):
        if category == "mean_reversion":
            return 1.15
        if category == "trend_following":
            return 0.85
        if category == "breakout":
            return 0.9
        return 1.0

    return 1.0


def _clip(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _apply_agent_filter(
    market_mind: dict[str, Any],
    quant_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    regime = str(market_mind.get("market_beliefs", {}).get("regime", ""))
    mind_weights = _mind_weight_map(market_mind)
    min_strength = 0.18

    filtered_signals: list[dict[str, Any]] = []
    for item in quant_signals:
        strategy_name = str(item.get("strategy_name", ""))
        category = str(item.get("category", "unknown"))

        raw_signal = str(item.get("signal", "hold")).lower()
        raw_strength = _clip(_safe_float(item.get("strength", 0.0)), 0.0, 1.0)

        static_weight = _safe_float(STRATEGY_WEIGHTS.get(strategy_name), 1.0)
        exact_weight = _safe_float(mind_weights.get(strategy_name), 1.0)
        category_weight = _safe_float(mind_weights.get(category), 1.0)
        regime_weight = _regime_multiplier(regime=regime, category=category)
        combined_weight = _clip(exact_weight * category_weight * regime_weight, 0.15, 2.0)

        adjusted_strength = _clip(raw_strength * combined_weight, 0.0, 1.0)
        accepted = raw_signal in {"buy", "sell"} and adjusted_strength >= min_strength

        filter_reason = "accepted"
        filtered_signal = raw_signal
        if raw_signal == "hold":
            filter_reason = "raw_signal_is_hold"
        elif not accepted:
            filtered_signal = "hold"
            filter_reason = "suppressed_by_agent_filter"

        next_item = dict(item)
        next_item["raw_signal"] = raw_signal
        next_item["raw_strength"] = round(raw_strength, 4)
        next_item["signal"] = filtered_signal
        next_item["strength"] = round(adjusted_strength, 4)
        next_item["agent_filter"] = {
            "accepted": accepted,
            "reason": filter_reason,
            "static_weight": round(static_weight, 4),
            "mind_strategy_weight": round(exact_weight, 4),
            "mind_category_weight": round(category_weight, 4),
            "regime_weight": round(regime_weight, 4),
            "combined_weight": round(combined_weight, 4),
            "threshold": min_strength,
        }
        filtered_signals.append(next_item)

    summary = summarize_quant_signals(filtered_signals)
    return {
        "signals": filtered_signals,
        "summary": summary,
        "mind_weights": mind_weights,
        "market_regime": regime,
        "threshold": min_strength,
    }


def generate_decision(context: DecisionContext) -> dict[str, Any]:
    """
    根据市场数据和认知状态生成交易决策。

    当前为Phase 1确定性策略（7/21日线均线交叉），后续将替换为真实LLM调用。
    返回包含 decision/position_size_pct/entry_price/stop_loss/take_profit/
    confidence/reasoning 等字段的完整决策字典。
    """
    daily_closes = _close_series(context.daily_klines)
    hourly_closes = _close_series(context.hourly_klines)
    latest_price = hourly_closes[-1] if hourly_closes else (daily_closes[-1] if daily_closes else 0.0)

    raw_summary = summarize_quant_signals(context.quant_signals)
    filtered_view = _apply_agent_filter(market_mind=context.market_mind, quant_signals=context.quant_signals)
    quant_summary = filtered_view["summary"]

    decision = str(quant_summary.get("recommended_action", "hold")).lower()
    composite_score = _safe_float(quant_summary.get("composite_score", 0.0))
    confidence = _safe_float(quant_summary.get("confidence", 0.45))
    active_signal_count = int(_safe_float(quant_summary.get("active_signal_count", 0.0)))

    # Fallback to MA trend when all filtered strategy signals are neutral.
    if decision == "hold" and active_signal_count == 0 and daily_closes:
        decision, composite_score, short_ma, long_ma = _fallback_trend_decision(daily_closes=daily_closes)
        confidence = min(0.9, max(0.45, abs(composite_score) * 12 + 0.45))
    else:
        short_ma = _mean(daily_closes[-7:]) if len(daily_closes) >= 7 else _mean(daily_closes)
        long_ma = _mean(daily_closes[-21:]) if len(daily_closes) >= 21 else _mean(daily_closes)

    desired_position_pct = round(min(settings.max_position_pct * 100, confidence * 20), 2)
    if decision == "hold":
        desired_position_pct = 0.0

    stop_loss = round(latest_price * (1 - settings.max_stop_loss_pct), 2) if latest_price else 0.0
    take_profit = round(latest_price * (1 + settings.max_stop_loss_pct * 2), 2) if latest_price else 0.0

    filter_signals = []
    for item in filtered_view["signals"]:
        filter_signals.append(
            {
                "strategy_name": item.get("strategy_name"),
                "display_name": item.get("display_name"),
                "raw_signal": item.get("raw_signal"),
                "raw_strength": item.get("raw_strength"),
                "filtered_signal": item.get("signal"),
                "filtered_strength": item.get("strength"),
                "accepted": bool(item.get("agent_filter", {}).get("accepted", False)),
                "reason": item.get("agent_filter", {}).get("reason", ""),
            }
        )

    reasoning = {
        "market_regime": context.market_mind.get("market_beliefs", {}).get("regime", "unknown"),
        "mind_alignment": _infer_mind_alignment(context.market_mind, decision),
        "quant_signals_summary": (
            f"raw_score={_safe_float(raw_summary.get('composite_score', 0.0)):.4f}, "
            f"filtered_score={composite_score:.4f}, action={decision}, "
            f"votes(buy/sell/hold)="
            f"{int(_safe_float(quant_summary.get('bullish_count', 0)))}"
            f"/{int(_safe_float(quant_summary.get('bearish_count', 0)))}"
            f"/{int(_safe_float(quant_summary.get('hold_count', 0)))}"
        ),
        "agent_filter": {
            "market_regime": filtered_view.get("market_regime"),
            "mind_weights": filtered_view.get("mind_weights", {}),
            "threshold": filtered_view.get("threshold", 0.18),
            "raw_recommended_action": raw_summary.get("recommended_action"),
            "raw_composite_score": raw_summary.get("composite_score"),
            "filtered_recommended_action": quant_summary.get("recommended_action"),
            "filtered_composite_score": quant_summary.get("composite_score"),
            "active_signal_count": quant_summary.get("active_signal_count"),
            "signals": filter_signals,
        },
        "news_sentiment": "not_enabled_phase1",
        "key_factors": [
            f"quant_composite_score={composite_score:.4f}",
            f"active_signal_count={active_signal_count}",
            f"daily_short_ma={short_ma:.2f}",
            f"daily_long_ma={long_ma:.2f}",
            f"latest_price={latest_price:.2f}",
        ],
        "risk_considerations": ["执行硬性仓位上限", "执行止损距离上限"],
        "bias_check": _infer_bias_check(context.market_mind),
        "final_logic": "AI agent根据Market Mind过滤量化信号后输出结构化决策，再交由风控执行。",
    }

    input_payload = {
        "mind": context.market_mind,
        "daily_klines": context.daily_klines[-30:],
        "hourly_klines": context.hourly_klines[-24:],
        "quant_signals": context.quant_signals,
        "quant_signals_filtered": filtered_view["signals"],
        "portfolio": context.portfolio,
        "recent_decisions": context.recent_decisions[-5:],
    }
    input_hash = hashlib.sha256(json.dumps(input_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "position_size_pct": desired_position_pct,
        "entry_price": round(latest_price, 2),
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": round(confidence, 3),
        "reasoning": reasoning,
        "model_used": settings.ai_model,
        "input_hash": input_hash,
        "prompt_preview": build_prompt(context),
    }
