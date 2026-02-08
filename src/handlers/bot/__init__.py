def setup_bot_handlers(dp):
    from .chat import router as chat_router
    from .private import router as private_router

    dp.include_router(chat_router)
    dp.include_router(private_router)
