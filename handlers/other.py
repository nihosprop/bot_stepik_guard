import logging

from aiogram import Router
from aiogram.filters import or_f
from aiogram.types import Message

from filters.filters import AccessOwnersFilter, AccessUsersFilter
from utils.redis_service import RedisService
from utils.utils import MessageProcessor

logger = logging.getLogger(__name__)

other_router = Router()
other_router.message.filter(
    ~or_f(AccessUsersFilter(), AccessOwnersFilter()))
other_router.callback_query.filter(
    ~or_f(AccessUsersFilter(), AccessOwnersFilter()))


@other_router.message()
async def other_handler(msg: Message,
                        owners: list[int],
                        msg_processor: MessageProcessor,
                        redis_service: RedisService) -> None:
    
    logger.debug('Entry')
    
    await msg.delete()
    
    owners_links = await redis_service.get_owners_info()
    
    if not owners_links:
        fallback_rows: list[str] = []
        for own_id in owners:
            fallback_rows.append(
                f'👑 <a href="tg://user?id={own_id}">{own_id}</a>')
        owners_links = '\n'.join(fallback_rows)
    
    text = (f'Для отслеживания комментариев на Stepik, обратитесь '
            f'к любому из супер-админов:\n{owners_links}')
    
    await msg_processor.deletes_messages(msgs_for_del=True)
    value = await msg.answer(text)
    await msg_processor.deletes_msg_a_delay(value, delay=20, indication=True)
    
    logger.debug('Exit')
