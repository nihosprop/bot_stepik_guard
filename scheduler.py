import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from filters.filters import ProfanityFilter
from filters.toxicity_classifiers import RussianToxicityClassifier
from tasks.tasks import StepikTasks

logger_scheduler = logging.getLogger(__name__)


async def start_scheduler(stepik_tasks: StepikTasks,
                          profanity_filter: ProfanityFilter,
                          toxicity_filter: RussianToxicityClassifier) -> None:
    
    scheduler = AsyncIOScheduler()
    
    logger_scheduler.info("🟢=== PLANNER INITIALIZATION STARTED ===")
    
    scheduler.add_job(
        stepik_tasks.check_comments,
        args=[profanity_filter, toxicity_filter],
        trigger='interval',
        minutes=1,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60)
    
    scheduler.start()
    logger_scheduler.info("🟢=== PLANNER IS LAUNCHED ===")
