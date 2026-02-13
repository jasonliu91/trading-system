from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.src.config import settings
from backend.src.data.binance_client import BinanceAPIError
from backend.src.data.kline_service import (
    fallback_mock_klines,
    fetch_and_store_klines,
    get_recent_klines,
    latest_price_from_db,
)
from backend.src.db.database import SessionLocal, get_db
from backend.src.db.init_db import init_db
from backend.src.db.models import Decision, Kline, MarketMindHistory, Trade
from backend.src.mind.market_mind import (
    inject_to_prompt,
    load as load_market_mind,
    save as save_market_mind,
    update as update_market_mind,
    validate_market_mind,
)
from backend.src.orchestrator.service import run_analysis_cycle, scheduler_status, start_scheduler, stop_scheduler
from backend.src.trading.paper_engine import get_portfolio_snapshot

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MindUpdateRequest(BaseModel):
    market_mind: dict[str, Any] | None = None
    patch: dict[str, Any] | None = None
    changed_by: str = "api_user"
    change_summary: str | None = None


class ConfigUpdateRequest(BaseModel):
    analysis_interval_hours: int | None = None
    max_position_pct: float | None = None
    max_exposure_pct: float | None = None
    max_daily_loss_pct: float | None = None
    scheduler_enabled: bool | None = None


def _serialize_decision(row: Decision) -> dict[str, Any]:
    try:
        reasoning = json.loads(row.reasoning_json) if row.reasoning_json else {}
    except json.JSONDecodeError:
        reasoning = {"raw": row.reasoning_json}
    return {
        "id": row.id,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        "decision": row.decision,
        "position_size_pct": row.position_size_pct,
        "entry_price": row.entry_price,
        "stop_loss": row.stop_loss,
        "take_profit": row.take_profit,
        "confidence": row.confidence,
        "reasoning": reasoning,
        "model_used": row.model_used,
        "input_hash": row.input_hash,
    }


def _serialize_trade(row: Trade) -> dict[str, Any]:
    return {
        "id": row.id,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        "symbol": row.symbol,
        "side": row.side,
        "quantity": row.quantity,
        "price": row.price,
        "fee": row.fee,
        "slippage": row.slippage,
        "pnl": row.pnl,
        "notes": row.notes,
    }


def _latest_decision(db: Session) -> Decision | None:
    return db.execute(select(Decision).order_by(Decision.timestamp.desc(), Decision.id.desc()).limit(1)).scalars().first()


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    load_market_mind()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/api/system/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, Any]:
    """详细健康检查，验证数据库连接、数据新鲜度和调度器状态。"""
    checks: dict[str, Any] = {}

    # 数据库连接检查
    try:
        db.execute(select(Decision).limit(1))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # 数据新鲜度检查
    latest_kline = db.execute(
        select(Kline).where(Kline.symbol == settings.trading_pair).order_by(Kline.open_time.desc()).limit(1)
    ).scalars().first()
    if latest_kline and latest_kline.open_time:
        age_hours = (datetime.now(timezone.utc) - latest_kline.open_time).total_seconds() / 3600
        checks["data_freshness"] = {
            "latest_kline_age_hours": round(age_hours, 1),
            "stale": age_hours > 6,
        }
    else:
        checks["data_freshness"] = {"latest_kline_age_hours": None, "stale": True}

    sched = scheduler_status()
    overall = "ok" if checks["database"] == "ok" and sched.get("status") != "error" else "degraded"

    return {
        "status": overall,
        "service": settings.app_name,
        "version": settings.app_version,
        "scheduler": sched,
        "checks": checks,
    }


