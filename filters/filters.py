import logging
import json
import re
from pathlib import Path

import pymorphy3
from Levenshtein import distance
from better_profanity import profanity
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from filters.patterns import DataProfanity
from utils.redis_service import RedisService
logger_filters = logging.getLogger(__name__)


class AccessRightsFilter(BaseFilter):
    def __init__(self, flag_users: bool = False):
        self.flag_users = flag_users
    
    async def __call__(self,
                       msg: Message | CallbackQuery,
                       owners: list[int],
                       redis_service: RedisService) -> bool:
        user_tg_id: int = msg.from_user.id
        
        if self.flag_users:
            users: list[int] = await redis_service.get_users()
            owners.extend(users)
        return user_tg_id in owners


class TgUserIDFilter(BaseFilter):
    """
    Фильтр для сообщений с Telegram ID.
    Пропускает сообщение, если текст — это положительное целое число
    с длиной в разумном диапазоне (по умолчанию 5–15 цифр).
    Используйте в хендлере ввода ID пользователя.
    """
    
    def __init__(self, min_len: int = 5, max_len: int = 15):
        self.min_len = min_len
        self.max_len = max_len
    
    async def __call__(self, msg: Message) -> bool:
        text = (msg.text or "").strip()
        if not text.isdigit():
            return False
        try:
            val = int(text)
        except Exception:
            return False
        if val <= 0:
            return False
        length = len(text)
        if length < self.min_len or length > self.max_len:
            return False
        return True


