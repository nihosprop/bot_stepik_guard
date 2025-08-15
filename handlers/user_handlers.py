import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from filters.filters import AccessRightsFilter

from keyboards.keyboards import kb_start
from utils.utils import get_username
from utils.utils import MessageProcessor

logger = logging.getLogger(__name__)

user_router = Router()

user_router.message.filter(AccessRightsFilter(flag_users=True))
user_router.callback_query.filter(AccessRightsFilter(flag_users=True))

@user_router.message(F.text == '/start')
async def cmd_start(msg: Message, msg_processor: MessageProcessor):
    logger.debug('Entry')
    await msg_processor.deletes_messages(msgs_for_del=True)
    await msg.answer(f'Приветствую, {await get_username(msg)}!', reply_markup=kb_start)
    logger.debug('Exit')