import logging
from itertools import batched

from aiogram import F, Router
from aiogram.filters import StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message

from filters.filters import AccessOwnersFilter, AccessUsersFilter
from keyboards.kb_utils import create_notification_settings_kb
from keyboards.keyboards import (kb_own_all_settings,
                                 kb_own_start,
                                 kb_user_all_settings,
                                 kb_user_start)
from states.states import AllSettingsStates
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
    
    data = await redis_service.get_courses_ids()
    _bat = tuple(' '.join(x) for x in batched(map(str, data), 3))
    stepik_courses_ids = '\n'.join(_bat)
    
    text = (f'<b>Мониторю курсы Stepik:</b>\n'
            f'<pre>\n{stepik_courses_ids if stepik_courses_ids else '<i>Пока нет курсов для отслеживания</i>'}</pre>\n')
    
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
    
    data = await redis_service.get_courses_ids()
    _bat = tuple(' '.join(x) for x in batched(map(str, data), 3))
    
    text = (f'<b>Приветствую, {await get_username(msg)}!</b>\n'
            f'<b>Статусы комментов обозначены кружками:</b>\n'
            f'<pre>Зеленый кружок 🟢 - Вероятно информативный.\n'
            f'Желтый кружок 🟡  - Вероятно НЕ информативный.\n'
            f'Белый кружок ⚪ - Решение</pre>\n'
            f'Отключить не нужные уведомления можно в настройках.\n'
            f'Важно❗\n'
            f'Пока вы взаимодействуете с ботом, уведомления о комментариях'
            f' не приходят. Это состояние будет обозначено значком: 📵\n'
            f'По этому после завершения операций - выйдите из диалога'
            f' нажав <b>Отмена</b>, <b>Выход</b> или'
            f' <b>/start</b>\n\n'
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
        await redis_service.update_user_username(
            tg_user_id=user_tg_id, tg_nickname=tg_nickname)
        logger.info(f'User {tg_nickname} updated.')
    await state.set_state(None)
    
    logger.debug(f'State clear:{tg_nickname}:{user_tg_id}')
    logger.debug('Exit')


@user_router.callback_query(
    F.data == 'all_settings', StateFilter(default_state))
async def clbk_settings(clbk: CallbackQuery,
                        state: FSMContext,
                        owners: list[int]):
    logger.debug('Entry')
    
    kb = (kb_user_all_settings, kb_own_all_settings)[clbk.from_user.id in owners]
    await clbk.message.edit_text(
        '📵 <b>Выберите настройку:</b>', reply_markup=kb)
    await state.set_state(AllSettingsStates.user_settings)
    await clbk.answer()
    
    logger.debug('Exit')


@user_router.callback_query(
    F.data == 'notifications', StateFilter(AllSettingsStates.user_settings))
async def clbk_notif(clbk: CallbackQuery,
                     state: FSMContext,
                     redis_service: RedisService):
    logger.debug('Entry')
    
    user_id = clbk.from_user.id
    
    if not await redis_service.check_user(user_id):
        await redis_service.add_user(user_id)
    
    user_notif = await redis_service.get_user_notif(user_id)
    logger.debug(f'{user_notif=}')
    kb_notif = await create_notification_settings_kb(user_notif)
    
    await clbk.message.edit_text(
        f'<b>📵🔔 Настройки уведомлений:\n</b>'
        f'<pre>\nРешения: {('OFF', 'ON')[user_notif.get('is_notif_solution')]}\n'
        f'Не информативные : {('OFF', 'ON')[user_notif.get(
            'is_notif_uninformative')]}</pre>', reply_markup=kb_notif)
    await state.set_state(AllSettingsStates.settings_notif)
    await clbk.answer()
    
    logger.debug('Exit')


@user_router.callback_query(
    F.data == 'back', StateFilter(AllSettingsStates.settings_notif))
async def clbk_notif_back(clbk: CallbackQuery,
                          state: FSMContext,
                          owners: list[int]):
    logger.debug('Entry')
    
    kb = (kb_user_all_settings, kb_own_all_settings)[clbk.from_user.id in owners]
    await clbk.message.edit_text(
        '📵 <b>Выберите настройку:</b>', reply_markup=kb)
    await state.set_state(AllSettingsStates.user_settings)
    await clbk.answer()
    
    logger.debug('Exit')


@user_router.callback_query(
    F.data.in_(
        [
            'on_notif_solution',
            'off_notif_solution',
            'on_notif_uninformative',
            'off_notif_uninformative']),
    StateFilter(AllSettingsStates.settings_notif))
async def clbk_toggle_notification(clbk: CallbackQuery,
                                   redis_service: RedisService):
    """
    Обработчик переключения настроек уведомлений.
    """
    logger.debug('Entry')
    
    user_id = clbk.from_user.id
    if clbk.data in ['on_notif_solution', 'off_notif_solution']:
        setting = 'is_notif_solution'
        new_value = clbk.data.startswith('on_')
    else:
        setting = 'is_notif_uninformative'
        new_value = clbk.data.startswith('on_')
    
    await redis_service.update_notif_flag(
        tg_user_id=user_id, **{setting: new_value})
    logger.info(
        f'Notification for {await get_username(clbk)}:{setting} '
        f'updated.')
    user_notif = await redis_service.get_user_notif(user_id)
    
    kb_notif = await create_notification_settings_kb(user_notif)
    await clbk.message.edit_text(
        f'<b>📵🔔 Настройки уведомлений:\n</b>'
        f'<pre>\nРешения: {('OFF', 'ON')[user_notif.get('is_notif_solution')]}\n'
        f'Не информативные : {('OFF', 'ON')[user_notif.get(
            'is_notif_uninformative')]}</pre>', reply_markup=kb_notif)
    await clbk.answer()
    
    logger.debug('Exit')


@user_router.callback_query(StateFilter(AllSettingsStates.user_settings))
async def clbk_other_handler(clbk: CallbackQuery):
    """
    Обработчик для нераспознанных callback'ов в состоянии настроек.
    """
    logger.debug('Entry')
    logger.debug(f'Unhandled callback in user_settings state: {clbk.data=}')
    logger.debug('Exit')


@user_router.message()
async def msg_other(msg: Message):
    logger.debug('Entry')
    await msg.delete()
    logger.debug('Exit')
