from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.src.config import settings


@dataclass
class RiskCheckResult:
    approved: bool
    adjusted_decision: dict[str, Any]
    violations: list[str] = field(default_factory=list)
    adjustments: list[str] = field(default_factory=list)


def _extract_dynamic_position_cap(market_mind: dict[str, Any]) -> float | None:
    # Example mitigation text:
    # "连续盈利3次后仓位上限自动降低到15%"
    for item in market_mind.get("bias_awareness", []):
        mitigation = str(item.get("mitigation", ""))
        if "仓位" not in mitigation or "上限" not in mitigation:
            continue
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", mitigation)
        if match:
            return float(match.group(1))
    return None


def _bound(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def apply_risk_checks(
    decision: dict[str, Any],
    portfolio: dict[str, Any],
    market_mind: dict[str, Any],
) -> RiskCheckResult:
    adjusted = dict(decision)
    violations: list[str] = []
    adjustments: list[str] = []

    action = str(adjusted.get("decision", "hold")).lower()
    if action not in {"buy", "sell", "hold"}:
        violations.append(f"Invalid decision action: {action}")
        return RiskCheckResult(approved=False, adjusted_decision=adjusted, violations=violations, adjustments=adjustments)

    current_exposure = float(portfolio.get("exposure_pct", 0.0))
    daily_pnl_pct = float(portfolio.get("daily_pnl_pct", 0.0))
    max_position_pct = settings.max_position_pct * 100
    max_exposure_pct = settings.max_exposure_pct * 100
    dynamic_cap = _extract_dynamic_position_cap(market_mind)
    if dynamic_cap is not None:
        max_position_pct = min(max_position_pct, dynamic_cap)

    requested_position_pct = float(adjusted.get("position_size_pct", 0.0))
    bounded_position = _bound(requested_position_pct, 0.0, max_position_pct)
    if bounded_position != requested_position_pct:
        adjusted["position_size_pct"] = round(bounded_position, 2)
        adjustments.append(f"position_size_pct adjusted to max single position cap: {bounded_position:.2f}%")

    if action == "buy":
        projected_exposure = current_exposure + float(adjusted.get("position_size_pct", 0.0))
        if projected_exposure > max_exposure_pct:
            allowed = max(0.0, max_exposure_pct - current_exposure)
            adjusted["position_size_pct"] = round(allowed, 2)
            adjustments.append(f"position_size_pct adjusted to exposure cap allowance: {allowed:.2f}%")

        entry_price = float(adjusted.get("entry_price", 0.0))
        stop_loss = float(adjusted.get("stop_loss", 0.0))
        if entry_price <= 0 or stop_loss <= 0:
            violations.append("Stop-loss is required for buy decisions.")
        elif stop_loss >= entry_price:
            violations.append("Stop-loss must be lower than entry price for long positions.")
        else:
            stop_loss_pct = (entry_price - stop_loss) / entry_price
            if stop_loss_pct > settings.max_stop_loss_pct:
                adjusted_stop = entry_price * (1 - settings.max_stop_loss_pct)
                adjusted["stop_loss"] = round(adjusted_stop, 2)
                adjustments.append(f"stop_loss adjusted to max distance cap: {settings.max_stop_loss_pct * 100:.2f}%")

    if daily_pnl_pct <= -settings.max_daily_loss_pct * 100:
        violations.append("Max daily loss reached; new positions are blocked.")

    approved = len(violations) == 0 and (action != "buy" or float(adjusted.get("position_size_pct", 0.0)) > 0)
    return RiskCheckResult(
        approved=approved,
        adjusted_decision=adjusted,
        violations=violations,
        adjustments=adjustments,
    )

