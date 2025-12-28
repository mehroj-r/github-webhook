from sqlalchemy.ext.asyncio import AsyncSession

from core import get_logger
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from handlers.github.models.events import CreateEvent

logger = get_logger(__name__)


@GitHubEventRegistry.register(event=GHEventType.CREATE)
async def handle_create_event(event: CreateEvent, session: AsyncSession):
    """Handle GitHub create events"""
    logger.info("Handling create event for repository: %s", event.repository.full_name)
