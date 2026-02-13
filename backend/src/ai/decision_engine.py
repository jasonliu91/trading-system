from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from backend.src.config import settings
from backend.src.mind.market_mind import inject_to_prompt


@dataclass
class DecisionContext:
    """AI决策所需的完整上下文，包含市场数据、持仓和认知状态。"""

    market_mind: dict[str, Any]
    daily_klines: list[dict[str, Any]]
    hourly_klines: list[dict[str, Any]]
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


def build_prompt(context: DecisionContext) -> str:
    """根据决策上下文构建LLM提示词，注入Market Mind认知状态和市场数据。"""
    mind_prompt = inject_to_prompt(context.market_mind)
    payload = {
        "daily_klines": context.daily_klines[-30:],
        "hourly_klines": context.hourly_klines[-24:],
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

    short_ma = _mean(daily_closes[-7:]) if len(daily_closes) >= 7 else _mean(daily_closes)
    long_ma = _mean(daily_closes[-21:]) if len(daily_closes) >= 21 else _mean(daily_closes)

    trend_score = 0.0
    if long_ma > 0:
        trend_score = (short_ma - long_ma) / long_ma

    if trend_score > 0.01:
        decision = "buy"
    elif trend_score < -0.01:
        decision = "sell"
    else:
        decision = "hold"

    confidence = min(0.9, max(0.45, abs(trend_score) * 12 + 0.45))
    desired_position_pct = round(min(settings.max_position_pct * 100, confidence * 20), 2)
    if decision == "hold":
        desired_position_pct = 0.0

    stop_loss = round(latest_price * (1 - settings.max_stop_loss_pct), 2) if latest_price else 0.0
    take_profit = round(latest_price * (1 + settings.max_stop_loss_pct * 2), 2) if latest_price else 0.0

    reasoning = {
        "market_regime": context.market_mind.get("market_beliefs", {}).get("regime", "unknown"),
        "mind_alignment": _infer_mind_alignment(context.market_mind, decision),
        "quant_signals_summary": f"daily_short_ma={short_ma:.2f}, daily_long_ma={long_ma:.2f}",
        "news_sentiment": "not_enabled_phase1",
        "key_factors": [
            f"trend_score={trend_score:.4f}",
            f"latest_price={latest_price:.2f}",
        ],
        "risk_considerations": ["执行硬性仓位上限", "执行止损距离上限"],
        "bias_check": _infer_bias_check(context.market_mind),
        "final_logic": "基于日线均线趋势和风险参数给出结构化建议。",
    }

    input_payload = {
        "mind": context.market_mind,
        "daily_klines": context.daily_klines[-30:],
        "hourly_klines": context.hourly_klines[-24:],
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

