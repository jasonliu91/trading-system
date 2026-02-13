from __future__ import annotations

import logging
import os
from datetime import datetime, time as dt_time, timezone
from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from backend.src.agent.api_client import APIClientError, BackendAPIClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
logger = logging.getLogger(__name__)

api_client = BackendAPIClient()
NOTIFY_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


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


def _pending_key() -> str:
    return "pending_action"


async def _send_error(update: Update, exc: Exception) -> None:
    logger.exception("Agent handler failed: %s", exc)
    if update.message:
        await update.message.reply_text(f"请求失败: {exc}")


async def _request_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    description: str,
) -> None:
    if not update.message:
        return
    context.chat_data[_pending_key()] = {
        "action": action,
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await update.message.reply_text(
        f"待确认操作: {description}\n"
        "发送 /confirm 执行，发送 /cancel 取消。"
    )


def _clear_pending(context: ContextTypes.DEFAULT_TYPE) -> None:
    if _pending_key() in context.chat_data:
        del context.chat_data[_pending_key()]


def _get_pending(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any] | None:
    value = context.chat_data.get(_pending_key())
    return value if isinstance(value, dict) else None


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
        "/analyze 触发分析（需确认）\n"
        "/pause 暂停调度（需确认）\n"
        "/resume 恢复调度（需确认）\n"
        "/view <你的观点> 写入 Market Mind.user_inputs\n"
        "/confirm 确认待执行操作\n"
        "/cancel 取消待执行操作"
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
    await _request_confirmation(update, context, action="analyze", description="触发一次分析周期")


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _request_confirmation(update, context, action="pause", description="暂停交易调度器")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _request_confirmation(update, context, action="resume", description="恢复交易调度器")


async def cmd_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message:
        return

    pending = _get_pending(context)
    if not pending:
        await update.message.reply_text("当前没有待确认操作。")
        return

    action = str(pending.get("action", ""))
    try:
        if action == "analyze":
            payload = api_client.trigger_analysis()
            result = payload.get("result", {})
            if not isinstance(result, dict):
                result = {}
            decision = result.get("decision", {})
            if not isinstance(decision, dict):
                decision = {}
            await update.message.reply_text(
                "分析已触发\n"
                f"- decision_id: {result.get('decision_id')}\n"
                f"- action: {decision.get('decision')}\n"
                f"- confidence: {_fmt_pct(float(decision.get('confidence', 0)) * 100)}"
            )
        elif action == "pause":
            payload = api_client.pause()
            await update.message.reply_text(f"已暂停: {payload.get('message')}")
        elif action == "resume":
            payload = api_client.resume()
            await update.message.reply_text(f"已恢复: {payload.get('message')}")
        else:
            await update.message.reply_text(f"未知待确认操作: {action}")
    except Exception as exc:
        await _send_error(update, exc)
    finally:
        _clear_pending(context)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message:
        return
    if _get_pending(context):
        _clear_pending(context)
        await update.message.reply_text("已取消待执行操作。")
    else:
        await update.message.reply_text("当前没有待取消操作。")


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
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    lowered = text.lower()

    if text in {"确认", "确认执行"}:
        await cmd_confirm(update, context)
        return
    if text in {"取消", "取消操作"}:
        await cmd_cancel(update, context)
        return

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
    if "触发分析" in text:
        await cmd_analyze(update, context)
        return
    if "暂停交易" in text:
        await cmd_pause(update, context)
        return
    if "恢复交易" in text:
        await cmd_resume(update, context)
        return

    if text.startswith("观点:") or text.startswith("我觉得") or text.startswith("我认为"):
        try:
            api_client.append_user_view(text, changed_by="telegram_user")
            await update.message.reply_text("观点已写入 Market Mind.user_inputs。")
        except APIClientError as exc:
            await _send_error(update, exc)
        return

    await update.message.reply_text("未识别指令。可用 /start 查看命令。")


async def job_notify_latest_decision(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not NOTIFY_CHAT_ID:
        return
    try:
        latest = api_client.get_latest_decision()
        if not latest:
            return
        decision_id = latest.get("id")
        if decision_id is None:
            return

        bot_data = context.application.bot_data
        last_id = bot_data.get("last_notified_decision_id")
        if last_id == decision_id:
            return

        reasoning = latest.get("reasoning", {})
        if not isinstance(reasoning, dict):
            reasoning = {}
        text = (
            "新决策通知\n"
            f"- id: {decision_id}\n"
            f"- time: {latest.get('timestamp')}\n"
            f"- action: {latest.get('decision')}\n"
            f"- size: {_fmt_pct(latest.get('position_size_pct'))}\n"
            f"- confidence: {_fmt_pct(float(latest.get('confidence', 0)) * 100)}\n"
            f"- mind_alignment: {reasoning.get('mind_alignment')}"
        )
        await context.bot.send_message(chat_id=NOTIFY_CHAT_ID, text=text)
        bot_data["last_notified_decision_id"] = decision_id
    except Exception as exc:
        logger.warning("job_notify_latest_decision failed: %s", exc)


async def job_notify_latest_trade(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not NOTIFY_CHAT_ID:
        return
    try:
        trade = api_client.get_latest_trade()
        if not trade:
            return

        trade_id = trade.get("id")
        if trade_id is None:
            return
        bot_data = context.application.bot_data
        last_id = bot_data.get("last_notified_trade_id")
        if last_id == trade_id:
            return

        message = (
            "交易事件通知\n"
            f"- id: {trade_id}\n"
            f"- time: {trade.get('timestamp')}\n"
            f"- side: {trade.get('side')}\n"
            f"- qty: {_fmt_num(trade.get('quantity'))}\n"
            f"- price: {_fmt_num(trade.get('price'))}\n"
            f"- pnl: {_fmt_num(trade.get('pnl'))}"
        )
        await context.bot.send_message(chat_id=NOTIFY_CHAT_ID, text=message)
        bot_data["last_notified_trade_id"] = trade_id
    except Exception as exc:
        logger.warning("job_notify_latest_trade failed: %s", exc)


async def job_daily_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not NOTIFY_CHAT_ID:
        return
    try:
        payload = api_client.get_daily_summary()
        await context.bot.send_message(
            chat_id=NOTIFY_CHAT_ID,
            text=f"每日日报 {payload.get('date')}\n{payload.get('summary')}",
        )
    except Exception as exc:
        logger.warning("job_daily_summary failed: %s", exc)


async def job_health_watch(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not NOTIFY_CHAT_ID:
        return
    bot_data = context.application.bot_data
    previous_ok = bot_data.get("health_ok")
    try:
        payload = api_client.get_health()
        current_ok = payload.get("status") == "ok"
        bot_data["health_ok"] = current_ok
        if previous_ok is False and current_ok is True:
            await context.bot.send_message(chat_id=NOTIFY_CHAT_ID, text="系统健康状态恢复正常。")
    except Exception as exc:
        bot_data["health_ok"] = False
        if previous_ok is not False:
            await context.bot.send_message(chat_id=NOTIFY_CHAT_ID, text=f"系统健康检查异常: {exc}")


def configure_jobs(app: Application) -> None:
    if not app.job_queue or not NOTIFY_CHAT_ID:
        logger.info("Job queue notifications disabled: TELEGRAM_CHAT_ID not set")
        return
    app.job_queue.run_repeating(job_notify_latest_decision, interval=90, first=15, name="notify-latest-decision")
    app.job_queue.run_repeating(job_notify_latest_trade, interval=90, first=20, name="notify-latest-trade")
    app.job_queue.run_repeating(job_health_watch, interval=180, first=30, name="health-watch")
    app.job_queue.run_daily(job_daily_summary, time=dt_time(hour=9, minute=0, tzinfo=timezone.utc), name="daily-summary")


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
    app.add_handler(CommandHandler("confirm", cmd_confirm))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("view", cmd_view))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    configure_jobs(app)
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
