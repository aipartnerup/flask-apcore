"""Scanner subpackage for flask-apcore.

Provides get_scanner() and auto_detect_scanner() for scanner selection.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flask_apcore.scanners.base import BaseScanner
from flask_apcore.scanners.native import NativeFlaskScanner

if TYPE_CHECKING:
    from flask import Flask

logger = logging.getLogger("flask_apcore")

_SCANNER_REGISTRY: dict[str, type[BaseScanner]] = {
    "native": NativeFlaskScanner,
}


def get_scanner(source: str) -> BaseScanner:
    """Return a scanner instance for the given source name.

    Args:
        source: Scanner source name ("native", "smorest", "restx").

    Returns:
        An instantiated BaseScanner subclass.

    Raises:
        ValueError: If source is unknown.
    """
    if source not in _SCANNER_REGISTRY:
        raise ValueError(f"Unknown scanner source: {source!r}")
    return _SCANNER_REGISTRY[source]()


def auto_detect_scanner(app: Flask) -> BaseScanner:
    """Auto-detect the best scanner for the given Flask app.

    Detection priority:
    1. flask-smorest Blueprints -> SmorestScanner (P1)
    2. flask-restx Api -> RestxScanner (P1)
    3. Fallback -> NativeFlaskScanner

    Args:
        app: Flask application instance.

    Returns:
        The most appropriate scanner for the app.
    """
    # P0: only NativeFlaskScanner is implemented
    return NativeFlaskScanner()
