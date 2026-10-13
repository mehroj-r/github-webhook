"""sqladmin dashboard at /admin, protected by HTTP Basic auth. Mounted only when ADMIN_PASSWORD is set."""

import base64
import binascii
import hmac
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from sqladmin import Admin, ModelView
from starlette.middleware import Middleware
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from config import settings
from core import get_logger
from database import async_session_maker
from database.models import BotAdmin, Chat, DigestItem, GithubRepository, WebhookDelivery

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger(__name__)

ADMIN_PATH = "/admin"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def credentials_valid(authorization: str | None, username: str, password: str) -> bool:
    """Constant-time check of an ``Authorization: Basic ...`` header."""
    if not authorization or not authorization.lower().startswith("basic "):
        return False
    try:
        decoded = base64.b64decode(authorization[6:].strip(), validate=True).decode()
    except (binascii.Error, UnicodeDecodeError):
        return False
    given_user, _, given_password = decoded.partition(":")
    user_ok = hmac.compare_digest(given_user.encode(), username.encode())
    password_ok = hmac.compare_digest(given_password.encode(), password.encode())
    return user_ok and password_ok


def is_cross_site(method: str, headers: dict[bytes, bytes]) -> bool:
    """
    Browsers resend Basic credentials on cross-site form posts and sqladmin has no CSRF tokens,
    so state-changing requests must come from the same host (judged by Origin, else Referer).
    """
    if method in SAFE_METHODS:
        return False
    source = headers.get(b"origin") or headers.get(b"referer")
    if not source:
        return False  # non-browser clients (curl) send neither
    host = headers.get(b"x-forwarded-host") or headers.get(b"host", b"")
    return urlsplit(source.decode("latin-1")).netloc != host.decode("latin-1").split(",")[0].strip()


class BasicAuthMiddleware:
    """Require HTTP Basic credentials for every request to the wrapped app and reject cross-site writes."""

    def __init__(self, app: ASGIApp, username: str, password: str) -> None:
        self.app = app
        self.username = username
        self.password = password

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        authorization = headers.get(b"authorization", b"").decode("latin-1") or None
        if credentials_valid(authorization, self.username, self.password):
            if is_cross_site(scope["method"], headers):
                await Response("Cross-site request rejected", status_code=403)(scope, receive, send)
                return
            await self.app(scope, receive, send)
            return

        response = Response(
            "Authentication required", status_code=401, headers={"WWW-Authenticate": 'Basic realm="admin"'}
        )
        await response(scope, receive, send)


class ChatAdmin(ModelView, model=Chat):
    icon = "fa-solid fa-comments"
    column_list = [Chat.chat_id, Chat.title, Chat.chat_type, Chat.is_active, Chat.template, Chat.created_at]
    column_searchable_list = [Chat.title, Chat.chat_id]
    column_sortable_list = [Chat.created_at, Chat.title]
    column_default_sort = (Chat.created_at, True)
    form_excluded_columns = [Chat.repositories, Chat.created_at, Chat.updated_at]
    can_create = False


class RepositoryAdmin(ModelView, model=GithubRepository):
    name = "Repository"
    name_plural = "Repositories"
    icon = "fa-brands fa-github"
    column_list = [
        GithubRepository.title,
        GithubRepository.chat,
        GithubRepository.is_active,
        GithubRepository.branch_filter,
        GithubRepository.muted_until,
        GithubRepository.digest_interval_minutes,
        GithubRepository.installation_id,
    ]
    column_searchable_list = [GithubRepository.title]
    column_sortable_list = [GithubRepository.title, GithubRepository.created_at]
    column_default_sort = (GithubRepository.created_at, True)
    form_excluded_columns = [GithubRepository.created_at, GithubRepository.updated_at]
    can_create = False


class DeliveryAdmin(ModelView, model=WebhookDelivery):
    name = "Delivery"
    name_plural = "Deliveries"
    icon = "fa-solid fa-inbox"
    column_list = [
        WebhookDelivery.created_at,
        WebhookDelivery.event_type,
        WebhookDelivery.action,
        WebhookDelivery.repo_name,
        WebhookDelivery.status,
        WebhookDelivery.error,
    ]
    column_searchable_list = [WebhookDelivery.delivery_id, WebhookDelivery.repo_name, WebhookDelivery.event_type]
    column_sortable_list = [WebhookDelivery.created_at, WebhookDelivery.event_type, WebhookDelivery.status]
    column_default_sort = (WebhookDelivery.created_at, True)
    can_create = False
    can_edit = False


class DigestItemAdmin(ModelView, model=DigestItem):
    name = "Digest item"
    name_plural = "Digest items"
    icon = "fa-solid fa-layer-group"
    column_list = [
        DigestItem.created_at,
        DigestItem.repo_name,
        DigestItem.chat_id,
        DigestItem.event_type,
        DigestItem.flushed_at,
    ]
    column_searchable_list = [DigestItem.repo_name]
    column_sortable_list = [DigestItem.created_at, DigestItem.flushed_at]
    column_default_sort = (DigestItem.created_at, True)
    can_create = False
    can_edit = False


class BotAdminAdmin(ModelView, model=BotAdmin):
    name = "Bot admin"
    name_plural = "Bot admins"
    icon = "fa-solid fa-user-shield"
    column_list = [BotAdmin.user_id, BotAdmin.name, BotAdmin.added_by_user_id, BotAdmin.created_at]
    form_columns = [BotAdmin.user_id, BotAdmin.name]


VIEWS: list[type[ModelView]] = [ChatAdmin, RepositoryAdmin, DeliveryAdmin, DigestItemAdmin, BotAdminAdmin]


def setup_admin(app: "FastAPI") -> Admin | None:
    """Mount the dashboard when ADMIN_PASSWORD is configured."""
    if not settings.ADMIN_PASSWORD:
        logger.info("Admin dashboard disabled (ADMIN_PASSWORD not set)")
        return None

    admin = Admin(
        app,
        session_maker=async_session_maker,
        base_url=ADMIN_PATH,
        title=f"{settings.APP_NAME} admin",
        middlewares=[
            Middleware(BasicAuthMiddleware, username=settings.ADMIN_USERNAME, password=settings.ADMIN_PASSWORD)
        ],
    )
    for view in VIEWS:
        admin.add_view(view)
    logger.info("Admin dashboard mounted at %s", ADMIN_PATH)
    return admin
