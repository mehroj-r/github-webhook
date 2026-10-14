import importlib
import pkgutil

GENERIC_MODULE = "generic"

# Import dedicated handler modules first so they take precedence over the generic fallback
for _, module_name, _ in pkgutil.iter_modules(__path__):
    if module_name != GENERIC_MODULE:
        importlib.import_module(f".{module_name}", __package__)

from .generic import register_generic_handlers  # noqa: E402

register_generic_handlers()
