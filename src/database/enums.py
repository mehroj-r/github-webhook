import enum


class ChatType(str, enum.Enum):

    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"
