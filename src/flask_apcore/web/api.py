"""JSON API endpoints for the explorer Blueprint."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from flask_apcore.serializers import annotations_to_dict


def register_api_routes(bp: Blueprint) -> None:

    @bp.route("/modules")
    def list_modules():
        registry = current_app.extensions["apcore"]["registry"]
        modules = []
        for module_id, module in registry.iter():
            metadata = getattr(module, "metadata", None) or {}
            entry = {
                "module_id": module_id,
                "description": getattr(module, "description", ""),
                "tags": list(getattr(module, "tags", None) or []),
                "http_method": metadata.get("http_method", ""),
                "url_rule": metadata.get("url_rule", ""),
                "version": getattr(module, "version", "1.0.0"),
            }
            modules.append(entry)
        return jsonify(modules)

    @bp.route("/modules/<path:module_id>")
    def get_module(module_id: str):
        registry = current_app.extensions["apcore"]["registry"]
        descriptor = registry.get_definition(module_id)
        if descriptor is None:
            return jsonify({"error": f"Module '{module_id}' not found"}), 404

        annotations_dict = annotations_to_dict(descriptor.annotations)

        result = {
            "module_id": descriptor.module_id,
            "description": descriptor.description,
            "documentation": descriptor.documentation,
            "tags": descriptor.tags,
            "version": descriptor.version,
            "annotations": annotations_dict,
            "metadata": descriptor.metadata,
            "http_method": descriptor.metadata.get("http_method", ""),
            "url_rule": descriptor.metadata.get("url_rule", ""),
            "input_schema": descriptor.input_schema,
            "output_schema": descriptor.output_schema,
        }
        return jsonify(result)
