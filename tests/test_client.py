# Copyright (C) 2026 Darkmine Pty Ltd
# SPDX-License-Identifier: Apache-2.0

import httpx
import pytest

from darkmine_data_mcp.client import DarkmineClient
from darkmine_data_mcp.config import DarkmineConfig
from darkmine_data_mcp.errors import DarkmineAPIError


def _config() -> DarkmineConfig:
    return DarkmineConfig(api_key="dm_test", base_url="https://api.example.test")


@pytest.mark.asyncio
async def test_client_sends_bearer_auth_and_usage_headers():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer dm_test"
        assert str(request.url) == "https://api.example.test/v1/raw/gswa/tables"
        return httpx.Response(
            200,
            json={"ok": True},
            headers={
                "X-Vault-Metered-MB": "0.25",
                "X-Darkmine-Records": "10",
            },
        )

    async with DarkmineClient(_config(), transport=httpx.MockTransport(handler)) as client:
        result = await client.get("/v1/raw/gswa/tables")

    assert result == {
        "data": {"ok": True},
        "usage": {"mb_used": 0.25, "records": 10},
    }


@pytest.mark.asyncio
async def test_api_401_handling():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "nope"})

    async with DarkmineClient(_config(), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DarkmineAPIError, match="invalid API key"):
            await client.get("/v1/raw/gswa/tables")


@pytest.mark.asyncio
async def test_api_429_handling():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"detail": "rate"})

    async with DarkmineClient(_config(), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DarkmineAPIError, match="quota exceeded"):
            await client.get("/v1/raw/gswa/tables")
