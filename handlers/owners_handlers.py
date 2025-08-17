import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery

from filters.filters import AccessRightsFilter
from keyboards.keyboards import kb_own_start, kb_settings_users
from states.states import UsersSettingsStates
from utils.utils import MessageProcessor, get_username

logger_owners = logging.getLogger(__name__)

owners_router = Router()

owners_router.message.filter(AccessRightsFilter())
owners_router.callback_query.filter(AccessRightsFilter())


@owners_router.callback_query(F.data == '/cancel', ~StateFilter(default_state))
async def cancel_callback(clbk: CallbackQuery,
                          state: FSMContext,
                          msg_processor: MessageProcessor,
                          stepik_courses_ids: list[int]):
    logger_owners.debug('Entry')
    
    text = (f'<b>Приветствую, {await get_username(clbk)}!</b>\n'
            f'Бот отслеживает курсы Stepik:\n'
            f'{stepik_courses_ids}\n'
            f'<b>Важность комментов обозначена кружками:</b>\n'
            f'<pre>Зеленый кружок 🟢 - Вероятно информативный.\n'
            f'Желтый кружок 🟡 - Вероятно НЕ информативный.</pre>\n'
            f'<b>Приятного полета</b> 🫡')
    await state.clear()
    value = await clbk.message.edit_text(text=text, reply_markup=kb_own_start)
    await msg_processor.save_msg_id(value=value, msgs_for_del=True)
    await clbk.answer()
    logger_owners.debug('Exit')


@owners_router.callback_query(F.data == 'settings_users',
                              StateFilter(default_state))
async def settings_users(clbk: CallbackQuery, state: FSMContext):
    logger_owners.debug('Entry')
    
    await clbk.message.edit_text(
        'Чтобы добавить / удалить юзера,'
        ' нажмите соответствующую кнопку и следуйте инструкциям.\n',
        reply_markup=kb_settings_users)
    await state.set_state(UsersSettingsStates.settings_users)
    await clbk.answer()
    
    logger_owners.debug('Exit')

@owners_router.callback_query(
    F.data == 'add_user', StateFilter(UsersSettingsStates.settings_users))
async def add_user(clbk: CallbackQuery, state: FSMContext):
    """
    Handler for the /add_user command.
    Adds a user to the list of users to monitor for comments.
    Args:
        clbk (CallbackQuery): The callback query object that triggered the
        command.
        state (FSMContext): An instance of the FSMContext class for managing
        state.
    """
    logger_owners.debug('Entry')
    
    text = ('Отправьте мне ID юзера.\n'
            'Узнать ID можно в боте:\n'
            '<a href="https://t.me/username_to_id_bot">IDBot</a>')
    await clbk.message.edit_text(text=text, reply_markup=kb_add_user)
    await state.set_state(UsersSettingsStates.add_user)
    await clbk.answer()
    
    logger_owners.debug('Exit')

@owners_router.callback_query(F.data == 'back', StateFilter(
    UsersSettingsStates.add_user))
async def back_from_add_user(clbk: CallbackQuery, state: FSMContext):
    """
    Handler for the /back command.
    Returns to the main menu.
    Args:
        clbk (CallbackQuery): The callback query object that triggered the
        command.
        state (FSMContext): An instance of the FSMContext class for managing
        state.
    """
    
    logger_owners.debug('Entry')
    
    await clbk.message.edit_text(
        'Чтобы добавить / удалить юзера,'
        ' нажмите соответствующую кнопку и следуйте инструкциям.\n',
        reply_markup=kb_settings_users)
    await state.set_state(UsersSettingsStates.settings_users)
    await clbk.answer()
    
    logger_owners.debug('Exit')



@owners_router.message(
    TgUserIDFilter(), StateFilter(UsersSettingsStates.add_user))
async def fill_tg_user_id(msg: Message, state: FSMContext):
    logger_owners.debug('Entry')
    
    await msg.answer('ID записан. Теперь отправьте мне никнейм юзера.')
    await state.set_state(UsersSettingsStates.add_user_nickname)
    
    logger_owners.debug('Exit')


@owners_router.callback_query(F.data == 'del_user')
async def del_user(clbk: CallbackQuery):
    logger_owners.debug('Entry')
    await clbk.answer('Кнопка в разработке', show_alert=True)
    logger_owners.debug('Exit')


@owners_router.callback_query(F.data == 'settings_courses')
async def settings_courses(clbk: CallbackQuery):
    logger_owners.debug('Entry')
    await clbk.answer('Кнопка в разработке', show_alert=True)
    logger_owners.debug('Exit')
