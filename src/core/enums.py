from enum import Enum


class GHEventType(str, Enum):
    PUSH = "push"
    CREATE = "create"
    DELETE = "delete"


class ContentType(str, Enum):
    JSON = "application/json"
    FORM_URLENCODED = "application/x-www-form-urlencoded"
