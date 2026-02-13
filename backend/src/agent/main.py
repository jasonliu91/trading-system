from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from backend.src.agent.api_client import APIClientError, BackendAPIClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
logger = logging.getLogger(__name__)

api_client = BackendAPIClient()


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_num(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "N/A"


async def _send_error(update: Update, exc: Exception) -> None:
    logger.exception("Agent handler failed: %s", exc)
    if update.message:
        await update.message.reply_text(f"请求失败: {exc}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message:
        return
    await update.message.reply_text(
        "Overseer Agent 在线。\n"
        "可用命令:\n"
        "/status 系统状态\n"
        "/portfolio 持仓与账户\n"
        "/performance 绩效\n"
        "/decision 最新决策\n"
        "/mind 市场观点摘要\n"
        "/analyze 触发一次分析\n"
        "/pause 暂停调度\n"
        "/resume 恢复调度\n"
        "/view <你的观点> 写入 Market Mind user_inputs"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message:
        return
    try:
        payload = api_client.get_system_status()
        await update.message.reply_text(
            "系统状态\n"
            f"- trading: {payload.get('trading')}\n"
            f"- scheduler: {payload.get('scheduler')}\n"
            f"- data_pipeline: {payload.get('data_pipeline')}\n"
            f"- interval_h: {payload.get('analysis_interval_hours')}\n"
            f"- last_decision_at: {payload.get('last_decision_at')}"
        )
    except Exception as exc:
        await _send_error(update, exc)


async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message:
        return
    try:
        payload = api_client.get_portfolio()
        positions = payload.get("positions", [])
        position_text = "无持仓"
        if isinstance(positions, list) and positions:
            first = positions[0]
            if isinstance(first, dict):
                position_text = (
                    f"{first.get('symbol')} qty={_fmt_num(first.get('quantity'))} "
                    f"entry={_fmt_num(first.get('entry_price'))} "
                    f"mark={_fmt_num(first.get('mark_price'))} "
                    f"uPnL={_fmt_num(first.get('unrealized_pnl'))}"
                )

        await update.message.reply_text(
            "账户快照\n"
            f"- equity: {_fmt_num(payload.get('equity'))}\n"
            f"- balance: {_fmt_num(payload.get('balance'))}\n"
            f"- exposure: {_fmt_pct(payload.get('exposure_pct'))}\n"
            f"- daily_pnl_pct: {_fmt_pct(payload.get('daily_pnl_pct'))}\n"
            f"- position: {position_text}"
        )
    except Exception as exc:
        await _send_error(update, exc)


async def cmd_performance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message:
        return
    try:
        payload = api_client.get_performance()
        metrics = payload.get("metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        await update.message.reply_text(
            "绩效指标\n"
            f"- total_return: {_fmt_pct(metrics.get('total_return_pct'))}\n"
            f"- max_drawdown: {_fmt_pct(metrics.get('max_drawdown_pct'))}\n"
            f"- win_rate: {_fmt_pct(float(metrics.get('win_rate', 0)) * 100)}\n"
            f"- profit_factor: {_fmt_num(metrics.get('profit_factor'))}"
        )
    except Exception as exc:
        await _send_error(update, exc)


async def cmd_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message:
        return
    try:
        payload = api_client.get_latest_decision()
        if not payload:
            await update.message.reply_text("暂无决策记录。")
            return
        reasoning = payload.get("reasoning", {})
        if not isinstance(reasoning, dict):
            reasoning = {}
        await update.message.reply_text(
            "最新决策\n"
            f"- time: {payload.get('timestamp')}\n"
            f"- action: {payload.get('decision')}\n"
            f"- size: {_fmt_pct(payload.get('position_size_pct'))}\n"
            f"- confidence: {_fmt_pct(float(payload.get('confidence', 0)) * 100)}\n"
            f"- mind_alignment: {reasoning.get('mind_alignment')}\n"
            f"- bias_check: {reasoning.get('bias_check')}"
        )
    except Exception as exc:
        await _send_error(update, exc)


async def cmd_mind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message:
        return
    try:
        payload = api_client.get_market_mind().get("market_mind", {})
        if not isinstance(payload, dict):
            payload = {}
        beliefs = payload.get("market_beliefs", {})
        if not isinstance(beliefs, dict):
            beliefs = {}
        regime = beliefs.get("regime", "N/A")
        narrative = beliefs.get("narrative", "N/A")
        updated = payload.get("last_updated", "N/A")
        await update.message.reply_text(
            "Market Mind 摘要\n"
            f"- regime: {regime}\n"
            f"- last_updated: {updated}\n"
            f"- narrative: {narrative}"
        )
    except Exception as exc:
        await _send_error(update, exc)


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message:
        return
    try:
        payload = api_client.trigger_analysis()
        result = payload.get("result", {})
        if not isinstance(result, dict):
            result = {}
        decision = result.get("decision", {})
        if not isinstance(decision, dict):
            decision = {}
        await update.message.reply_text(
            "分析已触发\n"
            f"- status: {payload.get('status')}\n"
            f"- decision_id: {result.get('decision_id')}\n"
            f"- action: {decision.get('decision')}\n"
            f"- confidence: {_fmt_pct(float(decision.get('confidence', 0)) * 100)}"
        )
    except Exception as exc:
        await _send_error(update, exc)


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message:
        return
    try:
        payload = api_client.pause()
        await update.message.reply_text(f"已暂停: {payload.get('message')}")
    except Exception as exc:
        await _send_error(update, exc)


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message:
        return
    try:
        payload = api_client.resume()
        await update.message.reply_text(f"已恢复: {payload.get('message')}")
    except Exception as exc:
        await _send_error(update, exc)


async def cmd_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    user_text = " ".join(context.args).strip()
    if not user_text:
        await update.message.reply_text("用法: /view <你的市场观点>")
        return

    try:
        api_client.append_user_view(user_text, changed_by="telegram_user")
        await update.message.reply_text("已记录到 Market Mind.user_inputs。")
    except Exception as exc:
        await _send_error(update, exc)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    lowered = text.lower()

    # Query intents from PRD/TASK_QUEUE.
    if "持仓" in text or "portfolio" in lowered:
        await cmd_portfolio(update, context)
        return
    if "绩效" in text or "performance" in lowered:
        await cmd_performance(update, context)
        return
    if "最新决策" in text or "decision" in lowered:
        await cmd_decision(update, context)
        return
    if "系统状态" in text or "status" in lowered:
        await cmd_status(update, context)
        return
    if "你怎么看市场" in text or "怎么看市场" in text or "market view" in lowered:
        await cmd_mind(update, context)
        return

    # User view ingestion from plain text.
    if text.startswith("观点:") or text.startswith("我觉得") or text.startswith("我认为"):
        try:
            api_client.append_user_view(text, changed_by="telegram_user")
            await update.message.reply_text("观点已写入 Market Mind.user_inputs。")
        except APIClientError as exc:
            await _send_error(update, exc)
        return

    await update.message.reply_text("未识别指令。可用 /start 查看命令。")


def build_application(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("portfolio", cmd_portfolio))
    app.add_handler(CommandHandler("performance", cmd_performance))
    app.add_handler(CommandHandler("decision", cmd_decision))
    app.add_handler(CommandHandler("mind", cmd_mind))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("view", cmd_view))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    logger.info("Starting Overseer Agent at %s", datetime.now(timezone.utc).isoformat())
    application = build_application(token)
    application.run_polling(close_loop=False)


if __name__ == "__main__":
    main()