class ProfanityFilter:
    
    BAD_WORDS_PATH = Path(__file__).parent.parent / "badwords.json"
    TECHNICAL_WORDS_PATH = (
        Path(__file__).parent.parent / 'filters' / 'technical_words.json')
    
    def __init__(self,
                 bad_words_file=BAD_WORDS_PATH,
                 technical_words_file=TECHNICAL_WORDS_PATH):
        # 1. Инициализация better_profanity
        profanity.load_censor_words()
        
        # Инициализация
        self.morph = pymorphy3.MorphAnalyzer()
        
        # словарь соответствий
        self.data_mapping = DataProfanity.CHAR_REPLACEMENT_MAP
        self.min_word_length = 4
        self.special_chars = set('0123456789!@#$%^&*')
        profanity.CHARS_MAPPING.update(self.data_mapping)
        
        # Загрузка кастомных слов из файла
        self.bad_words = []
        
        if bad_words_file:
            try:
                with open(bad_words_file, 'r', encoding='utf-8') as json_f:
                    self.bad_words = json.load(json_f)
                    logger_filters.debug(f'Added bad words')
                    profanity.add_censor_words(self.bad_words)
            
            except (FileNotFoundError, json.JSONDecodeError) as err:
                logger_filters.error(
                    f"🟢Ошибка загрузки файла {bad_words_file}:{err}")
                self.bad_words = []
            except Exception as err:
                logger_filters.error(
                    f'🟢Ошибка чтения JSON: {err}', exc_info=True)
        
        # Загрузка технических терминов(слов)
        self.tech_keywords = []
        try:
            with open(technical_words_file, 'r', encoding='utf-8') as json_f:
                self.tech_words = json.load(json_f)
                logger_filters.debug(f'Added technical words')
        except Exception as err:
            logger_filters.error(f'🟢Ошибка чтения JSON: {err}', exc_info=True)
        
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
        
        if await self._is_technical_text(text):
            logger_filters.debug(f'Пропущено (тех. текст): {text}')
            return False
        
        if any(
            symbol in text for symbol in
                {'=', '(', ')', 'print', 'def', 'class'}):
            logger_filters.debug(f'Пропущено (код/скобки): {text}')
            return False
        
        if len(set(text)) == 1:
            logger_filters.debug(f'Пропущено (повтор символов): {set(text)=}')
            return False
        
        if text.isdigit():
            logger_filters.debug(f'Пропущено (цифры):{text}')
            return False
        
        simple_text = text.lower().split()
        for word in simple_text:
            if word in self.bad_words:
                logger_filters.warning(
                    f'🟢Заблокировано simple_text bad_words:'
                    f' {word}')
                return True
        
        text = text.replace(" ", "")
        normalized_text = await self._normalize_text(text)
        text_lower = str(normalized_text).lower()
        
        if len(text_lower.strip()) < 3:
            logger_filters.debug(f'Пропущено: длина меньше 3х: {text_lower}')
            return False
        
        # 1. Быстрая проверка по better_profanity
        if profanity.contains_profanity(text_lower):
            # logger_tests.warning(
            #     'Фильтр 1 better_profanity(полное '
            #     'совпадение)')
            logger_filters.warning(f'🟢Заблокировано better_profanity: {text}')
            return True
        
        # 2. Проверка по регулярным выражениям
        if self.base_pattern.search(text_lower):
            logger_filters.warning(f'🟢Заблокировано base_pattern: {text}')
            return True
        
        for pattern in self.additional_patterns:
            if pattern.search(text.lower()):
                logger_filters.warning(
                    f'🟢Заблокировано additional_p'
                    f'atterns: {text.lower()}')
                return True
        
        for pattern in self.additional_patterns:
            if pattern.search(text_lower):
                logger_filters.warning(
                    f'🟢Заблокировано additional_patterns: {text_lower}')
                return True
        
        # 3. Проверка по списку слов (с учетом опечаток)
        words = re.findall(r'\w+', text_lower)
        if any(word in self.bad_words for word in words):
            logger_filters.warning(
                f'🟢Заблокировано Проверка по списку слов (с учетом опечаток): {words}')
            return True
        
        # 4. Дополнительные проверки (опционально)
        if await self._check_levenshtein(text_lower):
            logger_filters.warning('🟢Заблокировано: Фильтр 5 "Levenshtein"')
            return True
        logger_filters.debug('Текст прошел все фильтры')
        return False
    
    async def _is_technical_text(self, text: str) -> bool:
        """Проверяет, является ли текст техническим (игнорирует мат в таком контексте)"""
        words = re.findall(r'\w+', text.lower())
        for word in words:
            parsed = self.morph.parse(word)[0]  # берем самый вероятный разбор
            normal_form = parsed.normal_form  # нормальная форма слова
            if normal_form in self.tech_keywords:  # если это технический термин
                return True
        return False
    
    async def _is_technical_word(self, word: str) -> bool:
        """Проверяет, является ли слово техническим термином (игнорирует его в проверках)."""
        parsed = self.morph.parse(word.lower())[0]
        normal_form = parsed.normal_form  # нормальная форма слова
        return normal_form in self.tech_keywords
    
    async def _normalize_text(self, text: str) -> str:
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
    
    async def _check_levenshtein(self, phrase: str) -> bool:
        """Улучшенная проверка с контекстным анализом"""
        normalized = await self._normalize_text(phrase)
        words = re.findall(r'\b\w+\b', normalized)  # выделяем целые слова
        
        for bad_word in self.bad_words:
            bw_len = len(bad_word)
            
            # Не проверяем слишком короткие слова
            if bw_len < self.min_word_length:
                continue
            
            for candidate in words:
                c_len = len(candidate)
                
                # Игнорируем слова короче min_word_length
                if c_len < self.min_word_length:
                    continue
                
                # Быстрая проверка по длине
                if abs(c_len - bw_len) > 2:  # допускаем разницу до 1 символов
                    continue
                
                # Точное совпадение после нормализации
                if candidate == bad_word:
                    logger_filters.warning(f'🟢Точное совпадение: {bad_word}')
                    return True
                
                # Проверка расстояния Левенштейна (ужесточённая)
                max_allowed_distance = 1 if bw_len <= 6 else 2
                
                # Если кандидат — часть другого слова (например, "код" в "кодекс"), пропускаем
                if candidate in bad_word or bad_word in candidate:
                    continue
                
                # Если расстояние Левенштейна в допустимых пределах
                if distance(candidate, bad_word) <= max_allowed_distance:
                    # Дополнительная проверка: слово не должно быть частью технического термина
                    if not await self._is_technical_word(candidate):
                        logger_filters.debug(
                            f'🟢Найдено по Левенштейну: {bad_word} '
                            f'(кандидат: {candidate}, расстояние: {distance(candidate, bad_word)})')
                        return True
        
        return False
