import logging

from aiogram import F, Router
from aiogram.types import Message

from filters.filters import AccessRightsFilter
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
    """Handler for the /start command.

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
    value = await msg.answer(
        f'Приветствую, {await get_username(msg)}!\n'
        f'Бот отслеживает курсы Stepik:\n'
        f'{stepik_courses_ids}\n'
        f'Важность комментов обозначена кружками:\n'
        f'<pre>Зеленый кружок 🟢 - Вероятно информативный.\n'
        f'Красный кружок 🔴 - Вероятно НЕ информативный.</pre>\n')
    
    await msg_processor.save_msg_id(value, msgs_for_del=True)
    logger.debug('Exit')
