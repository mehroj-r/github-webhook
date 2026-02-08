def setup_api_routers(app):
    from .github import router as github_router
    from .misc import router as misc_router
    from .telegram import router as telegram_router

    app.include_router(telegram_router)
    app.include_router(misc_router)
    app.include_router(github_router)
