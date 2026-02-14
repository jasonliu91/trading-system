"""模拟交易引擎单元测试。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.src.db.models import Trade
from backend.src.trading.paper_engine import (
    AccountState,
    _rebuild_account_state,
    execute_decision,
    get_portfolio_snapshot,
)


def _add_trade(db: Session, side: str, quantity: float, price: float, pnl: float = 0.0) -> Trade:
    """向测试数据库添加一笔交易记录。"""
    trade = Trade(
        symbol="ETHUSDT",
        side=side,
        quantity=quantity,
        price=price,
        fee=0.01,
        slippage=0.005,
        pnl=pnl,
        notes="test_trade",
        timestamp=datetime.now(timezone.utc),
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


class TestRebuildAccountState:
    """账户状态重建测试。"""

    def test_empty_account(self, db: Session) -> None:
        """无交易记录时应返回初始余额。"""
        state = _rebuild_account_state(db=db, symbol="ETHUSDT")
        assert state.cash > 0
        assert state.position_qty == 0.0
        assert state.realized_pnl == 0.0

    def test_single_buy(self, db: Session) -> None:
        """单笔买入后应持有仓位。"""
        _add_trade(db, "buy", quantity=1.0, price=3000.0)
        state = _rebuild_account_state(db=db, symbol="ETHUSDT")
        assert state.position_qty > 0
        assert state.cash < 10000.0  # 初始余额

    def test_buy_then_sell(self, db: Session) -> None:
        """买入后全部卖出，仓位应归零。"""
        _add_trade(db, "buy", quantity=1.0, price=3000.0)
        _add_trade(db, "sell", quantity=1.0, price=3100.0, pnl=100.0)
        state = _rebuild_account_state(db=db, symbol="ETHUSDT")
        assert state.position_qty == 0.0
        assert state.realized_pnl > 0


class TestGetPortfolioSnapshot:
    """投资组合快照测试。"""

    def test_empty_portfolio(self, db: Session) -> None:
        """空仓状态应返回初始余额。"""
        snapshot = get_portfolio_snapshot(db=db, symbol="ETHUSDT", mark_price=3000.0)
        assert snapshot["balance"] > 0
        assert snapshot["positions"] == []
        assert snapshot["exposure_pct"] == 0.0

    def test_with_position(self, db: Session) -> None:
        """持仓状态应显示持仓详情和敞口。"""
        _add_trade(db, "buy", quantity=1.0, price=3000.0)
        snapshot = get_portfolio_snapshot(db=db, symbol="ETHUSDT", mark_price=3200.0)
        assert len(snapshot["positions"]) == 1
        assert snapshot["positions"][0]["unrealized_pnl"] > 0
        assert snapshot["exposure_pct"] > 0

    def test_unrealized_pnl_loss(self, db: Session) -> None:
        """价格下跌时未实现盈亏应为负。"""
        _add_trade(db, "buy", quantity=1.0, price=3000.0)
        snapshot = get_portfolio_snapshot(db=db, symbol="ETHUSDT", mark_price=2800.0)
        assert snapshot["positions"][0]["unrealized_pnl"] < 0


class TestExecuteDecision:
    """交易执行测试。"""

    def test_buy_creates_trade(self, db: Session) -> None:
        """buy决策应创建买入交易记录。"""
        result = execute_decision(
            db=db,
            decision={"decision": "buy", "position_size_pct": 10.0},
            symbol="ETHUSDT",
            market_price=3000.0,
        )
        assert result["executed_trade"] is not None
        assert result["executed_trade"]["side"] == "buy"

    def test_sell_with_position(self, db: Session) -> None:
        """持仓时sell决策应平仓。"""
        _add_trade(db, "buy", quantity=1.0, price=3000.0)
        result = execute_decision(
            db=db,
            decision={"decision": "sell"},
            symbol="ETHUSDT",
            market_price=3200.0,
        )
        assert result["executed_trade"] is not None
        assert result["executed_trade"]["side"] == "sell"

    def test_sell_without_position(self, db: Session) -> None:
        """无持仓时sell决策不应执行交易。"""
        result = execute_decision(
            db=db,
            decision={"decision": "sell"},
            symbol="ETHUSDT",
            market_price=3000.0,
        )
        assert result["executed_trade"] is None

    def test_hold_no_trade(self, db: Session) -> None:
        """hold决策不应执行任何交易。"""
        result = execute_decision(
            db=db,
            decision={"decision": "hold"},
            symbol="ETHUSDT",
            market_price=3000.0,
        )
        assert result["executed_trade"] is None

    def test_portfolio_before_after(self, db: Session) -> None:
        """执行结果应包含交易前后的投资组合快照。"""
        result = execute_decision(
            db=db,
            decision={"decision": "buy", "position_size_pct": 10.0},
            symbol="ETHUSDT",
            market_price=3000.0,
        )
        assert "portfolio_before" in result
        assert "portfolio_after" in result
