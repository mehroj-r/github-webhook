def setup_bot_handlers(dp):
    from .private import router as private_router
    from .chat import router as chat_router

    dp.include_router(chat_router)
    dp.include_router(private_router)
