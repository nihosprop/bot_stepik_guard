import logging
from itertools import batched

from aiogram import F, Router
from aiogram.filters import StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

from filters.filters import AccessOwnersFilter, StepikIDFilter, TgUserIDFilter
from keyboards.kb_utils import create_message_settings_kb
from keyboards.keyboards import (kb_add_del_course,
                                 kb_add_del_user,
                                 kb_exit,
                                 kb_own_start,
                                 kb_settings_courses,
                                 kb_settings_users,
                                 kb_own_all_settings)
from states.states import (CoursesSettingsStates,
                           UsersSettingsStates,
                           AllSettingsStates)
from utils.redis_service import RedisService
from utils.utils import MessageProcessor, get_username

logger_owners = logging.getLogger(__name__)

owners_router = Router()

owners_router.message.filter(AccessOwnersFilter())
owners_router.callback_query.filter(AccessOwnersFilter())


@owners_router.message(F.text == '/users_info', StateFilter(default_state))
async def get_users_info_no_state(msg: Message,
                                  msg_processor: MessageProcessor,
                                  redis_service: RedisService):
    logger_owners.debug('Entry')
    await msg.delete()
    await msg_processor.deletes_messages(msgs_for_del=True)
    users_info: str = await redis_service.get_users_info()
    logger_owners.debug(f'{users_info=}')
    value = await msg.answer(
        text=users_info if users_info else 'База пуста',
        reply_markup=kb_exit,
        link_preview_options=LinkPreviewOptions(is_disabled=True))
    await msg_processor.save_msg_id(value, msgs_for_del=True)
    
    logger_owners.debug('Exit')


@owners_router.message(F.text == '/users_info', ~StateFilter(default_state))
async def get_users_info_in_state(msg: Message, msg_processor: MessageProcessor):
    logger_owners.debug('Entry')
    
    await msg.delete()
    value = await msg.answer(text='Завершите сначала действия')
    await msg_processor.deletes_msg_a_delay(value, delay=4, indication=True)
    logger_owners.debug('Exit')


@owners_router.callback_query(
    F.data == 'settings_users', StateFilter(default_state))
async def settings_users(clbk: CallbackQuery, state: FSMContext):
    logger_owners.debug('Entry')
    
    await clbk.message.edit_text(
        '📵\nЧтобы <b>добавить / удалить</b> юзера,'
        ' нажмите соответствующую кнопку и следуйте инструкциям.\n',
        reply_markup=kb_settings_users)
    await state.set_state(UsersSettingsStates.settings_users)
    await clbk.answer()
    
    logger_owners.debug('Exit')


@owners_router.callback_query(
    F.data == 'add_user', StateFilter(UsersSettingsStates.settings_users))
async def add_user(clbk: CallbackQuery,
                   state: FSMContext,
                   msg_processor: MessageProcessor):
    """
    Handler for the /add_user command.
    Adds a user to the list of users to monitor for comments.
    Args:
        msg_processor (MessageProcessor): An instance of the MessageProcessor
        class for deleting messages.
        clbk (CallbackQuery): The callback query object that triggered the
        command.
        state (FSMContext): An instance of the FSMContext class for managing
        state.
    """
    logger_owners.debug('Entry')
    
    text = ('📵\nОтправьте мне Telegram ID юзера.\n'
            'Узнать ID можно в боте:\n'
            '<a href="https://t.me/username_to_id_bot">IDBot</a>')
    value = await clbk.message.edit_text(text=text, reply_markup=kb_add_del_user)
    await msg_processor.save_msg_id(value=value, msgs_for_del=True)
    await state.set_state(UsersSettingsStates.fill_tg_user_id_add)
    await clbk.answer()
    
    logger_owners.debug('Exit')


@owners_router.callback_query(
    F.data == 'back', or_f(
        StateFilter(
            UsersSettingsStates.fill_tg_user_id_add), StateFilter(
            UsersSettingsStates.fill_tg_user_id_delete)))
