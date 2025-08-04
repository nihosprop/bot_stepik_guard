import logging
import json
import os
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

logger_filters = logging.getLogger(__name__)


class AccessRightsFilter(BaseFilter):
    def __init__(self, flag_admins: bool = False):
        self.flag_admins = flag_admins
    
    async def __call__(self,
                       msg: Message | CallbackQuery,
                       owners: list[int]) -> bool:
        user_tg_id = msg.from_user.id
        
        return user_tg_id in owners
