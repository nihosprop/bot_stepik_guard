from dataclasses import dataclass
import logging

logger_lexicon = logging.getLogger(__name__)

@dataclass
class LexiconRu:
    start: str = 'Запуск'
    users_info: str = 'Инфо о юзерах'