async def back_from_add_del_user(clbk: CallbackQuery,
                                 state: FSMContext,
                                 msg_processor: MessageProcessor):
    """
    Handler for the /back command.
    Args:
        clbk (CallbackQuery): The callback query object that triggered the
        command.
        state (FSMContext): An instance of the FSMContext class for managing
        state.
        msg_processor (MessageProcessor): An instance of the MessageProcessor
        class for deleting messages.
    """
    
    logger_owners.debug('Entry')
    
    value = await clbk.message.edit_text(
        '📵\nЧтобы добавить / удалить юзера,'
        ' нажмите соответствующую кнопку и следуйте инструкциям.\n',
        reply_markup=kb_settings_users)
    await msg_processor.save_msg_id(value=value, msgs_for_del=True)
    await state.set_state(UsersSettingsStates.settings_users)
    await clbk.answer()
    
    logger_owners.debug('Exit')


@owners_router.message(
    TgUserIDFilter(), StateFilter(UsersSettingsStates.fill_tg_user_id_add))
async def fill_tg_user_id(msg: Message,
                          msg_processor: MessageProcessor,
                          redis_service: RedisService,
                          state: FSMContext):
    """
    Handler for filling in the user ID.
    
    Args:
        msg (Message): The message object that triggered the command.
        msg_processor (MessageProcessor): An instance of the MessageProcessor
            class for deleting messages.
        redis_service (RedisService): An instance of the RedisService class for
            working with Redis.
        state (FSMContext): An instance of the FSMContext class for managing
            state.
    """
    logger_owners.debug('Entry')
    
    tg_user_id = int(msg.text)
    await msg.delete()
    await msg_processor.deletes_messages(msgs_for_del=True)
    
    if await redis_service.check_user(tg_user_id=tg_user_id):
        value = await msg.answer(
            f'📵\nЮзер Telegram ID:{tg_user_id} уже есть в базе.',
            reply_markup=kb_add_del_user)
        await msg_processor.save_msg_id(value=value, msgs_for_del=True)
        return
    
    await redis_service.add_user(tg_user_id=tg_user_id)
    value = await msg.answer(
        f'Юзер TG_ID:{tg_user_id} успешно добавлен.\n'
        f'Может стартовать бота! 🚀🧑‍🚀\n\n', reply_markup=kb_own_start)
    await msg_processor.save_msg_id(value=value, msgs_for_del=True)
    await state.set_state(state=None)
    logger_owners.debug('Exit')


@owners_router.callback_query(
    F.data == 'delete_user', StateFilter(UsersSettingsStates.settings_users))
async def clbk_delete_user(clbk: CallbackQuery,
                           state: FSMContext,
                           msg_processor: MessageProcessor,
                           redis_service: RedisService):
    """
    Handler for the /delete_user command.
    Removes a user from the list of users to monitor for comments.
    Args:
        clbk (CallbackQuery): The callback query object that triggered the
            command.
        state (FSMContext): An instance of the FSMContext class for managing
            state.
        msg_processor (MessageProcessor): An instance of the MessageProcessor
            class for deleting messages.
        redis_service (RedisService): An instance of the RedisService class for
            working with Redis.
    """
    logger_owners.debug('Entry')
    
    users = await redis_service.get_users_info()
    
    text = (f'📵\nОтправьте мне Telegram ID юзера для удаления.\n'
            f'<code>\n{users if users else 'Юзеров в базе нет.'}</code>')
    value = await clbk.message.edit_text(text=text, reply_markup=kb_add_del_user)
    await msg_processor.save_msg_id(value=value, msgs_for_del=True)
    await state.set_state(UsersSettingsStates.fill_tg_user_id_delete)
    await clbk.answer()
    
    logger_owners.debug('Exit')


@owners_router.message(
    TgUserIDFilter(), StateFilter(UsersSettingsStates.fill_tg_user_id_delete))
