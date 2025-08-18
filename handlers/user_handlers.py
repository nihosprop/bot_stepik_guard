import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from filters.filters import AccessRightsFilter
from keyboards.keyboards import kb_user_start, kb_own_start
from utils.utils import MessageProcessor, get_username

logger = logging.getLogger(__name__)

user_router = Router()

user_router.message.filter(AccessRightsFilter(flag_users=True))
user_router.callback_query.filter(AccessRightsFilter(flag_users=True))


@user_router.message(F.text.in_(['/start', '/cancel', 'exit']))
async def cmd_start(msg: Message,
                    msg_processor: MessageProcessor,
                    owners: list[int],
                    stepik_courses_ids: list[int],
                    state: FSMContext) -> None:
    """
    Handler for the /start command.

    Sends a welcome message to the user and starts monitoring comments on the
    courses specified in the `stepik_courses_ids` list.

    Args:
        redis_service (RedisService): An instance of the RedisService class for
            working with Redis.
        owners (list[int]): A list of owner IDs
        msg (Message): The message object that triggered the /start command
        msg_processor (MessageProcessor): An instance of the MessageProcessor
            class for deleting messages
        stepik_courses_ids (list[int]): A list of course IDs to monitor for
            comments.
        state (FSMContext): An instance of the FSMContext class for managing
            state.
    Returns:
        None
    """
    logger.debug('Entry')
    
    await msg.delete()
    await msg_processor.deletes_messages(msgs_for_del=True)
    
    text = (f'<b>Приветствую, {await get_username(msg)}!</b>\n'
            f'Бот отслеживает курсы Stepik:\n'
            f'{stepik_courses_ids}\n'
            f'<b>Важность комментов обозначена кружками:</b>\n'
            f'<pre><b>Зеленый кружок</b> 🟢 - Вероятно информативный.\n'
            f'<b>Желтый кружок</b> 🟡 - Вероятно НЕ информативный.</pre>\n'
            f'События могут приходить совместно с вашими операциями в боте, '
            f'по этому просто вернитесь к своей операции и продолжите '
            f'взаимодействие с ботом.\n\n'
            f'<b>Приятного полета</b> 🫡')
    
    user_tg_id = msg.from_user.id
    keyboard = kb_user_start if user_tg_id not in owners else kb_own_start
    value = await msg.answer(text=text, reply_markup=keyboard)
    await msg_processor.save_msg_id(value, msgs_for_del=True)
    
    # TODO:
    if user_tg_id in owners:
        await redis_service.add_owner(tg_user_id=user_tg_id,
                                      tg_nickname=await get_username(msg))

    await state.set_state(None)
    logger.debug(f'State clear: {await get_username(msg)}:{msg.from_user.id}')

    logger.debug('Exit')


@user_router.callback_query(F.data.in_(['all_settings']))
async def shut(clbk: CallbackQuery):
    logger.debug('Entry')
    await clbk.answer('Кнопка в разработке', show_alert=True)
    logger.debug('Exit')
