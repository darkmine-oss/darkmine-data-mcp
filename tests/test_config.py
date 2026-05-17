# Copyright (C) 2026 Darkmine Pty Ltd
# SPDX-License-Identifier: Apache-2.0

import pytest

from darkmine_data_mcp.config import DEFAULT_BASE_URL, load_config
from darkmine_data_mcp.errors import DarkmineConfigError


def test_missing_api_key_fails_fast():
    with pytest.raises(DarkmineConfigError, match="DARKMINE_DATA_API_KEY"):
        load_config({})


def test_base_url_config_strips_trailing_slash():
    config = load_config(
        {
            "DARKMINE_DATA_API_KEY": "dm_test",
            "DARKMINE_DATA_BASE_URL": "https://example.test/",
            "DARKMINE_DATA_TIMEOUT_SECONDS": "12.5",
            "DARKMINE_DATA_MAX_RECORDS": "250",
        }
    )

    assert config.base_url == "https://example.test"
    assert config.timeout_seconds == 12.5
    assert config.max_records == 250


def test_default_base_url():
    config = load_config({"DARKMINE_DATA_API_KEY": "dm_test"})

    assert config.base_url == DEFAULT_BASE_URL


def test_auth_header_creation():
    config = load_config({"DARKMINE_DATA_API_KEY": "dm_test"})

    assert config.auth_headers == {"Authorization": "Bearer dm_test"}
