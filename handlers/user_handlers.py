import logging
from itertools import batched

from aiogram import F, Router
from aiogram.filters import or_f
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from filters.filters import AccessOwnersFilter, AccessUsersFilter
from keyboards.keyboards import kb_own_start, kb_user_start
from utils.redis_service import RedisService
from utils.utils import MessageProcessor, get_username

logger = logging.getLogger(__name__)

user_router = Router()

user_router.message.filter(
    or_f(
        AccessOwnersFilter(), AccessUsersFilter()))
user_router.callback_query.filter(
    or_f(
        AccessOwnersFilter(), AccessUsersFilter()))


@user_router.callback_query(F.data.in_(['/cancel', '/exit']))
async def clbk_cancel(clbk: CallbackQuery,
                      owners: list[int],
                      msg_processor: MessageProcessor,
                      redis_service: RedisService,
                      state: FSMContext) -> None:
    """
    Handler for the /cancel and /exit callback commands.
    
    Args:
        clbk (CallbackQuery): The callback query object that triggered the
            /cancel or /exit command
        msg_processor (MessageProcessor): An instance of the MessageProcessor
            class for deleting messages.
        redis_service (RedisService): An instance of the RedisService class for
            working with Redis.
        state (FSMContext): An instance of the FSMContext class for managing
            state.
        owners (list[int]): A list of owner IDs.
    """
    logger.debug('Entry')
    
    data = await redis_service.get_stepik_courses_ids()
    _bat = tuple(' '.join(x) for x in batched(map(str, data), 3))
    stepik_courses_ids = '\n'.join(_bat)
    
    text = (f'<b>Мониторю курсы Stepik:</b>\n'
            f'<pre>\n{stepik_courses_ids if stepik_courses_ids else
            '<i>Пока нет курсов для отслеживания</i>'}</pre>\n')
    
    user_tg_id = clbk.from_user.id
    keyboard = kb_user_start if user_tg_id not in owners else kb_own_start
    
    value = await clbk.message.edit_text(text=text, reply_markup=keyboard)
    await msg_processor.save_msg_id(value, msgs_for_del=True)

    await state.set_state(state=None)
    await clbk.answer()
    
    logger.debug(f'State clear:{await get_username(clbk)}:{clbk.from_user.id}')
    logger.debug('Exit')


@user_router.message(F.text == '/start')
async def cmd_start(msg: Message,
                    msg_processor: MessageProcessor,
                    redis_service: RedisService,
                    owners: list[int],
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
        state (FSMContext): An instance of the FSMContext class for managing
            state.
    """
    logger.debug('Entry')
    
    await msg_processor.deletes_messages(msgs_for_del=True)
    
    data = await redis_service.get_stepik_courses_ids()
    _bat = tuple(' '.join(x) for x in batched(map(str, data), 3))
    stepik_courses_ids = '\n'.join(_bat)
    
    text = (f'<b>Приветствую, {await get_username(msg)} !</b>\n'
            f'Мониторю курсы Stepik:\n'
            f'<pre>\n{stepik_courses_ids if stepik_courses_ids else
                '\n<i>Пока нет курсов для отслеживания</i>\n'}</pre>\n\n'
            f'<b>Важность комментов обозначена кружками:</b>\n'
            f'<pre><b>Зеленый кружок</b> 🟢 - Вероятно информативный.\n\n'
            f'<b>Желтый кружок</b> 🟡  - Вероятно НЕ информативный.</pre>\n'
            f'Важно❗\n'
            f'Пока вы взаимодействуете с ботом, уведомления о комментариях'
            f' не приходят. Это состояние будет обозначено значком: 📵\n'
            f'По этому после завершения операций - выйдите из диалога'
            f' нажав <b>Отмена</b>, <b>Выход</b> или'
            f' <b>/start</b>(в боковом меню)\n\n'
            f'<b>Приятного полета</b> 🫡')
    
    user_tg_id = msg.from_user.id
    tg_nickname: str = await get_username(msg)

    keyboard = kb_user_start if user_tg_id not in owners else kb_own_start
    value = await msg.answer(text=text, reply_markup=keyboard)
    await msg_processor.save_msg_id(value, msgs_for_del=True)
    
    if user_tg_id in owners:
        await redis_service.add_owner(
            tg_user_id=user_tg_id, tg_nickname=tg_nickname)
    
    if await redis_service.check_user(tg_user_id=user_tg_id):
        await redis_service.update_user_username(tg_user_id=user_tg_id,
                                                 tg_nickname=tg_nickname)
        logger.info(f'User {tg_nickname} updated.')
    await state.set_state(None)

    logger.debug(f'State clear:{tg_nickname}:{user_tg_id}')
    logger.debug('Exit')

@user_router.callback_query()
async def clbk_other_handler(clbk: CallbackQuery):
    logger.debug('Entry')
    logger.debug(f'{clbk.data=}')
    
    await clbk.answer('Кнопка в разработке', show_alert=True)
    
    logger.debug('Exit')

@user_router.message()
async def msg_other(msg: Message):
    logger.debug('Entry')
    
    await msg.delete()
    
    logger.debug('Exit')
    