async def confirm_remove_user(msg: Message,
                              msg_processor: MessageProcessor,
                              redis_service: RedisService,
                              state: FSMContext):
    logger_owners.debug('Entry')
    
    tg_user_id = int(msg.text)
    await msg.delete()
    await msg_processor.deletes_messages(msgs_for_del=True)
    
    if not await redis_service.check_user(tg_user_id=tg_user_id):
        value = await msg.answer(
            f'📵\nЮзер ID:{tg_user_id} не найден в базе.',
            reply_markup=kb_add_del_user)
        await msg_processor.save_msg_id(value=value, msgs_for_del=True)
        return
    
    await redis_service.remove_user(tg_user_id=tg_user_id)
    
    value = await msg.answer(
        f'Юзер TG_ID:{tg_user_id} успешно удален из базы.\n',
        reply_markup=kb_own_start)
    await msg.bot.send_message(
        chat_id=tg_user_id, text=f'{await get_username(msg)} Вас кикнул 😞')
    await msg_processor.save_msg_id(value=value, msgs_for_del=True)
    await state.set_state(state=None)
    
    logger_owners.debug('Exit')


@owners_router.callback_query(
    F.data == 'settings_courses', StateFilter(default_state))
async def settings_courses(clbk: CallbackQuery, state: FSMContext):
    logger_owners.debug('Entry')
    
    await clbk.message.edit_text(
        '📵\nЧтобы <b>добавить / удалить</b> курс,'
        ' нажмите соответствующую кнопку и следуйте инструкциям.\n',
        reply_markup=kb_settings_courses)
    await state.set_state(CoursesSettingsStates.settings_courses)
    await clbk.answer()
    
    logger_owners.debug('Exit')


@owners_router.callback_query(
    F.data == 'add_course', StateFilter(
        CoursesSettingsStates.settings_courses))
async def add_stepik_course(clbk: CallbackQuery,
                            state: FSMContext,
                            msg_processor: MessageProcessor):
    logger_owners.debug('Entry')
    
    text = '📵\nОтправьте мне ID курса Stepik.'
    value = await clbk.message.edit_text(
        text=text, reply_markup=kb_add_del_course)
    await msg_processor.save_msg_id(value=value, msgs_for_del=True)
    await state.set_state(CoursesSettingsStates.fill_course_id_add)
    await clbk.answer()
    
    logger_owners.debug('Exit')


@owners_router.message(
    StepikIDFilter(), StateFilter(CoursesSettingsStates.fill_course_id_add))
async def fill_course_stepik_id(msg: Message,
                                redis_service: RedisService,
                                msg_processor: MessageProcessor):
    logger_owners.debug('Entry')
    
    course_id = int(msg.text)
    await msg.delete()
    
    await msg_processor.deletes_messages(msgs_for_del=True)
    
    result: str = await redis_service.add_stepik_course_id(course_id=course_id)
    if result == 'added':
        course_title = await redis_service.stepik_client.get_course_title(
            course_id=course_id)
        await msg.answer(
            f'📵\nКурс ID {course_id}:\n<b>{course_title}</b> '
            f'добавлен для отслеживания.', reply_markup=kb_add_del_course)
        return
    
    value = await msg.answer(text='📵\n' + result, reply_markup=kb_add_del_course)
    await msg_processor.save_msg_id(value=value, msgs_for_del=True)
    
    logger_owners.debug('Exit')


@owners_router.callback_query(
    F.data == 'back', or_f(
        StateFilter(
            CoursesSettingsStates.fill_course_id_add,
            CoursesSettingsStates.fill_course_id_delete)))
async def back_from_add_del_course(clbk: CallbackQuery, state: FSMContext):
    logger_owners.debug('Entry')
    
    await clbk.message.edit_text(
        '📵\nЧтобы <b>добавить / удалить</b> курс,'
        ' нажмите соответствующую кнопку и следуйте инструкциям.\n',
        reply_markup=kb_settings_courses)
    await state.set_state(CoursesSettingsStates.settings_courses)
    await clbk.answer()
    
    logger_owners.debug('Exit')


@owners_router.callback_query(
    F.data == 'delete_course', StateFilter(
        CoursesSettingsStates.settings_courses))
