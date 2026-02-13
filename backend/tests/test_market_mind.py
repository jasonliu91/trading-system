"""Market Mind 单元测试。"""
from __future__ import annotations

from backend.src.mind.market_mind import (
    _deep_merge,
    inject_to_prompt,
    validate_market_mind,
)


class TestDeepMerge:
    """深度合并测试。"""

    def test_simple_merge(self) -> None:
        base = {"a": 1, "b": 2}
        patch = {"b": 3, "c": 4}
        result = _deep_merge(base, patch)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self) -> None:
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        patch = {"a": {"y": 99, "z": 100}}
        result = _deep_merge(base, patch)
        assert result["a"] == {"x": 1, "y": 99, "z": 100}
        assert result["b"] == 3

    def test_does_not_mutate_base(self) -> None:
        base = {"a": {"x": 1}}
        _deep_merge(base, {"a": {"x": 2}})
        assert base["a"]["x"] == 1


class TestValidateMarketMind:
    """Market Mind 验证测试。"""

    def test_valid_mind(self) -> None:
        mind = {
            "market_beliefs": {"regime": "bullish"},
            "strategy_weights": {"ema_adx": 0.5},
            "lessons_learned": ["lesson1"],
            "bias_awareness": [{"bias": "test", "mitigation": "test"}],
        }
        warnings = validate_market_mind(mind)
        assert warnings == []

    def test_missing_required_fields(self) -> None:
        mind = {"version": "1.0"}
        warnings = validate_market_mind(mind)
        assert len(warnings) >= 4

    def test_wrong_type_bias_awareness(self) -> None:
        mind = {
            "market_beliefs": {},
            "strategy_weights": {},
            "lessons_learned": [],
            "bias_awareness": "not_a_list",
        }
        warnings = validate_market_mind(mind)
        assert any("bias_awareness" in w for w in warnings)

    def test_wrong_type_strategy_weights(self) -> None:
        mind = {
            "market_beliefs": {},
            "strategy_weights": "not_a_dict",
            "lessons_learned": [],
            "bias_awareness": [],
        }
        warnings = validate_market_mind(mind)
        assert any("strategy_weights" in w for w in warnings)

    def test_non_dict_input(self) -> None:
        warnings = validate_market_mind("not_a_dict")  # type: ignore[arg-type]
        assert any("JSON对象" in w for w in warnings)


class TestInjectToPrompt:
    """提示词注入测试。"""

    def test_contains_role(self) -> None:
        mind = {"bias_awareness": [], "performance_memory": {}}
        prompt = inject_to_prompt(mind)
        assert "ETH量化交易分析师" in prompt

    def test_contains_bias_count(self) -> None:
        mind = {
            "bias_awareness": [{"bias": "a"}, {"bias": "b"}],
            "performance_memory": {},
        }
        prompt = inject_to_prompt(mind)
        assert "2条提醒" in prompt

    def test_accuracy_na_when_missing(self) -> None:
        mind = {"bias_awareness": [], "performance_memory": {}}
        prompt = inject_to_prompt(mind)
        assert "N/A" in prompt
