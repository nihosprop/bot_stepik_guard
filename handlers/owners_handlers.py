import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from filters.filters import AccessRightsFilter
from utils.utils import MessageProcessor, get_username
from keyboards.keyboards import kb_start

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
    
    text = (f'<b>Приветствую, {await get_username(msg)}!</b>\n\n'
            f'Бот начал мониторинг комментариев на ваших курсах:\n'
            f'{stepik_courses_ids}\n'
            f'При каждом, не прошедшем фильтр комментарии, бот его удалит и '
            f'вышлет вам в ЛС данные.\n\n'
            f'<pre>Для быстрого понимания важности комментов:\n'
            f'Зеленый кружок 🟡 - Вероятно информативный коммент.\n'
            f'Оранжевый кружок 🟢 - Вероятно не информативный коммент.</pre>\n'
            f'<b>Приятного полета</b> 🫡')
    
    value = await msg.answer(text=text, reply_markup=kb_start)
    
    await msg_processor.save_msg_id(value, msgs_for_del=True)
    logger_owners.debug('Exit')


@owners_router.callback_query(F.data.in_(['add_course_id', 'get_logs']))
async def in_development(clbk: CallbackQuery):
    logger_owners.debug('Entry')
    logger_owners.debug('Exit')
    await clbk.answer('Кнопка в разработке', show_alert=True)
