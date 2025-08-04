import logging
import json
import re
from pathlib import Path

from Levenshtein import distance
from better_profanity import profanity
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from filters.patterns import DataProfanity

logger_filters = logging.getLogger(__name__)


class AccessRightsFilter(BaseFilter):
    def __init__(self, flag_admins: bool = False):
        self.flag_admins = flag_admins
    
    async def __call__(self,
                       msg: Message | CallbackQuery,
                       owners: list[int]) -> bool:
        user_tg_id = msg.from_user.id
        
        return user_tg_id in owners


class ProfanityFilter:

    BAD_WORDS_PATH = Path(__file__).parent.parent / "badwords.json"

    def __init__(self, bad_words_file=BAD_WORDS_PATH):
        # 1. Инициализация better_profanity
        profanity.load_censor_words()
        
        # словарь соответствий
        self.data_mapping = DataProfanity.CHAR_REPLACEMENT_MAP
        
        profanity.CHARS_MAPPING.update(self.data_mapping)
        
        # 2. Загрузка кастомных слов из файла
        self.bad_words = []
        
        if bad_words_file:
            try:
                with open(bad_words_file, 'r', encoding='utf-8') as json_f:
                    self.bad_words = json.load(json_f)
                    logger_filters.debug(f'Добавляются слова')
                    profanity.add_censor_words(self.bad_words)
            
            except (FileNotFoundError, json.JSONDecodeError) as err:
                logger_filters.error(
                    f"Ошибка загрузки файла {bad_words_file}:{err}")
                self.bad_words = []
            except Exception as err:
                logger_filters.error(f'Ошибка чтения JSON: {err}', exc_info=True)
        
        # 4. Компиляция регулярных выражений
        self.base_pattern = re.compile(
            DataProfanity.base_pattern, flags=re.IGNORECASE)
        
        self.additional_patterns = [re.compile(pattern, flags=re.IGNORECASE) for
            pattern in DataProfanity.additional_patterns]
        
        # 5. Паттерн для разбивки текста на слова
        self.word_pattern = re.compile(r'\b\w+\b')
    
    async def is_profanity(self, text: str) -> bool:
        """
        Основная функция проверки
        :param text:
        :return bool:
        """
        text = text.replace(" ", "")
        normalized_text = await self._normalize_text(text)
        text_lower = str(normalized_text).lower()
        
        # Fast check
        if len(text_lower.strip()) < 3:
            return False
        
        # 1. Быстрая проверка по better_profanity
        if profanity.contains_profanity(text_lower):
            logger_filters.warning(
                'Фильтр 1 better_profanity(полное '
                'совпадение)')
            return True
        
        # 2. Проверка по регулярным выражениям
        if self.base_pattern.search(text_lower):
            logger_filters.warning('Фильтр 2  re1')
            return True
        
        for pattern in self.additional_patterns:
            if pattern.search(text_lower):
                logger_filters.warning('Фильтр 3 re2')
                return True
        
        # 3. Проверка по списку слов (с учетом опечаток)
        words = re.findall(r'\w+', text_lower)
        if any(word in self.bad_words for word in words):
            logger_filters.warning('Фильтр 4 с учетом опечаток')
            return True
        
        # 4. Дополнительные проверки (опционально)
        if await self._check_levenshtein(text_lower):
            logger_filters.warning('Фильтр 5 "Levenshtein"')
            return True
        return False
    
    async def _normalize_text(self, text: str) -> str:
        """Приводит текст к стандартному виду, заменяя символы на базовые буквы"""
        normalized = []
        for char in text.lower():
            replacement = char
            for base_char, variants in self.data_mapping.items():
                if char in variants:
                    replacement = base_char
                    break
            normalized.append(replacement)
        return ''.join(normalized)
    
    async def _check_levenshtein(self, phrase: str) -> bool:
        """Проверка обходов фильтра (замены символов и т.д.)"""
        for key, value in self.data_mapping.items():
            # Проходимся по каждой букве в значении словаря. То есть по вот этим спискам ['а', 'a', '@'].
            for letter in value:
                # Проходимся по каждой букве в нашей фразе.
                for phr in phrase:
                    # Если буква совпадает с буквой в нашем списке.
                    if letter == phr:
                        # Заменяем эту букву на ключ словаря.
                        phrase = phrase.replace(phr, key)
        
        # Проходимся по всем словам.
        for word in self.bad_words:
            # Разбиваем слово на части, и проходимся по ним.
            for part in range(len(phrase)):
                # Вот сам наш фрагмент.
                fragment = phrase[part: part + len(word)]
                # Если отличие этого фрагмента меньше или равно 25% этого слова, то считаем, что они равны.
                if distance(fragment, word) <= len(word) * 0.25:
                    # Если они равны, выводим надпись о их нахождении
                    logger_filters.warning(f'Найдено: {word}')
                    return word
        return False


# f = ProfanityFilter()
# print(f.is_profanity(input()))
