import asyncio
import logging
import re
import html

from dataclasses import dataclass

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatFullInfo, Message, Update

logger_utils = logging.getLogger(__name__)


async def get_username(_type_update: Message | CallbackQuery | ChatFullInfo) -> str:
    
    if isinstance(_type_update, ChatFullInfo):
        if username := _type_update.username:
            return f'@{username}'
        elif first_name := _type_update.first_name:
            return first_name
        return 'Anonymous'
    
    if username := _type_update.from_user.username:
        return f'@{username}'
    elif first_name := _type_update.from_user.first_name:
        return first_name
    return 'Anonymous'

def clean_html_tags(raw_html: str) -> str:
    """Удаляет HTML-теги из строки, оставляя только текст."""
    
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    clean_text = html.unescape(clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    return clean_text.strip()

@dataclass
class MessageProcessor:
    """
    Class for managing and processing chat messages.

    _message (Message | CallbackQuery): The message or callback query object.
    _state (FSMContext): The finite state machine context.
    """
    _type_update: Message | CallbackQuery
    _state: FSMContext
    
    async def deletes_messages(self,
                               msgs_for_del=False,
                               msgs_remove_kb=False) -> None:
        """
        Deleting messages from chat based on passed parameters.
        This method removes various types of messages from a chat.
        Messages are deleted only if the corresponding parameters
        are set to True.
        If no parameters are specified, the method does not perform any
        actions.
        :param msgs_for_del: bool
        :param msgs_remove_kb: bool
        :return: None
        """
        logger_utils.debug(f'Entry')
        
        if hasattr(self._type_update, 'message') and self._type_update.message:
            chat_id = self._type_update.message.chat.id
        elif (hasattr(
            self._type_update,
            'callback_query') and self._type_update.callback_query):
            chat_id = self._type_update.callback_query.message.chat.id
        else:
            logger_utils.error('Неподдерживаемый тип апдейта')
            return
        
        kwargs: dict = {
            "msgs_for_del": msgs_for_del,
            "msgs_remove_kb": msgs_remove_kb}
        
        keys = [key for key, val in kwargs.items() if val]
        logger_utils.debug(f'{keys=}')
        
        if keys:
            for key in keys:
                msgs_ids: list = dict(await self._state.get_data()).get(key, [])
                logger_utils.debug(f'Starting to delete messages…')
                
                for msg_id in set(msgs_ids):
                    try:
                        await self._type_update.bot.delete_message(
                            chat_id=chat_id, message_id=msg_id)
                    except Exception as err:
                        logger_utils.warning(
                            f'Failed to delete message with id {msg_id=}: '
                            f'{err=}')
                await self._state.update_data({key: []})
        
        logger_utils.debug('Exit')
    
    async def save_msg_id(self,
                          value: Message | CallbackQuery,
                          msgs_for_del=False,
                          msgs_remove_kb=False) -> None:
        """
        The writes_msg_id_to_storage method is intended for writing an identifier
        messages in the store depending on the values of the passed flags.
        It analyzes the method signature, determines the parameters with the set
        defaults to True, and then stores the message ID
        in the corresponding list in the object's state.
        After the recording process is completed, a success message is logged.
        completion of the operation.
        :param value: Message | CallbackQuery
        :param msgs_for_del: bool
        :param msgs_remove_kb: bool
        :return: None
        """
        logger_utils.debug('Entry')
        
        flags: dict = {
            'msgs_for_del': msgs_for_del,
            'msgs_remove_kb': msgs_remove_kb}
        
        for key, val in flags.items():
            logger_utils.debug('Start writing data to storage…')
            if val:
                data: list = dict(await self._state.get_data()).get(key, [])
                if value.message_id not in data:
                    data.append(str(value.message_id))
                    logger_utils.debug(f'Msg ID to recorded')
                logger_utils.debug('No msg ID to record')
                await self._state.update_data({key: data})
        logger_utils.debug('Exit')
    
    async def removes_inline_kb(self, key='msgs_remove_kb') -> None:
        """
        Removes built-in keyboards from messages.
        This function gets message IDs from the state and removes
        built-in keyboards from these messages. After removing the keyboards,
        the state is updated to clear the list of message IDs.
        Logs:
            — Start the keyboard removal process.
            — Errors when removing the keyboard.
            — Successful completion of the keyboard removal process.
        :param key: Str
        :return: None
        """
        logger_utils.debug('Entry')
        
        msgs: list = dict(await self._state.get_data()).get(key, [])
        
        if isinstance(self._type_update, Message):
            chat_id = self._type_update.chat.id
        else:
            chat_id = self._type_update.message.chat.id
        
        for msg_id in set(msgs):
            try:
                await self._type_update.bot.edit_message_reply_markup(
                    chat_id=chat_id, message_id=msg_id)
            except TelegramBadRequest as err:
                logger_utils.error(f'{err}', stack_info=True)
        logger_utils.debug('Keyboard removed')
        await self._state.update_data({key: []})
        
        logger_utils.debug('Exit')
    
    async def delete_message(self, key='msg_del_on_key') -> None:
        """
        Удаляет сообщение, используя указанный ключ. Метод извлекает данные из
        состояния и использует их для удаления сообщения с указанным ключом.
        Args: key (str): Ключ, по которому будет найдено сообщение
        удаление. По умолчанию «msg_id_for_del». Возвращает: None.
        :param key: str
        :return: None
        """
        logger_utils.debug('Entry')
        try:
            chat_id = None
            data = await self._state.get_data()
            if isinstance(self._type_update, Message):
                chat_id = self._type_update.chat.id
            elif isinstance(self._type_update, CallbackQuery):
                if self._type_update.message:
                    chat_id = self._type_update.message.chat.id
                else:
                    logger_utils.error(
                        "CallbackQuery does not contain a message.")
                    return
            elif isinstance(self._type_update, Update):
                if self._type_update.message:
                    chat_id = self._type_update.message.chat.id
                elif self._type_update.callback_query and self._type_update.callback_query.message:
                    chat_id = self._type_update.callback_query.message.chat.id
                else:
                    logger_utils.error(
                        "Update does not contain a valid chat or message.")
                    return
            await self._type_update.bot.delete_message(
                chat_id=chat_id, message_id=data.get(key))
        except Exception as err:
            logger_utils.error(f'{err=}', exc_info=True)
        logger_utils.debug('Exit')
    
    @staticmethod
    async def deletes_msg_a_delay(type_update: Message,
                                  delay: int = 2,
                                  indication=False) -> None:
        """
         Deletes a message after a specified time interval.
         Arguments: value (types.Message): The message to delete.
                    delay (int): Time in seconds before the message is deleted.
                    returns: None
        :param indication: Bool
        :param type_update: Message
        :param delay: int
        :return: None
        """
        logger_utils.debug('Entry')
        
        if not indication:
            await asyncio.sleep(delay)
            await type_update.delete()
            logger_utils.debug('Exit')
            return
        
        # Для сообщений с клавиатурой убирать клаву
        if type_update.reply_markup:
            await type_update.edit_reply_markup(reply_markup=None)
        
        # Сохраняем оригинальный текст сообщения
        original_text = type_update.text
        try:
            # Обратный отсчет от delay до 1
            for remaining in range(delay, 0, -1):
                # Обновляем текст сообщения с оставшимся временем
                await type_update.edit_text(
                    f"{original_text}\n\n"
                    f"Удалится через: {remaining} сек...")
                await asyncio.sleep(delay=1)
        except Exception as e:
            logger_utils.error(
                f"Ошибка при обновлении сообщения: {e}", exc_info=True)
        finally:
            await type_update.delete()
            logger_utils.debug('Exit')
