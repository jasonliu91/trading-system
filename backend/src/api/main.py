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
from backend.src.db.database import get_db
from backend.src.db.init_db import init_db
from backend.src.db.models import Decision, MarketMindHistory
from backend.src.mind.market_mind import (
    inject_to_prompt,
    load as load_market_mind,
    save as save_market_mind,
    update as update_market_mind,
)

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


def _mock_klines(timeframe: str, limit: int) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    step = {"1h": timedelta(hours=1), "4h": timedelta(hours=4), "1d": timedelta(days=1)}.get(timeframe, timedelta(hours=1))
    klines = []
    base_price = 3200.0
    for index in range(limit):
        open_time = now - step * (limit - index)
        open_price = base_price + index * 2.0
        close_price = open_price + ((index % 3) - 1) * 3.0
        high_price = max(open_price, close_price) + 4.0
        low_price = min(open_price, close_price) - 4.0
        klines.append(
            {
                "symbol": "ETHUSDT",
                "timeframe": timeframe,
                "open_time": open_time.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": round(1500 + index * 12.5, 2),
            }
        )
    return klines


def _serialize_decision(row: Decision) -> dict[str, Any]:
    try:
        reasoning = json.loads(row.reasoning_json)
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


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    load_market_mind()


@app.get("/api/system/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/klines")
def get_klines(
    timeframe: str = Query(default="1d"),
    limit: int = Query(default=90, ge=1, le=500),
) -> dict[str, Any]:
    if timeframe not in {"1h", "4h", "1d"}:
        raise HTTPException(status_code=400, detail="timeframe must be one of: 1h, 4h, 1d")
    return {"items": _mock_klines(timeframe=timeframe, limit=limit)}


@app.get("/api/portfolio")
def get_portfolio() -> dict[str, Any]:
    return {
        "balance": 10000.0,
        "equity": 10180.5,
        "available": 8120.2,
        "exposure_pct": 18.9,
        "positions": [
            {
                "symbol": "ETHUSDT",
                "side": "long",
                "quantity": 0.45,
                "entry_price": 3188.0,
                "mark_price": 3225.0,
                "unrealized_pnl": 16.65,
                "stop_loss": 3075.0,
                "take_profit": 3390.0,
            }
        ],
    }


@app.get("/api/decisions")
def get_decisions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    offset = (page - 1) * limit
    rows = db.execute(select(Decision).order_by(Decision.timestamp.desc()).offset(offset).limit(limit)).scalars().all()
    if rows:
        return {"items": [_serialize_decision(row) for row in rows], "page": page, "limit": limit}
    mock_item = {
        "id": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": "hold",
        "position_size_pct": 0.0,
        "entry_price": 0.0,
        "stop_loss": 0.0,
        "take_profit": 0.0,
        "confidence": 0.62,
        "reasoning": {
            "mind_alignment": "当前偏震荡，等待突破后再行动",
            "bias_check": "检查了过度乐观偏误，未触发开仓条件",
        },
        "model_used": "claude-sonnet-4-5-20250929",
        "input_hash": "mock-input-hash",
    }
    return {"items": [mock_item], "page": page, "limit": limit}


@app.get("/api/decisions/{decision_id}")
def get_decision_detail(decision_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.get(Decision, decision_id)
    if row is not None:
        return _serialize_decision(row)
    if decision_id == 1:
        return {
            "id": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": "hold",
            "position_size_pct": 0.0,
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "confidence": 0.62,
            "reasoning": {
                "market_regime": "ranging",
                "mind_alignment": "符合Market Mind中震荡期降低频繁交易的偏好",
                "bias_check": "检查偏误: 大跌抄底倾向，本次未逆势操作",
                "final_logic": "趋势不明确，继续等待",
            },
            "model_used": "claude-sonnet-4-5-20250929",
            "input_hash": "mock-input-hash",
        }
    raise HTTPException(status_code=404, detail="Decision not found")


@app.get("/api/performance")
def get_performance() -> dict[str, Any]:
    return {
        "equity_curve": [
            {"date": "2025-02-10", "equity": 10000.0},
            {"date": "2025-02-11", "equity": 10088.3},
            {"date": "2025-02-12", "equity": 10180.5},
        ],
        "metrics": {
            "total_return_pct": 1.8,
            "max_drawdown_pct": -0.9,
            "win_rate": 0.56,
            "profit_factor": 1.22,
        },
    }


@app.get("/api/signals")
def get_signals() -> dict[str, Any]:
    return {
        "items": [
            {"strategy_name": "ema_adx_daily", "signal": "buy", "strength": 0.71},
            {"strategy_name": "supertrend_daily", "signal": "hold", "strength": 0.53},
            {"strategy_name": "donchian_daily", "signal": "buy", "strength": 0.67},
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
def get_system_status() -> dict[str, Any]:
    return {
        "trading": "running",
        "scheduler": "running",
        "data_pipeline": "running",
        "agent": "not_configured",
        "analysis_interval_hours": settings.analysis_interval_hours,
    }


@app.post("/api/system/trigger-analysis")
def trigger_analysis() -> dict[str, str]:
    return {"status": "accepted", "message": "Manual analysis trigger queued"}


@app.post("/api/system/pause")
def pause_system() -> dict[str, str]:
    return {"status": "ok", "message": "Trading paused (mock)"}


@app.post("/api/system/resume")
def resume_system() -> dict[str, str]:
    return {"status": "ok", "message": "Trading resumed (mock)"}


@app.post("/api/config/update")
def update_config(payload: ConfigUpdateRequest) -> dict[str, Any]:
    applied = payload.model_dump(exclude_none=True) if hasattr(payload, "model_dump") else payload.dict(exclude_none=True)
    return {"status": "accepted", "applied": applied}


@app.get("/api/summary/daily")
def daily_summary() -> dict[str, Any]:
    return {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "summary": "今日策略以观望为主，等待关键阻力位突破。",
    }


@app.get("/api/summary/weekly")
def weekly_summary() -> dict[str, Any]:
    return {
        "week_start": (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat(),
        "summary": "本周回撤可控，趋势策略表现优于均值回归策略。",
    }


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": "ETHUSDT",
                "price": 3200.0,
                "decision_hint": "hold",
            }
            await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
