import asyncio
import logging
import html
import re
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


async def clean_html_tags(raw_html: str) -> str:
    """Удаляет HTML-теги из строки, сохраняя блоки кода.

    Args:
        raw_html (str): Строка с HTML-тегами, возможно содержащая блоки кода.

    Returns:
        str: Текст с сохраненными блоками кода (в тегах <pre><code>) и без остальных HTML-тегов.
    """
    if not raw_html:
        return ""
    
    # Словарь для временного хранения блоков кода
    code_blocks = {}
    
    # Шаг 1: Находим и сохраняем все блоки кода
    def save_code(match):
        block_id = f"__CODE_BLOCK_{len(code_blocks)}__"
        code_blocks[block_id] = match.group(0)  # Сохраняем с тегами <pre><code>
        return block_id
    
    # Заменяем блоки кода на временные метки
    pattern = re.compile(r'<pre><code>(.*?)</code></pre>', re.DOTALL)
    temp_text = pattern.sub(save_code, raw_html)
    
    # Шаг 2: Удаляем все оставшиеся HTML-теги
    clean_text = re.sub(r'<[^>]+>', '', temp_text)
    
    # Шаг 3: Восстанавливаем блоки кода с оригинальными тегами
    for block_id, code_block in code_blocks.items():
        clean_text = clean_text.replace(block_id, code_block)
    
    # Шаг 4: Обрабатываем HTML-сущности
    clean_text = html.unescape(clean_text)
    
    # Шаг 5: Экранируем специальные символы в не-кодовых частях
    parts = re.split(
        r'(<pre><code>.*?</code></pre>)',
        clean_text,
        flags=re.DOTALL)
    for i in range(len(parts)):
        # Пропускаем блоки кода
        if not parts[i].startswith('<pre><code>'):
            parts[i] = (
                parts[i].replace('&', '&amp;').replace('<', '&lt;').replace(
                    '>',
                    '&gt;').replace('"', '&quot;'))
    
    clean_text = ''.join(parts)
    
    # Шаг 6: Нормализуем пробелы в не-кодовых частях
    parts = re.split(
        r'(<pre><code>.*?</code></pre>)',
        clean_text,
        flags=re.DOTALL)
    for i in range(
        0,
        len(parts),
        2):  # Обрабатываем только нечетные части (не блоки кода)
        if i < len(parts):
            parts[i] = re.sub(r'\s+', ' ', parts[i]).strip()
    
    return ''.join(parts)


@dataclass
class MessageProcessor:
    """
    Класс для удаления сообщений и установки клавиатур.
    
    Attributes:
        _type_update (Union[Message, CallbackQuery]): Объект апдейта.
        _state (FSMContext): Объект контекста FSM.
        
    Methods:
        deletes_messages(msgs_for_del=False, msgs_remove_kb=False):
         Удаляет сообщения из чата.
        save_msg_id(value, msgs_for_del=False, msgs_remove_kb=False):
         Сохраняет идентификатор сообщения в хранилище.
        removes_inline_kb(msgs_remove_kb=False):
         Удаляет встроенную клавиатуру.
    Note:
        Этот класс предназначен для управления сообщениями в чате
         и удалением клавиатур. Он предоставляет методы для удаления
         сообщений, сохранения и удаления клавиатур.
    
    Example:
        message_processor = MessageProcessor(update, state)
        await message_processor.deletes_messages(msgs_for_del=True)
        await message_processor.removes_inline_kb(msgs_remove_kb=True)
    
    """
    _type_update: Message | CallbackQuery | Update
    _state: FSMContext
    
    async def deletes_messages(self,
                               msgs_for_del=False,
                               msgs_remove_kb=False) -> None:
        logger_utils.debug(f'Entry')
        
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
                    "Update does not contain a message.")
                return
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
                msgs_ids = [int(msg_id) for msg_id in msgs_ids]
                
                if not msgs_ids:
                    continue
                
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
    
    @staticmethod
    def _extract_message_id(value: Message | CallbackQuery | Update) -> (
        int | None):
        if isinstance(value, Message):
            return int(value.message_id)
        if isinstance(value, CallbackQuery) and value.message:
            return int(value.message.message_id)
        if isinstance(value, Update):
            if value.message:
                return int(value.message.message_id)
            if value.callback_query and value.callback_query.message:
                return int(value.callback_query.message.message_id)
        return None
    
    async def save_msg_id(self,
                          value: Message | CallbackQuery | Update,
                          msgs_for_del=False,
                          msgs_remove_kb=False) -> None:
        flags: dict = {
            'msgs_for_del': msgs_for_del,
            'msgs_remove_kb': msgs_remove_kb}
        
        for key, val in flags.items():
            logger_utils.debug('Start writing data to storage…')
            
            if val:
                
                data: list = dict(await self._state.get_data()).get(key, [])
                data = [int(msg_id) for msg_id in data]
                
                msg_id = self._extract_message_id(value)
                
                if msg_id is None:
                    logger_utils.info('No msg ID to record')
                    return
                
                if msg_id not in data:
                    data.append(msg_id)
                    
                    logger_utils.debug(f'Msg ID:{msg_id} to recorded')
                await self._state.update_data({key: data})
        
        logger_utils.debug('Exit')
    
    async def removes_inline_kb(self, key='msgs_remove_kb') -> None:
        
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
        Метод удаляет сообщение из чата, используя идентификатор
            сообщения, сохраненный в хранилище по ключу `key`.
        
        Args:
            key (str): Ключ в хранилище, содержащий идентификатор сообщения.
        Returns:
            None
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
        Удаляет сообщение с задержкой.
        
        Args:
            type_update (Message): Объект апдейта.
            delay (int): Задержка в секундах.
            indication (bool): Флаг индикации удаления.
        Returns:
            None
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
