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
from backend.src.db.models import Decision, MarketMindHistory, Trade
from backend.src.mind.market_mind import (
    inject_to_prompt,
    load as load_market_mind,
    save as save_market_mind,
    update as update_market_mind,
)
from backend.src.orchestrator.service import run_analysis_cycle, scheduler_status, start_scheduler, stop_scheduler
from backend.src.quant.library import build_quant_snapshot
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
def health_check() -> dict[str, Any]:
    return {"status": "ok", "service": settings.app_name, "scheduler": scheduler_status()}


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
    mark_price = latest_price_from_db(db=db, symbol=settings.trading_pair) or 0.0
    portfolio = get_portfolio_snapshot(db=db, symbol=settings.trading_pair, mark_price=mark_price)
    sells = db.execute(select(Trade).where(Trade.symbol == settings.trading_pair, Trade.side == "sell")).scalars().all()
    win_count = sum(1 for row in sells if float(row.pnl or 0.0) > 0)
    win_rate = (win_count / len(sells)) if sells else 0.0

    total_return_pct = (
        (float(portfolio["equity"]) - settings.initial_balance) / settings.initial_balance * 100
        if settings.initial_balance > 0
        else 0.0
    )

    equity_curve = [
        {
            "date": (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat(),
            "equity": round(settings.initial_balance, 2),
        },
        {"date": datetime.now(timezone.utc).date().isoformat(), "equity": round(float(portfolio["equity"]), 2)},
    ]

    return {
        "equity_curve": equity_curve,
        "metrics": {
            "total_return_pct": round(total_return_pct, 2),
            "max_drawdown_pct": 0.0,
            "win_rate": round(win_rate, 4),
            "profit_factor": 0.0,
        },
    }


@app.get("/api/signals")
def get_signals(
    timeframe: str = Query(default="1d"),
    limit: int = Query(default=120, ge=30, le=500),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if timeframe not in {"1h", "4h", "1d"}:
        raise HTTPException(status_code=400, detail="timeframe must be one of: 1h, 4h, 1d")

    klines = get_recent_klines(db=db, symbol=settings.trading_pair, timeframe=timeframe, limit=limit)
    source = "database"
    if not klines:
        klines = fallback_mock_klines(timeframe=timeframe, limit=limit, symbol=settings.trading_pair)
        source = "mock_fallback"

    snapshot = build_quant_snapshot(symbol=settings.trading_pair, timeframe=timeframe, klines=klines)
    return {"items": snapshot["signals"], "summary": snapshot["summary"], "source": source}


@app.get("/api/mind")
def get_market_mind() -> dict[str, Any]:
    market_mind = load_market_mind()
    return {
        "market_mind": market_mind,
        "prompt_preview": inject_to_prompt(market_mind),
    }


@app.put("/api/mind")
def put_market_mind(payload: MindUpdateRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    if payload.market_mind is not None:
        saved = save_market_mind(
            market_mind=payload.market_mind,
            changed_by=payload.changed_by,
            db=db,
            change_summary=payload.change_summary,
        )
        return {"market_mind": saved, "mode": "replace"}
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
