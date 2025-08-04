import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.filters import and_f, or_f

from filters.filters import AccessRightsFilter
from utils.utils import MessageProcessor, get_username

logger_owners = logging.getLogger(__name__)

owners_router = Router()

owners_router.message.filter(AccessRightsFilter())
owners_router.callback_query.filter(AccessRightsFilter())

@owners_router.message(F.text == '/start')
async def cmd_start(msg: Message,
                    msg_processor: MessageProcessor,
                    stepik_courses_ids: list[int]) -> None:
    logger_owners.debug('Entry')
    await msg_processor.deletes_messages(msgs_for_del=True)
    logger_owners.debug(f'{msg.model_dump_json(indent=4)}')
    
    text = (f'Приветствую, {await get_username(msg)}!\n\n'
            f'Бот начал мониторинг комментариев на ваших курсах:\n'
            f'{stepik_courses_ids}\n'
            f'При каждом, не прошедшем фильтр комментарии, бот его удалит и '
            f'вышлет вам в ЛС данные.\n'
            f'Приятного полета 🫡')
    
    value = await msg.answer(text=text)
    await msg_processor.save_msg_id(value, msgs_for_del=True)
    logger_owners.debug('Exit')
