import logging
from dataclasses import dataclass

from environs import Env

config_logger = logging.getLogger(__name__)

@dataclass
class TgBot:
    token: str
    id_owners: list[int]

@dataclass
class Stepik:
    client_id: str
    client_secret: str

@dataclass
class Config:
    tg_bot: TgBot
    stepik: Stepik
    redis_host: str
    redis_password: str
    level_log: str


def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)
    redis_host = env.str("REDIS_HOST", "localhost")
    level_log = env.str('LOG_LEVEL', 'INFO')
    redis_password = env.str("REDIS_PASSWORD", "")
    stepik_client_id = env.str("STEPIK_CLIENT_ID", "")
    stepik_client_secret = env.str("STEPIK_CLIENT_SECRET", "")
    
    return Config(
        tg_bot=TgBot(
            token=env('BOT_TOKEN'),
            id_owners=[*map(int, env('TG_IDS_OWNERS').split())]),
        stepik=Stepik(client_id=stepik_client_id,
                      client_secret=stepik_client_secret),
        redis_host=redis_host,
        redis_password=redis_password,
        level_log=level_log)
