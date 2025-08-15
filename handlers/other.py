import logging

from aiogram import F, Router
from aiogram.types import Message
from filters.filters import AccessRightsFilter

logger_owners = logging.getLogger(__name__)

other_router = Router()

@other_router.message()
async def other_handler(msg: Message) -> None:
    logger_owners.debug('Entry')
    await msg.delete()
    logger_owners.debug('Exit')
