import asyncio
import logging
from logging.config import dictConfig

import yaml
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from environs import Env
from aiogram.fsm.storage.redis import Redis, RedisStorage
from aiogram import Bot, Dispatcher

from config_data.config import Config, load_config
from filters.toxicity_classifiers import RussianToxicityClassifier
from handlers import other, owners_handlers
from keyboards.set_menu import set_main_menu
from scheduler import start_scheduler
from tasks.tasks import StepikTasks
from utils.stepik import StepikAPIClient
from middlewares.outer import MsgProcMiddleware
from filters.filters import ProfanityFilter

logger_main = logging.getLogger(__name__)


async def setup_logging(config: Config):
    with open('logs/logging_settings/log_conf.yml', 'rt') as file:
        config_str = file.read()
    # вставляем(заменяем шаблоны на) переменные окружения
    config_str = config_str.replace('${LOG_LEVEL}', config.level_log)
    log_config = yaml.safe_load(config_str)
    dictConfig(log_config)
    logger_main.info('=== LOGGING CONFIGURATION IS LOADED SUCCESSFULLY ===')


async def setup_redis(config: Config) -> tuple[Redis, Redis]:
    redis_fsm = Redis(
        host=config.redis_host,
        port=6379,
        db=0,
        password=config.redis_password or None)
    
    redis_data = Redis(
        host=config.redis_host,
        port=6379,
        db=1,
        decode_responses=True,
        password=config.redis_password or None)
    
    try:
        await redis_fsm.ping()
        logger_main.info("=== REDIS FSM SUCCESSFULLY CONNECTED ===")
    except Exception as err:
        logger_main.error(
            f"Ошибка подключения к Redis FSM: {err}", exc_info=True)
        raise
    
    try:
        await redis_data.ping()
        logger_main.info("=== REDIS DATA  SUCCESSFULLY CONNECTED ===")
    except Exception as err:
        logger_main.error(
            f"Ошибка подключения к Redis Cache: {err}", exc_info=True)
        raise
    
    return redis_fsm, redis_data


async def main():
    env = Env()
    env.read_env()
    config: Config = load_config()
    
    await setup_logging(config=config)
    
    stepik_client_id: str = config.stepik.client_id
    stepik_client_secret: str = config.stepik.client_secret
    stepik_courses_ids: list[int] = config.stepik.stepic_courses_ids
    redis_fsm, redis_data = await setup_redis(config)
    
    stepik_client = StepikAPIClient(
        client_id=stepik_client_id,
        client_secret=stepik_client_secret,
        redis_client=redis_data)
    
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    logger_main.info('=== BOT INITIALIZATION SUCCEEDED ===')
    
    storage = RedisStorage(redis=redis_fsm)
    
    dp = Dispatcher(storage=storage)
    
    await set_main_menu(bot=bot)
    
    profanity_filter = ProfanityFilter()
    logger_main.info('=== PROFANITY FILTER INITIALIZATION SUCCEEDED ===')
    
    logger_main.info('=== TOXICITY FILTER START INITIALIZATION ===')
    toxicity_filter = RussianToxicityClassifier(
            ["SkolkovoInstitute/russian_toxicity_classifier"])
    await toxicity_filter.initialize()
    logger_main.info('=== TOXICITY FILTER INITIALIZATION SUCCEEDED ===')
    
    stepik_tasks = StepikTasks(
        stepik_client=stepik_client,
        stepik_courses_ids=stepik_courses_ids,
        bot=bot,
        owners=config.tg_bot.id_owners)
    logger_main.info('=== STEPIK TASKS INITIALIZATION SUCCEEDED ===')
    
    await start_scheduler(
        stepik_tasks=stepik_tasks,
        profanity_filter=profanity_filter,
        toxicity_filter=toxicity_filter)
    
    try:
        # routers
        dp.include_router(owners_handlers.owners_router)
        dp.include_router(other.other_router)
        
        # middlewares
        dp.update.middleware(MsgProcMiddleware())
        
        await bot.delete_webhook(drop_pending_updates=True)
        logger_main.info('Start bot')
        
        await asyncio.gather(
            dp.start_polling(
                bot,
                owners=config.tg_bot.id_owners,
                redis_fsm=redis_fsm,
                redis_data=redis_data,
                stepik_client=stepik_client,
                stepik_courses_ids=stepik_courses_ids))
    
    except Exception as err:
        logger_main.exception(err)
        raise
    finally:
        await redis_fsm.aclose()
        logger_main.info('Stop bot')


if __name__ == "__main__":
    asyncio.run(main())
