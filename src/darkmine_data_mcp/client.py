# Copyright (C) 2026 Darkmine Pty Ltd
# SPDX-License-Identifier: Apache-2.0

"""Async client for the Darkmine Zuplo-authenticated API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .config import DarkmineConfig
from .errors import DarkmineAPIError, DarkmineTimeoutError


USAGE_HEADERS = {
    "x-darkmine-mb-used": "mb_used",
    "x-darkmine-records": "records",
    "x-darkmine-cost": "cost",
    "x-vault-metered-mb": "mb_used",
    "x-vault-metered-bytes": "bytes_used",
    "x-vault-meter-values": "meter_values",
}


class DarkmineClient:
    def __init__(
        self,
        config: DarkmineConfig,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers=config.auth_headers,
            timeout=config.timeout_seconds,
            transport=transport,
        )

    async def __aenter__(self) -> "DarkmineClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def post(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("POST", path, params=params, json=json)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, params=params, json=json)
        except httpx.TimeoutException as exc:
            raise DarkmineTimeoutError(
                "Darkmine API request failed: timeout. Try a smaller area or lower limit."
            ) from exc
        except httpx.HTTPError as exc:
            raise DarkmineAPIError("Darkmine API request failed: network error.") from exc

        if response.status_code >= 400:
            raise DarkmineAPIError(_format_error(response))

        try:
            data = response.json()
        except ValueError as exc:
            raise DarkmineAPIError("Darkmine API request failed: response was not JSON.") from exc

        return {"data": data, "usage": extract_usage(response.headers)}


def extract_usage(headers: httpx.Headers | Mapping[str, str]) -> dict[str, Any]:
    usage: dict[str, Any] = {}
    lowered = {key.lower(): value for key, value in headers.items()}
    for header, output_key in USAGE_HEADERS.items():
        raw_value = lowered.get(header)
        if raw_value is None:
            continue
        usage[output_key] = _parse_header_value(raw_value)
    return usage


def _parse_header_value(value: str) -> Any:
    stripped = value.strip()
    if not stripped:
        return stripped
    try:
        if "." in stripped:
            return float(stripped)
        return int(stripped)
    except ValueError:
        return stripped


def _format_error(response: httpx.Response) -> str:
    status = response.status_code
    detail = _safe_detail(response)
    if status == 400:
        reason = detail or "bad request. Check the query parameters."
    elif status == 401:
        reason = "invalid API key. Check DARKMINE_DATA_API_KEY."
    elif status == 402:
        reason = "payment required. Check your plan or billing status."
    elif status == 429:
        reason = "quota exceeded. Check your plan or API usage dashboard."
    elif 500 <= status <= 599:
        reason = "backend failure. Try again later."
    else:
        reason = detail or f"HTTP {status}."
    return f"Darkmine API request failed: {reason}"


def _safe_detail(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, str):
        return detail
    return None
