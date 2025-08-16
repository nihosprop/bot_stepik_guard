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


@owners_router.message(F.text == '/start')
async def cmd_start(msg: Message,
                    msg_processor: MessageProcessor,
                    stepik_courses_ids: list[int]) -> None:
    """
    Handler for the /start command.
    Sends a welcome message to the user and starts monitoring comments on the
    courses specified in the `stepik_courses_ids` list.
    Args:
        msg (Message): The message object that triggered the /start command
        msg_processor (MessageProcessor): An instance of the MessageProcessor
            class for deleting messages.
        stepik_courses_ids (list[int]): A list of course IDs to monitor for
            comments.
    """
    logger_owners.debug('Entry')
    
    await msg_processor.deletes_messages(msgs_for_del=True)
    
    text = (f'<b>Приветствую, {await get_username(msg)}!</b>\n'
            f'Бот отслеживает курсы Stepik:\n'
            f'{stepik_courses_ids}\n'
            f'<b>Важность комментов обозначена кружками:</b>\n'
            f'<pre>Зеленый кружок 🟢 - Вероятно информативный.\n'
            f'Красный кружок 🔴 - Вероятно НЕ информативный.</pre>\n'
            f'<b>Приятного полета</b> 🫡')
    
    value = await msg.answer(text=text, reply_markup=kb_add_course)
    
    await msg_processor.save_msg_id(value, msgs_for_del=True)
    logger_owners.debug('Exit')


@owners_router.callback_query(F.data.in_(['add_course']))
async def in_development(clbk: CallbackQuery):
    logger_owners.debug('Entry')
    await clbk.answer('Кнопка в разработке', show_alert=True)
    logger_owners.debug('Exit')
