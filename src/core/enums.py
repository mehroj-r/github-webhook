from enum import Enum


class GHEventType(str, Enum):
    PUSH = "push"
    CREATE = "create"
    DELETE = "delete"
