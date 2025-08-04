import logging

from aiogram import Bot
from aiogram.fsm.storage.redis import Redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from filters.filters import ProfanityFilter
from tasks.tasks import StepikTasks
from utils.stepik import StepikAPIClient

logger_scheduler = logging.getLogger(__name__)

async def start_scheduler(stepik_client: StepikAPIClient,
                          stepik_courses_ids: list[int],
                          profanity_filter: ProfanityFilter) -> None:
    scheduler = AsyncIOScheduler()
    logger_scheduler.info("🟢 Инициализация планировщика…")
    
    stepik_tasks = StepikTasks(stepik_client=stepik_client,
                               stepik_courses_ids=stepik_courses_ids)
    
    scheduler.add_job(stepik_tasks.check_comments,
                      args=[profanity_filter],
                      trigger='interval',
                      seconds=30,
                      max_instances=1,
                      coalesce=True,
                      misfire_grace_time=60)
    
    scheduler.start()
    logger_scheduler.info("🟢 Планировщик запущен")
