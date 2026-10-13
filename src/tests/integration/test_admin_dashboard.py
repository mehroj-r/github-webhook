import base64
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.admin import VIEWS, credentials_valid, setup_admin
from config import settings
from database.enums import ChatType
from database.models import BotAdmin, Chat, DigestItem, GithubRepository, WebhookDelivery


def basic(user: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
async def client(sqlite_session_maker):
    async with sqlite_session_maker() as session:
        chat = await Chat.create(session, chat_id=-100, chat_type=ChatType.SUPERGROUP, title="Dev team")
        await GithubRepository.create(
            session, title="octocat/Hello-World", url="https://github.com/octocat/Hello-World", chat_id=chat.id
        )
        await WebhookDelivery.create(session, delivery_id="d-1", event_type="push", status="processed")
        await DigestItem.create(session, repo_name="octocat/Hello-World", chat_id=-100, event_type="push", text="x")
        await BotAdmin.create(session, user_id=7, name="Ada")
        await session.commit()

    app = FastAPI()
    with (
        patch.object(settings, "ADMIN_USERNAME", "root"),
        patch.object(settings, "ADMIN_PASSWORD", "hunter2"),
        patch("api.admin.async_session_maker", sqlite_session_maker),
    ):
        setup_admin(app)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


class TestCredentials:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "header,expected",
        [
            (basic("root", "hunter2")["Authorization"], True),
            (basic("root", "wrong")["Authorization"], False),
            (basic("other", "hunter2")["Authorization"], False),
            ("Bearer hunter2", False),
            ("Basic !!!not-base64", False),
            (None, False),
        ],
    )
    def test_credentials_valid(self, header, expected):
        assert credentials_valid(header, "root", "hunter2") is expected


class TestDashboard:
    @pytest.mark.unit
    def test_disabled_without_password(self):
        app = FastAPI()
        with patch.object(settings, "ADMIN_PASSWORD", ""):
            assert setup_admin(app) is None
        assert not any(getattr(route, "path", "") == "/admin" for route in app.routes)

    @pytest.mark.integration
    async def test_requires_basic_auth(self, client):
        anonymous = await client.get("/admin/")
        wrong = await client.get("/admin/", headers=basic("root", "nope"))

        assert anonymous.status_code == 401
        assert anonymous.headers["www-authenticate"].startswith("Basic")
        assert wrong.status_code == 401

    @pytest.mark.integration
    async def test_every_list_view_renders(self, client):
        index = await client.get("/admin/", headers=basic("root", "hunter2"))
        assert index.status_code == 200

        for view in VIEWS:
            identity = view.identity
            response = await client.get(f"/admin/{identity}/list", headers=basic("root", "hunter2"))
            assert response.status_code == 200, identity

    @pytest.mark.integration
    async def test_list_shows_rows(self, client):
        response = await client.get("/admin/github-repository/list", headers=basic("root", "hunter2"))
        assert "octocat/Hello-World" in response.text

    @pytest.mark.integration
    async def test_edit_and_create_forms_render(self, client, sqlite_session_maker):
        async with sqlite_session_maker() as session:
            chat = await Chat.get(session, chat_id=-100)
            repo = await GithubRepository.get(session, title="octocat/Hello-World")

        auth = basic("root", "hunter2")
        for url in (f"/admin/chat/edit/{chat.id}", f"/admin/github-repository/edit/{repo.id}", "/admin/bot-admin/create"):
            response = await client.get(url, headers=auth)
            assert response.status_code == 200, url

    @pytest.mark.integration
    async def test_cross_site_post_is_rejected(self, client, sqlite_session_maker):
        auth = basic("root", "hunter2")
        form = {"user_id": "99", "name": "Mallory"}

        forged = await client.post(
            "/admin/bot-admin/create", data=form, headers={**auth, "Origin": "https://evil.example"}
        )
        assert forged.status_code == 403

        same_site = await client.post("/admin/bot-admin/create", data=form, headers={**auth, "Origin": "http://test"})
        assert same_site.status_code in (200, 302, 303)

        async with sqlite_session_maker() as session:
            created = await BotAdmin.get(session, user_id=99)
        assert created is not None
        assert created.name == "Mallory"
