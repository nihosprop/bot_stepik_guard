import logging

from aiogram import F, Router
from aiogram.types import Message
from filters.filters import AccessRightsFilter

logger_owners = logging.getLogger(__name__)

other_router = Router()

other_router.message.filter(AccessRightsFilter())
other_router.callback_query.filter(AccessRightsFilter())


@other_router.message()
async def other_handler(msg: Message):
    await msg.delete()
