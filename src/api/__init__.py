from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def setup_api_routers(app: "FastAPI") -> None:
    import importlib
    import pkgutil
    from fastapi import APIRouter

    package_name = __name__  # api
    package_path = __path__

    for module_info in pkgutil.iter_modules(package_path):
        module_name = module_info.name

        if module_name.startswith("_"):
            continue

        module = importlib.import_module(f"{package_name}.{module_name}")

        router = getattr(module, "router", None)
        if router and isinstance(router, APIRouter):
            app.include_router(router)
