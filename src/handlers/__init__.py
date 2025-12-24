def register_all_handlers(dp):
    from .bot import setup_bot_handlers

    setup_bot_handlers(dp)


def setup_api_routers(app):
    from .api import setup_api_routers

    setup_api_routers(app)
