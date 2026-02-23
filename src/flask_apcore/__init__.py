"""flask-apcore: Flask Extension for apcore AI-Perceivable Core integration."""

__version__ = "0.1.0"

from flask_apcore.extension import Apcore

from apcore import module

from apcore import (
    ACL,
    Config,
    Context,
    Executor,
    Identity,
    Middleware,
    ModuleAnnotations,
    ModuleDescriptor,
    Registry,
)

__all__ = [
    "Apcore",
    "__version__",
    "module",
    "ACL",
    "Config",
    "Context",
    "Executor",
    "Identity",
    "Middleware",
    "ModuleAnnotations",
    "ModuleDescriptor",
    "Registry",
]
