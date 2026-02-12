from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.src.config import settings
from backend.src.db.models import Trade


@dataclass
class AccountState:
    cash: float
    position_qty: float
    avg_entry_price: float
    realized_pnl: float
    day_realized_pnl: float


def _rebuild_account_state(db: Session, symbol: str) -> AccountState:
    cash = settings.initial_balance
    position_qty = 0.0
    avg_entry_price = 0.0
    realized_pnl = 0.0
    day_realized_pnl = 0.0
    today = datetime.now(timezone.utc).date()

    rows = db.execute(select(Trade).where(Trade.symbol == symbol).order_by(Trade.timestamp.asc(), Trade.id.asc())).scalars().all()
    for row in rows:
        side = row.side.lower()
        quantity = float(row.quantity)
        price = float(row.price)
        fee = float(row.fee or 0.0)
        slippage = float(row.slippage or 0.0)

        if side == "buy":
            total_cost = quantity * price + fee + slippage
            new_qty = position_qty + quantity
            if new_qty > 0:
                avg_entry_price = ((avg_entry_price * position_qty) + (price * quantity)) / new_qty
            position_qty = new_qty
            cash -= total_cost
        elif side == "sell":
            quantity = min(quantity, position_qty)
            proceeds = quantity * price - fee - slippage
            trade_pnl = (price - avg_entry_price) * quantity - fee - slippage
            realized_pnl += trade_pnl
            cash += proceeds
            position_qty -= quantity
            if position_qty <= 1e-12:
                position_qty = 0.0
                avg_entry_price = 0.0
            if row.timestamp and row.timestamp.date() == today:
                day_realized_pnl += trade_pnl

    return AccountState(
        cash=round(cash, 8),
        position_qty=round(position_qty, 8),
        avg_entry_price=round(avg_entry_price, 8),
        realized_pnl=round(realized_pnl, 8),
        day_realized_pnl=round(day_realized_pnl, 8),
    )


def get_portfolio_snapshot(db: Session, symbol: str, mark_price: float | None) -> dict[str, Any]:
    state = _rebuild_account_state(db=db, symbol=symbol)
    mark = float(mark_price or 0.0)
    unrealized_pnl = (mark - state.avg_entry_price) * state.position_qty if state.position_qty > 0 and mark > 0 else 0.0
    position_value = state.position_qty * mark if mark > 0 else 0.0
    equity = state.cash + position_value
    exposure_pct = (position_value / equity * 100) if equity > 0 else 0.0

    daily_pnl_pct = (state.day_realized_pnl / settings.initial_balance * 100) if settings.initial_balance > 0 else 0.0

    return {
        "balance": round(state.cash, 2),
        "equity": round(equity, 2),
        "available": round(state.cash, 2),
        "exposure_pct": round(exposure_pct, 2),
        "daily_pnl_pct": round(daily_pnl_pct, 2),
        "realized_pnl": round(state.realized_pnl, 2),
        "positions": (
            [
                {
                    "symbol": symbol,
                    "side": "long",
                    "quantity": round(state.position_qty, 8),
                    "entry_price": round(state.avg_entry_price, 2),
                    "mark_price": round(mark, 2),
                    "unrealized_pnl": round(unrealized_pnl, 2),
                }
            ]
            if state.position_qty > 0
            else []
        ),
    }


def execute_decision(db: Session, decision: dict[str, Any], symbol: str, market_price: float) -> dict[str, Any]:
    action = str(decision.get("decision", "hold")).lower()
    state = _rebuild_account_state(db=db, symbol=symbol)
    snapshot = get_portfolio_snapshot(db=db, symbol=symbol, mark_price=market_price)
    equity = float(snapshot["equity"])
    executed_trade: dict[str, Any] | None = None

    if action == "buy":
        position_pct = max(float(decision.get("position_size_pct", 0.0)), 0.0)
        desired_notional = equity * (position_pct / 100)
        buy_notional = min(desired_notional, state.cash)
        execution_price = market_price * (1 + settings.slippage_pct)
        quantity = buy_notional / execution_price if execution_price > 0 else 0.0
        if quantity > 0:
            fee = quantity * execution_price * settings.trading_fee_pct
            slippage = quantity * market_price * settings.slippage_pct
            trade = Trade(
                symbol=symbol,
                side="buy",
                quantity=quantity,
                price=execution_price,
                fee=fee,
                slippage=slippage,
                pnl=0.0,
                notes="executed_by_paper_engine",
            )
            db.add(trade)
            db.commit()
            db.refresh(trade)
            executed_trade = {
                "id": trade.id,
                "side": trade.side,
                "quantity": round(quantity, 8),
                "price": round(execution_price, 2),
                "fee": round(fee, 4),
                "slippage": round(slippage, 4),
            }
    elif action == "sell" and state.position_qty > 0:
        quantity = state.position_qty
        execution_price = market_price * (1 - settings.slippage_pct)
        fee = quantity * execution_price * settings.trading_fee_pct
        slippage = quantity * market_price * settings.slippage_pct
        realized = (execution_price - state.avg_entry_price) * quantity - fee - slippage
        trade = Trade(
            symbol=symbol,
            side="sell",
            quantity=quantity,
            price=execution_price,
            fee=fee,
            slippage=slippage,
            pnl=realized,
            notes="executed_by_paper_engine",
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)
        executed_trade = {
            "id": trade.id,
            "side": trade.side,
            "quantity": round(quantity, 8),
            "price": round(execution_price, 2),
            "fee": round(fee, 4),
            "slippage": round(slippage, 4),
            "realized_pnl": round(realized, 2),
        }

    after = get_portfolio_snapshot(db=db, symbol=symbol, mark_price=market_price)
    return {"executed_trade": executed_trade, "portfolio_before": snapshot, "portfolio_after": after}

