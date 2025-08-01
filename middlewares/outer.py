import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from utils.utils import MessageProcessor

logger_middl_outer = logging.getLogger(__name__)

class MsgProcMiddleware(BaseMiddleware):
    """
    Middleware для обработки Message и callback-запросов.
    Добавляет экземпляр класса MessageProcessor в контекст(в данные (data)),
    который может быть использован в обработчиках для дополнительной обработки
     сообщений.
    """
    
    async def __call__(self,
                       handler: Callable[
                           [TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: Message | CallbackQuery,
                       data: Dict[str, Any]) -> Any:
        """
        Обрабатывает event(входящее событие).
        Args:
            handler: Обработчик, который будет вызван после middleware.
            event(Message | CallbackQuery): Входящее событие
            data: Словарь с данными, которые передаются между middleware и
            обработчиками.
        Returns:
            handler.
        """
        data["msg_processor"] = MessageProcessor(event, _state=data["state"])
        return await handler(event, data)
