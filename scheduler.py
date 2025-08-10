import logging

from aiogram.fsm.storage.redis import Redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from filters.filters import ProfanityFilter
from tasks.tasks import StepikTasks

logger_scheduler = logging.getLogger(__name__)

async def start_scheduler(stepik_tasks: StepikTasks,
                          profanity_filter: ProfanityFilter) -> None:
    
    scheduler = AsyncIOScheduler()
    
    logger_scheduler.info("🟢 Инициализация планировщика…")
    
    scheduler.add_job(stepik_tasks.check_comments,
                      args=[profanity_filter],
                      trigger='interval',
                      minutes=1,
                      max_instances=1,
                      coalesce=True,
                      misfire_grace_time=60)
    
    scheduler.start()
    logger_scheduler.info("🟢 Планировщик запущен")
