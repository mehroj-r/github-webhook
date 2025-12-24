from .private import router as private_router


def setup_chat_handlers(dp):
    dp.include_router(private_router)
