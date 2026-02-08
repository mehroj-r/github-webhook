import enum


class ChatType(enum.StrEnum):
    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"
