"""JSON API endpoints for the explorer Blueprint."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

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

    @bp.route("/modules/<path:module_id>/call", methods=["POST"])
    def call_module(module_id: str):
        settings = current_app.extensions["apcore"]["settings"]
        if not settings.explorer_allow_execute:
            return jsonify({"error": "Module execution is disabled. "
                           "Set APCORE_EXPLORER_ALLOW_EXECUTE=True to enable."}), 403

        from apcore.errors import ModuleNotFoundError as ApcoreNotFound
        from apcore.errors import SchemaValidationError

        from flask_apcore.registry import get_context_factory, get_executor

        inputs = request.get_json(silent=True) or {}

        executor = get_executor()
        context = get_context_factory().create_context(request)

        try:
            output = executor.call(module_id, inputs, context)
        except ApcoreNotFound:
            return jsonify({"error": f"Module '{module_id}' not found"}), 404
        except SchemaValidationError as e:
            return jsonify({"error": f"Input validation failed: {e}"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        return jsonify({"output": output})