async def clbk_delete_course(clbk: CallbackQuery,
                             state: FSMContext,
                             redis_service: RedisService,
                             msg_processor: MessageProcessor):
    logger_owners.debug('Entry')
    
    data = await redis_service.get_courses_ids()
    _bat = tuple(' '.join(x) for x in batched(map(str, data), 3))
    stepik_courses_ids = '\n'.join(_bat)
    
    text = (f'📵\nОтправьте мне ID курса Stepik для удаления.\n'
            f'<code>\n{stepik_courses_ids if stepik_courses_ids else 'Курсов в базе нет.'}</code>')
    
    value = await clbk.message.edit_text(
        text=text, reply_markup=kb_add_del_course)
    await msg_processor.save_msg_id(value=value, msgs_for_del=True)
    await state.set_state(CoursesSettingsStates.fill_course_id_delete)
    await clbk.answer()
    logger_owners.debug('Exit')


@owners_router.message(StateFilter(CoursesSettingsStates.fill_course_id_delete))
async def clbk_confirm_remove_course(msg: Message,
                                     state: FSMContext,
                                     msg_processor: MessageProcessor,
                                     redis_service: RedisService):
    logger_owners.debug('Entry')
    
    course_id = int(msg.text)
    await msg.delete()
    
    data = await redis_service.get_courses_ids()
    _bat = tuple(' '.join(x) for x in batched(map(str, data), 3))
    stepik_courses_ids = '\n'.join(_bat)
    
    await msg_processor.deletes_messages(msgs_for_del=True)
    
    if await redis_service.remove_stepik_course_id(course_id=course_id):
        value = await msg.answer(
            f'Курс ID:{course_id} успешно удален из базы.\n',
            reply_markup=kb_own_start)
        await msg_processor.save_msg_id(value=value, msgs_for_del=True)
        await state.set_state(state=None)
        logger_owners.debug('Exit')
        return
    
    value = await msg.answer(
        f'📵\nКурс ID:{course_id} не найден в базе.\n'
        f'Попробуй еще разок 🤓:\n'
        f'<code>\n{stepik_courses_ids}</code>', reply_markup=kb_add_del_course)
    await msg_processor.save_msg_id(value=value, msgs_for_del=True)
    logger_owners.debug('Exit')
    return


@owners_router.callback_query(F.data == 'messages')
async def clbk_messages_settings(clbk: CallbackQuery,
                                 state: FSMContext,
                                 redis_service: RedisService):
    logger_owners.debug('Entry')
    
    msgs_settings = await redis_service.get_msgs_settings()
    kb = await create_message_settings_kb(message_settings=msgs_settings)
    
    await clbk.message.edit_text(
        text=f'<b>📵 Настройки токсичных комментариев Stepik\n</b>'
             f'<pre>\nУдалять токсичные:'
             f' {('OFF', 'ON')[msgs_settings.get('remove_toxic')]}</pre>',
        reply_markup=kb)
    await state.set_state(AllSettingsStates.settings_toxic_msgs)
    await clbk.answer()
    logger_owners.debug('Exit')
    
@owners_router.callback_query(F.data.in_(['on_remove_toxic',
                                          'off_remove_toxic']),
                              StateFilter(AllSettingsStates.settings_toxic_msgs))
async def clbk_toxic_setting_toggle(clbk: CallbackQuery,
                                    redis_service: RedisService):
    logger_owners.debug('Entry')
    
    msgs_settings: dict[str, bool] = await redis_service.get_msgs_settings()
    new_settings_flag: bool = not msgs_settings.get('remove_toxic', False)
    
    await redis_service.update_msgs_settings(remove_toxic_flag=new_settings_flag)
    
    new_msgs_settings = await redis_service.get_msgs_settings()
    kb = await create_message_settings_kb(message_settings=new_msgs_settings)
    await clbk.message.edit_text(
        text=f'<b>📵 Настройки токсичных комментариев Stepik\n</b>'
             f'<pre>\nУдалять токсичные:'
             f' {('OFF', 'ON')[new_msgs_settings.get('remove_toxic')]}</pre>',
        reply_markup=kb)
    await clbk.answer()
    logger_owners.info(f'Настройки удаления токсичных комментариев изменены'
                       f' {await get_username(clbk)} на {new_settings_flag}')
    logger_owners.debug('Exit')

