import logging

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger_kb_utils = logging.getLogger(__name__)


def create_static_kb(width: int = 1,
                     *args,
                     cancel_butt=False,
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
        url_buttons (dict): Кнопки с URL {текст: url}
        **kwargs : Кнопки в формате {callback_data: текст}

    Returns: InlineKeyboardMarkup
    """
    BUTT_CANCEL: dict[str, str] = {'cancel': 'Отмена'}
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


async def create_notification_settings_kb(user_data_notif: dict) -> InlineKeyboardMarkup:
    # Формируем текст и callback_data для кнопок
    solution_text = '🔴 Отключить уведомления о решениях' if user_data_notif.get(
        'is_notif_solution', True) else '🟢 Включить уведомления о решениях'
    solution_clbk = 'off_notif_solution' if user_data_notif.get(
        'is_notif_solution', True) else 'on_notif_solution'
    
    uninformative_text = '🔴 Отключить неинформативные' if user_data_notif.get(
        'is_notif_uninformative', True) else '🟢 Включить неинформативные'
    uninformative_cb = 'off_notif_uninformative' if user_data_notif.get(
        'is_notif_uninformative', True) else 'on_notif_uninformative'
    
    kb = create_static_kb(
        **{solution_clbk: solution_text},
        **{uninformative_cb: uninformative_text},
        back=True,
        exit_=True)
    
    return kb


async def create_message_settings_kb(message_settings: dict[
    str, bool]) -> InlineKeyboardMarkup:
    text = '🔴 Отключить удаление' if message_settings.get(
        'remove_toxic', True) else '🟢 Включить удаление'
    clbk = 'off_remove_toxic' if message_settings.get(
        'remove_toxic', True) else 'on_remove_toxic'
    
    return create_static_kb(**{clbk: text}, back=True, exit_=True)
