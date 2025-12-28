import importlib
import pkgutil

for _, module_name, _ in pkgutil.iter_modules(__path__):
    importlib.import_module(f".{module_name}", __package__)
