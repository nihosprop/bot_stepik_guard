import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message

from filters.filters import AccessOwnersFilter, TgUserIDFilter
from keyboards.keyboards import (kb_add_user, kb_exit, kb_settings_users)
from states.states import UsersSettingsStates
from utils.redis_service import RedisService
from utils.utils import MessageProcessor

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
    value = await msg.answer(text=users_info, reply_markup=kb_exit)
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
        'Чтобы <b>добавить / удалить</b> юзера,'
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
    await state.set_state(UsersSettingsStates.fill_tg_user_id)
    await clbk.answer()
    
    logger_owners.debug('Exit')


@owners_router.callback_query(
    F.data == 'back', StateFilter(
        UsersSettingsStates.fill_tg_user_id))
async def back_from_add_user(clbk: CallbackQuery,
                             state: FSMContext,
                             msg_processor: MessageProcessor):
    """
    Handler for the /back command.
    Returns to the main menu.
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
        'Чтобы добавить / удалить юзера,'
        ' нажмите соответствующую кнопку и следуйте инструкциям.\n',
        reply_markup=kb_settings_users)
    await msg_processor.save_msg_id(value=value, msgs_for_del=True)
    await state.set_state(UsersSettingsStates.settings_users)
    await clbk.answer()
    
    logger_owners.debug('Exit')


@owners_router.message(
    TgUserIDFilter(), StateFilter(UsersSettingsStates.fill_tg_user_id))
async def fill_tg_user_id(msg: Message,
                          msg_processor: MessageProcessor,
                          redis_service: RedisService):
    """
    Handler for filling in the user ID.
    
    Args:
        msg (Message): The message object that triggered the command.
        msg_processor (MessageProcessor): An instance of the MessageProcessor
            class for deleting messages.
        redis_service (RedisService): An instance of the RedisService class for
            working with Redis.
    """
    logger_owners.debug('Entry')
    
    tg_user_id = int(msg.text)
    await msg.delete()
    await msg_processor.deletes_messages(msgs_for_del=True)

    if await redis_service.check_user(tg_user_id=tg_user_id):
        value = await msg.answer(f'Юзер ID:{tg_user_id} уже есть в базе.',
                                 reply_markup=kb_add_user)
        await msg_processor.save_msg_id(value=value, msgs_for_del=True)
        return
        
    await redis_service.add_user(tg_user_id=tg_user_id)
    value = await msg.answer(
        f'Юзер TG_ID:{tg_user_id} успешно добавлен.\n'
        f'Может стартовать бота! 🚀🧑‍🚀\n\n',
        reply_markup=kb_exit)
    await msg_processor.save_msg_id(value=value, msgs_for_del=True)
    
    logger_owners.debug('Exit')
