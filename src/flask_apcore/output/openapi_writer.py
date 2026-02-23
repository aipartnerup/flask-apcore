"""OpenAPI 3.1 output writer for flask-apcore.

Writes all ScannedModules as a single openapi.json file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask_apcore.scanners.base import ScannedModule

logger = logging.getLogger("flask_apcore")

_DEFAULT_TITLE = "flask-apcore API"
_DEFAULT_VERSION = "1.0.0"


class OpenAPIWriter:
    """Generates openapi.json from ScannedModule instances."""

    def write(
        self,
        modules: list[ScannedModule],
        output_dir: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        from flask_apcore.serializers import modules_to_openapi

        spec = modules_to_openapi(
            modules, title=_DEFAULT_TITLE, version=_DEFAULT_VERSION
        )

        if not dry_run and modules:
            output_path = Path(output_dir).resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            file_path = output_path / "openapi.json"
            file_path.write_text(
                json.dumps(spec, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Written: %s", file_path)

        return spec
