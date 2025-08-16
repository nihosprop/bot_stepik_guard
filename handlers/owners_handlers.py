import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from filters.filters import AccessRightsFilter
from utils.utils import MessageProcessor, get_username
from lexicon.lexicon_ru import LexiconRu

logger_owners = logging.getLogger(__name__)

owners_router = Router()

owners_router.message.filter(AccessRightsFilter())
owners_router.callback_query.filter(AccessRightsFilter())

@owners_router.callback_query(F.data.in_(['settings_courses', 'settings_users']))
async def in_development(clbk: CallbackQuery):
    logger_owners.debug('Entry')
    await clbk.answer('Кнопка в разработке', show_alert=True)
    logger_owners.debug('Exit')
