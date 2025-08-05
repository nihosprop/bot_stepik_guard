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
        self.min_word_length = 4
        self.special_chars = set('0123456789!@#$%^&*')
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
    
    def is_profanity(self, text: str) -> bool:
        """
        Основная функция проверки
        :param text:
        :return bool:
        """
        if any(
            symbol in text for symbol in
                {'=', '(', ')', 'print', 'def', 'class'}):
            return False
        
        if len(set(text)) == 1:
            return False
        
        if text.isdigit():
            return False
        
        simple_text = text.split()
        for word in simple_text:
            if word in self.bad_words:
                # print(f'Простая проверка: {word}')
                return True
        
        # if profanity.contains_profanity(simple_text):
        #     return True
        
        text = text.replace(" ", "")
        normalized_text = self._normalize_text(text)
        text_lower = str(normalized_text).lower()
        
        # Fast check
        if len(text_lower.strip()) < 3:
            return False
        
        # 1. Быстрая проверка по better_profanity
        if profanity.contains_profanity(text_lower):
            # logger_tests.warning(
            #     'Фильтр 1 better_profanity(полное '
            #     'совпадение)')
            return True
        
        # 2. Проверка по регулярным выражениям
        if self.base_pattern.search(text_lower):
            # logger_tests.warning('Фильтр 2  re1')
            return True
        
        for pattern in self.additional_patterns:
            if pattern.search(text.lower()):
                return True
        
        for pattern in self.additional_patterns:
            if pattern.search(text_lower):
                # logger_tests.warning('Фильтр 3 re2')
                return True
        
        # 3. Проверка по списку слов (с учетом опечаток)
        words = re.findall(r'\w+', text_lower)
        if any(word in self.bad_words for word in words):
            # logger_tests.warning('Фильтр 4 с учетом опечаток')
            return True
        
        # 4. Дополнительные проверки (опционально)
        if self._check_levenshtein(text_lower):
            logger_filters.warning('Фильтр 5 "Levenshtein"')
            return True
        return False
    
    def _normalize_text(self, text: str) -> str:
        """Улучшенная нормализация текста с учетом контекста"""
        # Сначала заменяем все спецсимволы и похожие буквы
        normalized = []
        for char in text.lower():
            replacement = char
            for base_char, variants in self.data_mapping.items():
                if char in variants:
                    replacement = base_char
                    break
            normalized.append(replacement)
        normalized_text = ''.join(normalized)
        
        # Удаляем повторяющиеся символы (например "прривет" -> "привет")
        normalized_text = re.sub(r'(.)\1+', r'\1', normalized_text)
        return normalized_text
    
    def _is_valid_match(self, candidate: str, bad_word: str) -> bool:
        """Проверка, является ли совпадение валидным"""
        # Если в кандидате есть цифры/спецсимволы - считаем подозрительным
        if any(c in self.special_chars for c in candidate):
            return True
        
        # Для коротких слов (3-4 символа) требуем точного совпадения после нормализации
        if len(bad_word) <= 3:
            return candidate == bad_word
        
        # Для слов из 5 символов - максимум 1 ошибка
        if len(bad_word) == 5:
            return distance(candidate, bad_word) <= 1
        
        # Для более длинных слов - максимум 2 ошибки
        return distance(candidate, bad_word) <= 2
    
    def _check_levenshtein(self, phrase: str) -> bool:
        """Улучшенная проверка с контекстным анализом"""
        normalized = self._normalize_text(phrase)
        words = re.findall(r'\b\w+\b', normalized)  # выделяем целые слова
        
        for bad_word in self.bad_words:
            bw_len = len(bad_word)
            
            # Не проверяем слишком короткие слова
            if bw_len < self.min_word_length:
                continue
            
            for candidate in words:
                c_len = len(candidate)
                
                # Быстрая проверка по длине
                if abs(c_len - bw_len) > 2:  # допускаем разницу до 2 символов
                    continue
                
                # Точное совпадение после нормализации
                if candidate == bad_word:
                    logger_filters.warning(f'Точное совпадение: {bad_word}')
                    return True
                
                # Проверка расстояния Левенштейна с учетом контекста
                if self._is_valid_match(candidate, bad_word):
                    logger_filters.warning(
                        f'Найдено по Левенштейну: {bad_word} '
                        f'(кандидат: {candidate}, расстояние: {distance(candidate, bad_word)})')
                    return True
        
        return False
