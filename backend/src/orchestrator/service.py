from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.src.ai.decision_engine import DecisionContext, generate_decision
from backend.src.config import settings
from backend.src.data.binance_client import BinanceAPIError
from backend.src.data.kline_service import fetch_and_store_klines, get_recent_klines, latest_price_from_db, maybe_backfill_initial_klines
from backend.src.db.database import SessionLocal
from backend.src.db.models import Decision
from backend.src.mind.market_mind import load as load_market_mind
from backend.src.quant.library import build_quant_snapshot
from backend.src.risk.engine import apply_risk_checks
from backend.src.trading.paper_engine import execute_decision, get_portfolio_snapshot

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover
    BackgroundScheduler = None  # type: ignore[assignment]

scheduler: Any = None

# 调度器运行状态追踪
_last_cycle_at: datetime | None = None
_consecutive_failures: int = 0


def _load_recent_decisions(db: Session, limit: int = 5) -> list[dict[str, Any]]:
    """从数据库加载最近N条决策记录，用于提供给AI作为上下文。"""
    rows = db.execute(select(Decision).order_by(Decision.timestamp.desc()).limit(limit)).scalars().all()
    items: list[dict[str, Any]] = []
    for row in reversed(rows):
        try:
            reasoning = json.loads(row.reasoning_json) if row.reasoning_json else {}
        except json.JSONDecodeError:
            reasoning = {"raw": row.reasoning_json}
        items.append(
            {
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
        )
    return items


def _sync_latest_klines(db: Session, symbol: str) -> dict[str, Any]:
    """同步最新K线数据，包括首次回填和增量更新，记录各阶段错误。"""
    updates: dict[str, Any] = {"initial_backfill": {}, "incremental": {}, "errors": []}
    try:
        updates["initial_backfill"] = maybe_backfill_initial_klines(db=db, symbol=symbol)
    except BinanceAPIError as exc:
        logger.warning("K线初始回填失败: %s", exc)
        updates["errors"].append(f"backfill: {exc}")

    for timeframe, limit in {"1h": 200, "4h": 120, "1d": 90}.items():
        try:
            updates["incremental"][timeframe] = fetch_and_store_klines(
                db=db,
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
            )
        except BinanceAPIError as exc:
            logger.warning("K线增量更新失败 (%s): %s", timeframe, exc)
            updates["errors"].append(f"{timeframe}: {exc}")
    return updates


def run_analysis_cycle(db: Session, source: str = "scheduler") -> dict[str, Any]:
    """
    执行完整的分析周期: 数据同步 → AI决策 → 风控检查 → 交易执行。

    每个阶段独立捕获异常并记录日志，确保单阶段失败不会中断整个流程。
    """
    global _last_cycle_at, _consecutive_failures
    cycle_start = time.monotonic()
    symbol = settings.trading_pair

    logger.info("开始分析周期 [来源=%s, 品种=%s]", source, symbol)

    # 阶段1: 数据同步
    sync_status = _sync_latest_klines(db=db, symbol=symbol)
    if sync_status["errors"]:
        logger.warning("数据同步有错误: %s", sync_status["errors"])

    # 阶段2: 构建决策上下文
    daily_klines = get_recent_klines(db=db, symbol=symbol, timeframe="1d", limit=120)
    hourly_klines = get_recent_klines(db=db, symbol=symbol, timeframe="1h", limit=24)
    quant_snapshot = build_quant_snapshot(symbol=symbol, timeframe="1d", klines=daily_klines)
    market_price = latest_price_from_db(db=db, symbol=symbol) or 0.0

    if market_price <= 0:
        logger.warning("无法获取市场价格，跳过本次分析周期")
        _consecutive_failures += 1
        return {
            "source": source,
            "symbol": symbol,
            "sync_status": sync_status,
            "market_price": 0.0,
            "error": "无法获取市场价格",
            "skipped": True,
        }

    portfolio = get_portfolio_snapshot(db=db, symbol=symbol, mark_price=market_price)
    market_mind = load_market_mind()
    recent_decisions = _load_recent_decisions(db=db, limit=5)

    # 阶段3: 生成决策
    decision_payload = generate_decision(
        DecisionContext(
            market_mind=market_mind,
            daily_klines=daily_klines,
            hourly_klines=hourly_klines,
            quant_signals=quant_snapshot["signals"],
            portfolio=portfolio,
            recent_decisions=recent_decisions,
        )
    )

    # 阶段4: 风控检查
    risk_result = apply_risk_checks(
        decision=decision_payload,
        portfolio=portfolio,
        market_mind=market_mind,
    )

    final_decision = dict(risk_result.adjusted_decision)
    final_decision.setdefault("reasoning", {})
    final_decision["reasoning"]["risk_check"] = {
        "approved": risk_result.approved,
        "violations": risk_result.violations,
        "adjustments": risk_result.adjustments,
    }

    if risk_result.violations:
        logger.info("风控违规: %s", risk_result.violations)
    if risk_result.adjustments:
        logger.info("风控调整: %s", risk_result.adjustments)

    # 阶段5: 执行交易
    trade_result = {"executed_trade": None, "portfolio_before": portfolio, "portfolio_after": portfolio}
    if risk_result.approved and market_price > 0:
        try:
            trade_result = execute_decision(db=db, decision=final_decision, symbol=symbol, market_price=market_price)
            if trade_result.get("executed_trade"):
                logger.info(
                    "交易执行成功: %s %s @ %.2f",
                    trade_result["executed_trade"]["side"],
                    symbol,
                    trade_result["executed_trade"]["price"],
                )
        except Exception as exc:
            logger.error("交易执行失败: %s", exc)
            trade_result["error"] = str(exc)

    # 阶段6: 持久化决策记录
    decision_row = Decision(
        timestamp=datetime.now(timezone.utc),
        decision=final_decision["decision"],
        position_size_pct=float(final_decision.get("position_size_pct", 0.0)),
        entry_price=float(final_decision.get("entry_price", 0.0)),
        stop_loss=float(final_decision.get("stop_loss", 0.0)),
        take_profit=float(final_decision.get("take_profit", 0.0)),
        confidence=float(final_decision.get("confidence", 0.0)),
        reasoning_json=json.dumps(final_decision.get("reasoning", {}), ensure_ascii=False),
        model_used=str(final_decision.get("model_used", settings.ai_model)),
        input_hash=str(final_decision.get("input_hash", "")),
    )
    db.add(decision_row)
    db.commit()
    db.refresh(decision_row)

    elapsed = time.monotonic() - cycle_start
    _last_cycle_at = datetime.now(timezone.utc)
    _consecutive_failures = 0
    logger.info("分析周期完成 [决策=%s, 耗时=%.2fs]", final_decision["decision"], elapsed)

    return {
        "source": source,
        "symbol": symbol,
        "sync_status": sync_status,
        "market_price": market_price,
        "quant_snapshot": quant_snapshot,
        "decision_id": decision_row.id,
        "decision": final_decision,
        "risk_result": {
            "approved": risk_result.approved,
            "violations": risk_result.violations,
            "adjustments": risk_result.adjustments,
        },
        "trade_result": trade_result,
        "elapsed_sec": round(elapsed, 2),
    }


def run_analysis_cycle_with_new_session(source: str = "scheduler") -> dict[str, Any]:
    """使用独立数据库会话执行分析周期，确保异常时正确关闭连接。"""
    global _consecutive_failures
    db = SessionLocal()
    try:
        return run_analysis_cycle(db=db, source=source)
    except Exception as exc:
        _consecutive_failures += 1
        logger.error(
            "分析周期异常 (连续失败=%d): %s", _consecutive_failures, exc, exc_info=True,
        )
        return {"source": source, "error": str(exc), "consecutive_failures": _consecutive_failures}
    finally:
        db.close()


def start_scheduler() -> dict[str, Any]:
    """启动定时分析调度器。"""
    global scheduler
    if not settings.scheduler_enabled:
        return {"status": "disabled", "reason": "SCHEDULER_ENABLED=false"}

    if BackgroundScheduler is None:
        return {"status": "unavailable", "reason": "apscheduler is not installed"}

    if scheduler is not None and getattr(scheduler, "running", False):
        return {"status": "running"}

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_analysis_cycle_with_new_session,
        trigger="interval",
        hours=max(1, settings.analysis_interval_hours),
        id="analysis-cycle",
        replace_existing=True,
        kwargs={"source": "scheduler"},
    )
    scheduler.start()
    logger.info("调度器已启动, 间隔=%s小时", settings.analysis_interval_hours)
    return {"status": "running", "interval_hours": settings.analysis_interval_hours}


def stop_scheduler() -> dict[str, Any]:
    """停止定时分析调度器。"""
    global scheduler
    if scheduler is None:
        return {"status": "stopped"}
    if getattr(scheduler, "running", False):
        scheduler.shutdown(wait=False)
    scheduler = None
    logger.info("调度器已停止")
    return {"status": "stopped"}


def scheduler_status() -> dict[str, Any]:
    """获取调度器运行状态，包含最近周期时间和连续失败次数。"""
    status = "stopped"
    if scheduler is not None and getattr(scheduler, "running", False):
        status = "running"
    return {
        "status": status,
        "last_cycle_at": _last_cycle_at.isoformat() if _last_cycle_at else None,
        "consecutive_failures": _consecutive_failures,
    }