@app.get("/api/klines")
def get_klines(
    timeframe: str = Query(default="1d"),
    limit: int = Query(default=90, ge=1, le=500),
    refresh: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if timeframe not in {"1h", "4h", "1d"}:
        raise HTTPException(status_code=400, detail="timeframe must be one of: 1h, 4h, 1d")

    refresh_result: dict[str, Any] = {"requested": refresh}
    if refresh:
        try:
            count = fetch_and_store_klines(
                db=db,
                symbol=settings.trading_pair,
                timeframe=timeframe,
                limit=max(limit, 60),
            )
            refresh_result["stored"] = count
        except BinanceAPIError as exc:
            refresh_result["error"] = str(exc)

    items = get_recent_klines(db=db, symbol=settings.trading_pair, timeframe=timeframe, limit=limit)
    source = "database"
    if not items:
        items = fallback_mock_klines(timeframe=timeframe, limit=limit, symbol=settings.trading_pair)
        source = "mock_fallback"

    return {"items": items, "source": source, "refresh": refresh_result}


@app.get("/api/portfolio")
def get_portfolio(db: Session = Depends(get_db)) -> dict[str, Any]:
    mark_price = latest_price_from_db(db=db, symbol=settings.trading_pair) or 0.0
    snapshot = get_portfolio_snapshot(db=db, symbol=settings.trading_pair, mark_price=mark_price)
    snapshot["symbol"] = settings.trading_pair
    snapshot["mark_price"] = round(mark_price, 2)
    return snapshot


@app.get("/api/decisions")
def get_decisions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    offset = (page - 1) * limit
    rows = db.execute(select(Decision).order_by(Decision.timestamp.desc(), Decision.id.desc()).offset(offset).limit(limit)).scalars().all()
    return {"items": [_serialize_decision(row) for row in rows], "page": page, "limit": limit}


@app.get("/api/decisions/{decision_id}")
def get_decision_detail(decision_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.get(Decision, decision_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return _serialize_decision(row)


@app.get("/api/trades")
def get_trades(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    offset = (page - 1) * limit
    rows = db.execute(select(Trade).order_by(Trade.timestamp.desc(), Trade.id.desc()).offset(offset).limit(limit)).scalars().all()
    return {"items": [_serialize_trade(row) for row in rows], "page": page, "limit": limit}


@app.get("/api/performance")
def get_performance(db: Session = Depends(get_db)) -> dict[str, Any]:
    """计算真实的绩效指标，包括权益曲线、最大回撤、胜率和盈亏比。"""
    mark_price = latest_price_from_db(db=db, symbol=settings.trading_pair) or 0.0
    portfolio = get_portfolio_snapshot(db=db, symbol=settings.trading_pair, mark_price=mark_price)

    # 获取所有交易记录，按时间排序
    all_trades = db.execute(
        select(Trade).where(Trade.symbol == settings.trading_pair).order_by(Trade.timestamp.asc())
    ).scalars().all()

    # 构建真实权益曲线（基于每笔交易后的权益变化）
    equity_curve: list[dict[str, Any]] = []
    running_equity = settings.initial_balance
    seen_dates: set[str] = set()

    # 起始点
    if all_trades and all_trades[0].timestamp:
        start_date = (all_trades[0].timestamp.date() - timedelta(days=1)).isoformat()
    else:
        start_date = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    equity_curve.append({"date": start_date, "equity": round(settings.initial_balance, 2)})
    seen_dates.add(start_date)

    for trade in all_trades:
        pnl = float(trade.pnl or 0.0)
        fee = float(trade.fee or 0.0)
        if trade.side == "sell":
            running_equity += pnl
        else:
            running_equity -= fee

        if trade.timestamp:
            date_key = trade.timestamp.date().isoformat()
            if date_key not in seen_dates:
                equity_curve.append({"date": date_key, "equity": round(running_equity, 2)})
                seen_dates.add(date_key)
            else:
                # 更新当天最后一个值
                for point in reversed(equity_curve):
                    if point["date"] == date_key:
                        point["equity"] = round(running_equity, 2)
                        break

    # 添加当前权益
    today_key = datetime.now(timezone.utc).date().isoformat()
    current_equity = float(portfolio["equity"])
    if today_key not in seen_dates:
        equity_curve.append({"date": today_key, "equity": round(current_equity, 2)})
    else:
        for point in reversed(equity_curve):
            if point["date"] == today_key:
                point["equity"] = round(current_equity, 2)
                break

    # 计算最大回撤
    max_drawdown_pct = 0.0
    peak_equity = settings.initial_balance
    for point in equity_curve:
        eq = point["equity"]
        if eq > peak_equity:
            peak_equity = eq
        if peak_equity > 0:
            drawdown = (peak_equity - eq) / peak_equity * 100
            max_drawdown_pct = max(max_drawdown_pct, drawdown)

    # 计算胜率和盈亏比
    sells = [t for t in all_trades if t.side == "sell"]
    win_count = sum(1 for t in sells if float(t.pnl or 0.0) > 0)
    win_rate = (win_count / len(sells)) if sells else 0.0

    total_profit = sum(float(t.pnl) for t in sells if float(t.pnl or 0.0) > 0)
    total_loss = abs(sum(float(t.pnl) for t in sells if float(t.pnl or 0.0) < 0))
    profit_factor = (total_profit / total_loss) if total_loss > 0 else (float("inf") if total_profit > 0 else 0.0)

    total_return_pct = (
        (current_equity - settings.initial_balance) / settings.initial_balance * 100
        if settings.initial_balance > 0
        else 0.0
    )

    return {
        "equity_curve": equity_curve,
        "metrics": {
            "total_return_pct": round(total_return_pct, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "Inf",
            "total_trades": len(sells),
            "winning_trades": win_count,
            "losing_trades": len(sells) - win_count,
        },
    }


@app.get("/api/signals")
def get_signals() -> dict[str, Any]:
    return {
        "items": [
            {"strategy_name": "ema_adx_daily", "signal": "pending_phase2", "strength": 0.0},
            {"strategy_name": "supertrend_daily", "signal": "pending_phase2", "strength": 0.0},
            {"strategy_name": "donchian_daily", "signal": "pending_phase2", "strength": 0.0},
        ]
    }


@app.get("/api/mind")
def get_market_mind() -> dict[str, Any]:
    market_mind = load_market_mind()
    return {
        "market_mind": market_mind,
        "prompt_preview": inject_to_prompt(market_mind),
    }


@app.put("/api/mind")
def put_market_mind(payload: MindUpdateRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """更新Market Mind，支持完整替换和增量合并两种模式。"""
    if payload.market_mind is not None:
        warnings = validate_market_mind(payload.market_mind)
        saved = save_market_mind(
            market_mind=payload.market_mind,
            changed_by=payload.changed_by,
            db=db,
            change_summary=payload.change_summary,
        )
        result: dict[str, Any] = {"market_mind": saved, "mode": "replace"}
        if warnings:
            result["validation_warnings"] = warnings
        return result
    if payload.patch is not None:
        saved = update_market_mind(
            patch=payload.patch,
            changed_by=payload.changed_by,
            db=db,
            change_summary=payload.change_summary,
        )
        return {"market_mind": saved, "mode": "merge"}
    raise HTTPException(status_code=400, detail="Provide either market_mind or patch")


@app.get("/api/mind/history")
def get_market_mind_history(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = db.execute(select(MarketMindHistory).order_by(MarketMindHistory.changed_at.desc()).limit(limit)).scalars().all()
    items = [
        {
            "id": row.id,
            "changed_at": row.changed_at.isoformat() if row.changed_at else None,
            "changed_by": row.changed_by,
            "change_summary": row.change_summary,
            "previous_state": json.loads(row.previous_state),
            "new_state": json.loads(row.new_state),
        }
        for row in rows
    ]
    return {"items": items}


@app.get("/api/system/status")
def get_system_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    latest = _latest_decision(db)
    return {
        "trading": "running",
        "scheduler": scheduler_status(),
        "data_pipeline": "running",
        "agent": "not_configured",
        "analysis_interval_hours": settings.analysis_interval_hours,
        "last_decision_at": latest.timestamp.isoformat() if latest and latest.timestamp else None,
    }


@app.post("/api/system/trigger-analysis")
def trigger_analysis(db: Session = Depends(get_db)) -> dict[str, Any]:
    result = run_analysis_cycle(db=db, source="manual_api")
    return {"status": "completed", "result": result}


@app.post("/api/system/pause")
def pause_system() -> dict[str, Any]:
    return {"status": "ok", "scheduler": stop_scheduler(), "message": "Trading scheduler paused"}


@app.post("/api/system/resume")
def resume_system() -> dict[str, Any]:
    return {"status": "ok", "scheduler": start_scheduler(), "message": "Trading scheduler resumed"}


@app.post("/api/config/update")
def update_config(payload: ConfigUpdateRequest) -> dict[str, Any]:
    applied = payload.model_dump(exclude_none=True) if hasattr(payload, "model_dump") else payload.dict(exclude_none=True)
    return {
        "status": "accepted",
        "applied": applied,
        "note": "Runtime env values are not mutated yet; persisted config update is pending Phase 1 system module.",
    }


@app.get("/api/summary/daily")
def daily_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    latest = _latest_decision(db)
    if latest is None:
        summary = "今日尚无决策。"
    else:
        summary = f"最新决策: {latest.decision}，置信度 {latest.confidence:.2f}。"
    return {"date": datetime.now(timezone.utc).date().isoformat(), "summary": summary}


@app.get("/api/summary/weekly")
def weekly_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = (
        db.execute(
            select(Decision).where(Decision.timestamp >= datetime.now(timezone.utc) - timedelta(days=7)).order_by(Decision.timestamp.desc())
        )
        .scalars()
        .all()
    )
    buys = sum(1 for row in rows if row.decision == "buy")
    sells = sum(1 for row in rows if row.decision == "sell")
    holds = sum(1 for row in rows if row.decision == "hold")
    summary = f"近7天决策共{len(rows)}次，buy={buys}, sell={sells}, hold={holds}。"
    return {"week_start": (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat(), "summary": summary}


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            db = SessionLocal()
            try:
                price = latest_price_from_db(db=db, symbol=settings.trading_pair) or 0.0
                latest = _latest_decision(db)
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "symbol": settings.trading_pair,
                    "price": round(price, 2),
                    "latest_decision": latest.decision if latest else None,
                    "latest_decision_id": latest.id if latest else None,
                }
            finally:
                db.close()

            await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
