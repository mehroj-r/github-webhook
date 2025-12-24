def setup_bot_handlers(dp):
    from .private import router as private_router

    dp.include_router(private_router)
