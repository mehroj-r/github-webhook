from enum import StrEnum


class GHEventType(StrEnum):
    PING = "ping"
    PUSH = "push"
    CREATE = "create"
    DELETE = "delete"


class ContentType(StrEnum):
    JSON = "application/json"
    FORM_URLENCODED = "application/x-www-form-urlencoded"
