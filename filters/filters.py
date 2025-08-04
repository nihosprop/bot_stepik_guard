import logging
import json
import os
import re

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from utils.patterns import Patterns

logger_filters = logging.getLogger(__name__)


class AccessRightsFilter(BaseFilter):
    def __init__(self, flag_admins: bool = False):
        self.flag_admins = flag_admins
    
    async def __call__(self,
                       msg: Message | CallbackQuery,
                       owners: list[int]) -> bool:
        user_tg_id = msg.from_user.id
        
        return user_tg_id in owners

# Комбинированный фильтр
def is_profanity(text: str) -> bool:
    text = text.lower()
    # Проверка основного паттерна
    if Patterns.profanity_pattern.search(text):
        return True
    # Проверка дополнительных паттернов
    for pattern in Patterns.additional_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False
