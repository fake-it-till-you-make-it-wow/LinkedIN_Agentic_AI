"""Ocean CLI error hierarchy."""

from __future__ import annotations


class OceanError(Exception):
    """Base error for CLI failures."""

    exit_code = 1


class HttpClientError(OceanError):
    """4xx HTTP response."""

    exit_code = 1


class HttpServerError(OceanError):
    """5xx HTTP response."""

    exit_code = 2


class NetworkError(OceanError):
    """Network or timeout failure."""

    exit_code = 3


class SpecUnavailable(OceanError):
    """OpenAPI spec unavailable or invalid."""

    exit_code = 4
