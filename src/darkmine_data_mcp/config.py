# Copyright (C) 2026 Darkmine Pty Ltd
# SPDX-License-Identifier: Apache-2.0

"""Environment-backed configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import DarkmineConfigError


DEFAULT_BASE_URL = "https://api.darkmine.ai"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RECORDS = 1000


@dataclass(frozen=True)
class DarkmineConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_records: int = DEFAULT_MAX_RECORDS

    @property
    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}


def load_config(env: dict[str, str] | None = None) -> DarkmineConfig:
    values = os.environ if env is None else env
    api_key = values.get("DARKMINE_DATA_API_KEY", "").strip()
    if not api_key:
        raise DarkmineConfigError("DARKMINE_DATA_API_KEY is required.")

    base_url = values.get("DARKMINE_DATA_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        raise DarkmineConfigError("DARKMINE_DATA_BASE_URL must start with http:// or https://.")

    try:
        timeout_seconds = float(
            values.get("DARKMINE_DATA_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
        )
    except ValueError as exc:
        raise DarkmineConfigError("DARKMINE_DATA_TIMEOUT_SECONDS must be a number.") from exc
    if timeout_seconds <= 0:
        raise DarkmineConfigError("DARKMINE_DATA_TIMEOUT_SECONDS must be greater than 0.")

    try:
        max_records = int(values.get("DARKMINE_DATA_MAX_RECORDS", str(DEFAULT_MAX_RECORDS)))
    except ValueError as exc:
        raise DarkmineConfigError("DARKMINE_DATA_MAX_RECORDS must be an integer.") from exc
    if max_records < 1 or max_records > 10000:
        raise DarkmineConfigError("DARKMINE_DATA_MAX_RECORDS must be between 1 and 10000.")

    return DarkmineConfig(
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        max_records=max_records,
    )
