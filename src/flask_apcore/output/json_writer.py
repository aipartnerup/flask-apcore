"""JSON output writer for flask-apcore.

Writes all ScannedModules as a single apcore-modules.json file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask_apcore.scanners.base import ScannedModule

logger = logging.getLogger("flask_apcore")


class JSONWriter:
    """Generates a single apcore-modules.json from ScannedModule instances."""

    def write(
        self,
        modules: list[ScannedModule],
        output_dir: str,
        dry_run: bool = False,
    ) -> list[dict[str, Any]]:
        if not modules:
            return []

        from flask_apcore.serializers import modules_to_dicts

        results = modules_to_dicts(modules)

        if not dry_run:
            output_path = Path(output_dir).resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            file_path = output_path / "apcore-modules.json"
            file_path.write_text(
                json.dumps(results, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Written: %s", file_path)

        return results
