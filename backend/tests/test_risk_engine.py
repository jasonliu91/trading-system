"""风控引擎单元测试。"""
from __future__ import annotations

from backend.src.risk.engine import RiskCheckResult, apply_risk_checks


def _base_decision(
    action: str = "buy",
    position_size_pct: float = 10.0,
    entry_price: float = 3000.0,
    stop_loss: float = 2800.0,
    take_profit: float = 3400.0,
    confidence: float = 0.7,
) -> dict:
    return {
        "decision": action,
        "position_size_pct": position_size_pct,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": confidence,
    }


def _base_portfolio(
    exposure_pct: float = 0.0,
    daily_pnl_pct: float = 0.0,
) -> dict:
    return {
        "exposure_pct": exposure_pct,
        "daily_pnl_pct": daily_pnl_pct,
    }


def _base_market_mind() -> dict:
    return {
        "market_beliefs": {"regime": "range_bound"},
        "bias_awareness": [],
        "strategy_weights": {},
    }


class TestApplyRiskChecks:
    """apply_risk_checks 核心逻辑测试。"""

    def test_valid_buy_passes(self) -> None:
        """正常buy决策应该通过风控。"""
        result = apply_risk_checks(
            decision=_base_decision(),
            portfolio=_base_portfolio(),
            market_mind=_base_market_mind(),
        )
        assert result.approved is True
        assert result.violations == []

    def test_hold_always_passes(self) -> None:
        """hold决策不执行任何风控检查。"""
        result = apply_risk_checks(
            decision=_base_decision(action="hold"),
            portfolio=_base_portfolio(),
            market_mind=_base_market_mind(),
        )
        assert result.approved is True
        assert result.violations == []

    def test_invalid_action_rejected(self) -> None:
        """无效的决策动作应被拒绝。"""
        result = apply_risk_checks(
            decision=_base_decision(action="invalid"),
            portfolio=_base_portfolio(),
            market_mind=_base_market_mind(),
        )
        assert result.approved is False
        assert any("Invalid" in v for v in result.violations)

    def test_position_size_cap(self) -> None:
        """超过最大仓位限制的决策应被调整。"""
        result = apply_risk_checks(
            decision=_base_decision(position_size_pct=99.0),
            portfolio=_base_portfolio(),
            market_mind=_base_market_mind(),
        )
        assert result.approved is True
        assert float(result.adjusted_decision["position_size_pct"]) <= 20.0
        assert len(result.adjustments) > 0

    def test_exposure_cap(self) -> None:
        """当前敞口+新仓位超过总敞口上限时应被调整。"""
        result = apply_risk_checks(
            decision=_base_decision(position_size_pct=20.0),
            portfolio=_base_portfolio(exposure_pct=55.0),
            market_mind=_base_market_mind(),
        )
        assert result.approved is True
        assert float(result.adjusted_decision["position_size_pct"]) <= 5.0

    def test_stop_loss_too_wide(self) -> None:
        """止损距离超过限制时应被调整。"""
        result = apply_risk_checks(
            decision=_base_decision(entry_price=3000.0, stop_loss=2500.0),
            portfolio=_base_portfolio(),
            market_mind=_base_market_mind(),
        )
        assert result.approved is True
        adjusted_sl = float(result.adjusted_decision["stop_loss"])
        assert adjusted_sl > 2500.0

    def test_stop_loss_above_entry_rejected(self) -> None:
        """止损高于入场价的多头决策应被拒绝。"""
        result = apply_risk_checks(
            decision=_base_decision(entry_price=3000.0, stop_loss=3100.0),
            portfolio=_base_portfolio(),
            market_mind=_base_market_mind(),
        )
        assert result.approved is False
        assert any("Stop-loss" in v for v in result.violations)

    def test_daily_loss_limit_blocks(self) -> None:
        """达到日亏损上限时应阻止新开仓。"""
        result = apply_risk_checks(
            decision=_base_decision(),
            portfolio=_base_portfolio(daily_pnl_pct=-5.0),
            market_mind=_base_market_mind(),
        )
        assert result.approved is False
        assert any("daily loss" in v.lower() for v in result.violations)

    def test_dynamic_position_cap_from_mind(self) -> None:
        """Market Mind中的动态仓位限制应生效。"""
        mind = _base_market_mind()
        mind["bias_awareness"] = [
            {"bias": "过度自信", "mitigation": "连续盈利3次后仓位上限自动降低到10%"}
        ]
        result = apply_risk_checks(
            decision=_base_decision(position_size_pct=15.0),
            portfolio=_base_portfolio(),
            market_mind=mind,
        )
        assert float(result.adjusted_decision["position_size_pct"]) <= 10.0

    def test_zero_entry_price_rejected(self) -> None:
        """入场价为0的buy决策应被拒绝。"""
        result = apply_risk_checks(
            decision=_base_decision(entry_price=0.0, stop_loss=0.0),
            portfolio=_base_portfolio(),
            market_mind=_base_market_mind(),
        )
        assert result.approved is False
