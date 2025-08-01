import logging

from aiogram import Bot
from aiogram.fsm.storage.redis import Redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tasks.tasks import StepikTasks
from utils.stepik import StepikAPIClient

logger_scheduler = logging.getLogger(__name__)

async def start_scheduler(stepik_client: StepikAPIClient,
                          stepik_courses_ids: list[int]) -> None:
    scheduler = AsyncIOScheduler()
    logger_scheduler.info("🟢 Инициализация планировщика…")
    
    scheduler.add_job(StepikTasks.check_comments,
                      args=[stepik_client, stepik_courses_ids],
                      trigger='interval',
                      minutes=1,
                      max_instances=1,
                      coalesce=True,
                      misfire_grace_time=60)
    
    scheduler.start()
    logger_scheduler.info("🟢 Планировщик запущен")
