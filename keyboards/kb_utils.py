import logging

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger_kb_utils = logging.getLogger(__name__)

def create_static_kb(width: int = 1,
                     *args,
                     cancel_butt=True,
                     back=False,
                     exit_=False,
                     reverse_size_text=False,
                     url_buttons: dict = None,
                     **kwargs) -> InlineKeyboardMarkup:
    """
    Генерация инлайн-клавиатур с поддержкой CallbackData
    Args:
        width (int): Количество кнопок в строке
        *args (str | CallbackData): Кнопки (текст или CallbackData)
        cancel_butt (bool): Добавить кнопку 'Отмена'
        back (bool): Добавить кнопку "Назад"
        exit_ (bool): Добавить кнопку "Выйти"
        reverse_size_text (bool): Инвертировать порядок больших/маленьких кнопок
        url_buttons (): Кнопки с URL {текст: url}
        **kwargs (): Кнопки в формате {callback_data: текст}

    Returns: InlineKeyboardMarkup
    """
    BUTT_CANCEL: dict[str, str] = {'cancel': '❌ Отмена'}
    BUTT_BACK: dict[str, str] = {'back': '🔙 Назад'}
    BUTT_EXIT: dict[str, str] = {'exit': 'Выйти'}
    
    kb_builder = InlineKeyboardBuilder()
    big_text: list[InlineKeyboardButton] = []
    small_text: list[InlineKeyboardButton] = []
    
    if args:
        for item in args:
            text = BUTT_CANCEL.get(
                item, item)
            btn = InlineKeyboardButton(
                text=text, callback_data=item)
            (big_text if len(text) > 16 else small_text).append(btn)
    
    if kwargs:
        for data, text in kwargs.items():
            btn = InlineKeyboardButton(
                text=text, callback_data=data)
            (big_text if len(text) > 16 else small_text).append(btn)
    
    if reverse_size_text:
        kb_builder.row(*small_text, width=width)
        kb_builder.row(*big_text, width=1)
    else:
        kb_builder.row(*big_text, width=1)
        kb_builder.row(*small_text, width=width)
    
    # Добавляет ссылки в кнопки(если они есть)
    if url_buttons:
        url_buttons_list = [InlineKeyboardButton(text=text, url=url) for
            text, url in url_buttons.items()]
        
        kb_builder.row(*url_buttons_list, width=1)
    
    # Other buttons
    if cancel_butt:
        kb_builder.row(
            InlineKeyboardButton(
                text=BUTT_CANCEL['cancel'], callback_data='/cancel'))
    
    if exit_:
        kb_builder.row(
            InlineKeyboardButton(text=BUTT_EXIT['exit'], callback_data='/exit'))
    if back:
        kb_builder.row(
            InlineKeyboardButton(text=BUTT_BACK['back'], callback_data='back'))
    return kb_builder.as_markup()
