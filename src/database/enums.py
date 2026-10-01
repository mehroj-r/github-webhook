import enum


class ChatType(enum.StrEnum):
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class DeliveryStatus(enum.StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    IGNORED = "ignored"
    FAILED = "failed"


class MessageTemplate(enum.StrEnum):
    VERBOSE = "verbose"
    COMPACT = "compact"
