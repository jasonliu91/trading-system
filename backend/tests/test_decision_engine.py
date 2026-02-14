"""决策引擎单元测试。"""
from __future__ import annotations

from backend.src.ai.decision_engine import (
    DecisionContext,
    _close_series,
    _infer_bias_check,
    _infer_mind_alignment,
    _mean,
    _safe_float,
    build_prompt,
    generate_decision,
)


class TestHelpers:
    """辅助函数测试。"""

    def test_safe_float_valid(self) -> None:
        assert _safe_float("3.14") == 3.14
        assert _safe_float(42) == 42.0

    def test_safe_float_invalid(self) -> None:
        assert _safe_float("abc") == 0.0
        assert _safe_float(None) == 0.0
        assert _safe_float(None, default=-1.0) == -1.0

    def test_close_series_extracts_valid(self) -> None:
        klines = [{"close": 100.0}, {"close": 0}, {"close": 200.0}]
        result = _close_series(klines)
        assert result == [100.0, 200.0]

    def test_close_series_empty(self) -> None:
        assert _close_series([]) == []

    def test_mean_normal(self) -> None:
        assert _mean([10.0, 20.0, 30.0]) == 20.0

    def test_mean_empty(self) -> None:
        assert _mean([]) == 0.0


class TestBiasCheck:
    """偏误检查推断测试。"""

    def test_empty_bias_awareness(self) -> None:
        result = _infer_bias_check({"bias_awareness": []})
        assert "保守" in result

    def test_with_bias_items(self) -> None:
        mind = {
            "bias_awareness": [
                {"bias": "确认偏误", "mitigation": "执行双重确认"},
            ]
        }
        result = _infer_bias_check(mind)
        assert "确认偏误" in result
        assert "双重确认" in result


class TestMindAlignment:
    """认知对齐推断测试。"""

    def test_buy_alignment(self) -> None:
        mind = {"market_beliefs": {"regime": "bullish"}}
        result = _infer_mind_alignment(mind, "buy")
        assert "bullish" in result
        assert "偏多" in result

    def test_sell_alignment(self) -> None:
        mind = {"market_beliefs": {"regime": "bearish"}}
        result = _infer_mind_alignment(mind, "sell")
        assert "风险" in result

    def test_hold_alignment(self) -> None:
        mind = {"market_beliefs": {"regime": "range"}}
        result = _infer_mind_alignment(mind, "hold")
        assert "不明确" in result


def _make_klines(closes: list[float], timeframe: str = "1d") -> list[dict]:
    return [
        {"close": c, "open": c, "high": c + 10, "low": c - 10, "volume": 1000, "open_time": f"2025-01-{i+1:02d}T00:00:00", "timeframe": timeframe}
        for i, c in enumerate(closes)
    ]


class TestGenerateDecision:
    """决策生成集成测试。"""

    def test_returns_required_fields(self) -> None:
        """决策结果必须包含所有必要字段。"""
        context = DecisionContext(
            market_mind={"market_beliefs": {"regime": "bullish"}, "bias_awareness": []},
            daily_klines=_make_klines([100 + i * 2 for i in range(30)]),
            hourly_klines=_make_klines([150 + i for i in range(24)], "1h"),
            portfolio={"equity": 10000, "balance": 10000, "exposure_pct": 0},
            recent_decisions=[],
        )
        result = generate_decision(context)

        required_fields = [
            "timestamp", "decision", "position_size_pct", "entry_price",
            "stop_loss", "take_profit", "confidence", "reasoning",
            "model_used", "input_hash",
        ]
        for field in required_fields:
            assert field in result, f"缺少字段: {field}"

    def test_decision_is_valid_action(self) -> None:
        """决策动作必须是 buy/sell/hold 之一。"""
        context = DecisionContext(
            market_mind={"market_beliefs": {}, "bias_awareness": []},
            daily_klines=_make_klines([100] * 30),
            hourly_klines=_make_klines([100] * 24, "1h"),
            portfolio={"equity": 10000, "balance": 10000, "exposure_pct": 0},
            recent_decisions=[],
        )
        result = generate_decision(context)
        assert result["decision"] in ("buy", "sell", "hold")

    def test_uptrend_signals_buy(self) -> None:
        """明显上升趋势应触发买入信号。"""
        # 7日均线 >> 21日均线
        closes = [100 + i * 5 for i in range(30)]
        context = DecisionContext(
            market_mind={"market_beliefs": {"regime": "bullish"}, "bias_awareness": []},
            daily_klines=_make_klines(closes),
            hourly_klines=_make_klines([closes[-1]] * 24, "1h"),
            portfolio={"equity": 10000, "balance": 10000, "exposure_pct": 0},
            recent_decisions=[],
        )
        result = generate_decision(context)
        assert result["decision"] == "buy"

    def test_downtrend_signals_sell(self) -> None:
        """明显下降趋势应触发卖出信号。"""
        closes = [300 - i * 5 for i in range(30)]
        context = DecisionContext(
            market_mind={"market_beliefs": {"regime": "bearish"}, "bias_awareness": []},
            daily_klines=_make_klines(closes),
            hourly_klines=_make_klines([closes[-1]] * 24, "1h"),
            portfolio={"equity": 10000, "balance": 10000, "exposure_pct": 0},
            recent_decisions=[],
        )
        result = generate_decision(context)
        assert result["decision"] == "sell"

    def test_flat_market_signals_hold(self) -> None:
        """横盘行情应触发持有信号。"""
        closes = [100.0] * 30
        context = DecisionContext(
            market_mind={"market_beliefs": {"regime": "range"}, "bias_awareness": []},
            daily_klines=_make_klines(closes),
            hourly_klines=_make_klines([100.0] * 24, "1h"),
            portfolio={"equity": 10000, "balance": 10000, "exposure_pct": 0},
            recent_decisions=[],
        )
        result = generate_decision(context)
        assert result["decision"] == "hold"

    def test_reasoning_contains_required_fields(self) -> None:
        """reasoning 必须包含 mind_alignment 和 bias_check。"""
        context = DecisionContext(
            market_mind={"market_beliefs": {}, "bias_awareness": []},
            daily_klines=_make_klines([100] * 30),
            hourly_klines=_make_klines([100] * 24, "1h"),
            portfolio={"equity": 10000, "balance": 10000, "exposure_pct": 0},
            recent_decisions=[],
        )
        result = generate_decision(context)
        assert "mind_alignment" in result["reasoning"]
        assert "bias_check" in result["reasoning"]

    def test_confidence_in_range(self) -> None:
        """置信度必须在 [0, 1] 范围内。"""
        context = DecisionContext(
            market_mind={"market_beliefs": {}, "bias_awareness": []},
            daily_klines=_make_klines([100 + i for i in range(30)]),
            hourly_klines=_make_klines([130] * 24, "1h"),
            portfolio={"equity": 10000, "balance": 10000, "exposure_pct": 0},
            recent_decisions=[],
        )
        result = generate_decision(context)
        assert 0 <= result["confidence"] <= 1.0


class TestBuildPrompt:
    """提示词构建测试。"""

    def test_contains_market_mind(self) -> None:
        context = DecisionContext(
            market_mind={"market_beliefs": {"regime": "test_regime"}, "bias_awareness": []},
            daily_klines=[],
            hourly_klines=[],
            portfolio={},
            recent_decisions=[],
        )
        prompt = build_prompt(context)
        assert "Market Mind" in prompt
        assert "test_regime" in prompt
