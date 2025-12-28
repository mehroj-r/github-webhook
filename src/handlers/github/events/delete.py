from sqlalchemy.ext.asyncio import AsyncSession

from core import get_logger
from core.decorators import GitHubEventRegistry
from core.enums import GHEventType
from handlers.github.models.events import DeleteEvent

logger = get_logger(__name__)


@GitHubEventRegistry.register(event=GHEventType.DELETE)
async def handle_delete_event(event: DeleteEvent, session: AsyncSession):
    """Handle GitHub delete events"""
    logger.info("Handling delete event for repository: %s", event.repository.full_name)
