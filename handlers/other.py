import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from filters.filters import AccessRightsFilter
from utils.stepik import StepikAPIClient
from utils.utils import MessageProcessor, get_username
from keyboards.keyboards import kb_start

logger_owners = logging.getLogger(__name__)

other_router = Router()

other_router.message.filter(AccessRightsFilter())
other_router.callback_query.filter(AccessRightsFilter())

