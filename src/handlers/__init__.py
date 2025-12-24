from .chat import setup_chat_handlers


def register_all_handlers(dp):
    setup_chat_handlers(dp)
