from __future__ import annotations

import copy
import json
import shutil
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.src.config import settings
from backend.src.db.models import MarketMindHistory


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def ensure_market_mind_file() -> None:
    settings.ensure_runtime_paths()
    if settings.market_mind_path.exists():
        return
    if settings.market_mind_template_path.exists():
        shutil.copy(settings.market_mind_template_path, settings.market_mind_path)
        return
    fallback = {
        "version": "1.0",
        "last_updated": None,
        "updated_by": "manual_init",
        "market_beliefs": {},
        "strategy_weights": {},
        "lessons_learned": [],
        "bias_awareness": [],
        "active_watchlist": [],
        "user_inputs": [],
        "performance_memory": {},
    }
    settings.market_mind_path.write_text(
        json.dumps(fallback, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load() -> dict[str, Any]:
    ensure_market_mind_file()
    content = settings.market_mind_path.read_text(encoding="utf-8")
    return json.loads(content)


def save(
    market_mind: dict[str, Any],
    changed_by: str = "manual_update",
    db: Session | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    previous_state = load()
    next_state = copy.deepcopy(market_mind)
    next_state["last_updated"] = _utc_iso_now()
    next_state["updated_by"] = changed_by

    settings.market_mind_path.write_text(
        json.dumps(next_state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if db is not None:
        record = MarketMindHistory(
            changed_by=changed_by,
            previous_state=json.dumps(previous_state, ensure_ascii=False),
            new_state=json.dumps(next_state, ensure_ascii=False),
            change_summary=change_summary or "Market Mind updated",
        )
        db.add(record)
        db.commit()

    return next_state


def update(
    patch: dict[str, Any],
    changed_by: str = "manual_update",
    db: Session | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    current = load()
    merged = _deep_merge(current, patch)
    return save(
        market_mind=merged,
        changed_by=changed_by,
        db=db,
        change_summary=change_summary,
    )


def inject_to_prompt(market_mind: dict[str, Any]) -> str:
    bias_count = len(market_mind.get("bias_awareness", []))
    accuracy = market_mind.get("performance_memory", {}).get("recent_accuracy")

    last_updated = market_mind.get("last_updated")
    days_since = "unknown"
    if last_updated:
        try:
            updated_at = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            days_since = str(max((datetime.now(timezone.utc) - updated_at).days, 0))
        except ValueError:
            days_since = "unknown"

    accuracy_text = json.dumps(accuracy, ensure_ascii=False) if accuracy is not None else "N/A"
    mind_json = json.dumps(market_mind, ensure_ascii=False, indent=2)

    return (
        "你是ETH量化交易分析师。\n\n"
        "## 你的当前认知状态 (Market Mind)\n"
        f"{mind_json}\n\n"
        "## 重要提醒\n"
        f"- 你的偏误警觉列表中有{bias_count}条提醒，做决策前请检查\n"
        f"- 上次更新认知是在{days_since}天前\n"
        f"- 你最近10次决策的准确率是{accuracy_text}\n"
    )

