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
            class for deleting messages
        stepik_courses_ids (list[int]): A list of course IDs to monitor for
            comments
    Returns:
        None
    """
    logger.debug('Entry')
    
    await msg_processor.deletes_messages(msgs_for_del=True)
    
    text = (f'<b>Приветствую, {await get_username(msg)}!</b>\n'
            f'Stepik курсы, которые бот мониторит:\n'
            f'{stepik_courses_ids}\n'
            f'При каждом, не прошедшем фильтр комментарии, бот его удалит и '
            f'вышлет вам в ЛС данные с пометкой "УДАЛЕНО".\n\n'
            f'Для быстрого понимания важности комментов:\n'
            f'<pre>Зеленый кружок 🟢 - Вероятно информативный коммент.\n'
            f'Желтый кружок 🟡 - Вероятно НЕ информативный коммент.</pre>\n'
            f'<b>Приятного полета</b> 🫡')
    
    value = await msg.answer(text=text, reply_markup=kb_start)
    
    await msg_processor.save_msg_id(value, msgs_for_del=True)
    logger.debug('Exit')
