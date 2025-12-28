from sqlalchemy.ext.asyncio import AsyncSession

from core import get_logger
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from handlers.github.models.events import PushEvent

logger = get_logger(__name__)


@GitHubEventRegistry.register(event=GHEventType.PUSH)
async def handle_push_event(event: PushEvent, session: AsyncSession):
    """Handle GitHub push events"""
    logger.info("Handling push event for repository: %s", event.repository.full_name)


@GitHubEventRegistry.register(event=GHEventType.CREATE)
async def handle_create_event(event, session: AsyncSession):
    """Handle GitHub create events"""
    logger.info("Handling create event for repository: %s", event.repository.full_name)


@GitHubEventRegistry.register(event=GHEventType.DELETE)
async def handle_delete_event(event, session: AsyncSession):
    """Handle GitHub delete events"""
    logger.info("Handling delete event for repository: %s", event.repository.full_name)
