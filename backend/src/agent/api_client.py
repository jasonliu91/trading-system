from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class APIClientError(RuntimeError):
    """Raised when backend API call fails."""


@dataclass
class BackendAPIClient:
    base_url: str = os.getenv("BACKEND_API_BASE_URL", "http://127.0.0.1:8000")
    timeout_sec: int = 12

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(url=url, method=method, data=payload)
        if body is not None:
            request.add_header("Content-Type", "application/json")

        try:
            with urlopen(request, timeout=self.timeout_sec) as response:
                raw = response.read().decode("utf-8")
        except (HTTPError, URLError) as exc:
            raise APIClientError(f"{method} {path} failed: {exc}") from exc

        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise APIClientError(f"Invalid JSON from {method} {path}: {raw}") from exc

        if not isinstance(decoded, dict):
            raise APIClientError(f"Unexpected payload type for {method} {path}: {type(decoded)}")
        return decoded

    def get_system_status(self) -> dict[str, Any]:
        return self._request("GET", "/api/system/status")

    def get_portfolio(self) -> dict[str, Any]:
        return self._request("GET", "/api/portfolio")

    def get_latest_decision(self) -> dict[str, Any] | None:
        payload = self._request("GET", "/api/decisions?limit=1")
        items = payload.get("items", [])
        if isinstance(items, list) and items:
            value = items[0]
            return value if isinstance(value, dict) else None
        return None

    def get_performance(self) -> dict[str, Any]:
        return self._request("GET", "/api/performance")

    def get_market_mind(self) -> dict[str, Any]:
        return self._request("GET", "/api/mind")

    def trigger_analysis(self) -> dict[str, Any]:
        return self._request("POST", "/api/system/trigger-analysis")

    def pause(self) -> dict[str, Any]:
        return self._request("POST", "/api/system/pause")

    def resume(self) -> dict[str, Any]:
        return self._request("POST", "/api/system/resume")

    def append_user_view(self, user_text: str, changed_by: str = "telegram_user") -> dict[str, Any]:
        current = self.get_market_mind().get("market_mind", {})
        if not isinstance(current, dict):
            raise APIClientError("Market mind payload is not an object")

        user_inputs = current.get("user_inputs", [])
        if not isinstance(user_inputs, list):
            user_inputs = []
        user_inputs.append(
            {
                "input": user_text,
                "date": date.today().isoformat(),
                "incorporated": False,
            }
        )
        current["user_inputs"] = user_inputs

        updated = self._request(
            "PUT",
            "/api/mind",
            body={
                "market_mind": current,
                "changed_by": changed_by,
                "change_summary": "Added user market view from Telegram",
            },
        )
        return updated

