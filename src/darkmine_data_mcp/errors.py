# Copyright (C) 2026 Darkmine Pty Ltd
# SPDX-License-Identifier: Apache-2.0

"""User-facing Darkmine MCP errors."""

from __future__ import annotations


class DarkmineError(Exception):
    """Base class for errors that are safe to show to MCP clients."""


class DarkmineConfigError(DarkmineError):
    """Configuration is missing or invalid."""


class DarkmineValidationError(DarkmineError):
    """Tool input failed validation."""


class DarkmineAPIError(DarkmineError):
    """The upstream Darkmine API returned an error."""


class DarkmineTimeoutError(DarkmineAPIError):
    """The upstream Darkmine API timed out."""
