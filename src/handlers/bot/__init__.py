def setup_bot_handlers(dp):
    from .actions import router as actions_router
    from .admins import router as admins_router
    from .chat import router as chat_router
    from .private import router as private_router
    from .settings import router as settings_router

    dp.include_router(actions_router)
    dp.include_router(admins_router)
    dp.include_router(chat_router)
    dp.include_router(settings_router)
    dp.include_router(private_router)
