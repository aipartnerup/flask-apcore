"""Output writer subpackage for flask-apcore.

Provides get_writer() factory for selecting output format.

Default writer is RegistryWriter (direct registration).
YAML writer is available via output_format="yaml".
JSON writer is available via output_format="json".
OpenAPI writer is available via output_format="openapi".
"""

from __future__ import annotations


def get_writer(output_format: str | None = None):
    """Return a writer instance for the given format.

    Args:
        output_format: None for direct registry, "yaml" for YAML files,
            "json" for a single JSON file, "openapi" for OpenAPI 3.1 spec.

    Returns:
        A RegistryWriter (default), YAMLWriter, JSONWriter, or
        OpenAPIWriter instance.

    Raises:
        ValueError: If format is unknown.
    """
    if output_format is None:
        from flask_apcore.output.registry_writer import RegistryWriter

        return RegistryWriter()
    elif output_format == "yaml":
        from flask_apcore.output.yaml_writer import YAMLWriter

        return YAMLWriter()
    elif output_format == "json":
        from flask_apcore.output.json_writer import JSONWriter

        return JSONWriter()
    elif output_format == "openapi":
        from flask_apcore.output.openapi_writer import OpenAPIWriter

        return OpenAPIWriter()
    else:
        raise ValueError(f"Unknown output format: {output_format!r}")
