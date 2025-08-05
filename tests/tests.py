import html
import json
import logging
import re

import unicodedata
from Levenshtein import distance
from pathlib import Path

from better_profanity import profanity

from filters.patterns import DataProfanity

logger_tests = logging.getLogger(__name__)

test_cases = [
    # Базовые матерные слова
    ("хуй", True),
    ("пизда", True),
    ("ебал", True),
    ("блядь", True),
    ("сука", True),
    ("гондон", True),
    ("мудак", True),
    ("залупа", True),
    ("шлюха", True),
    ("пидор", True),
    
    # Обычные слова (не должны триггерить)
    ("хороший", False),
    ("прекрасно", False),
    ("нейтрально", False),
    ("обычный", False),
    ("слово", False),
    ("фильтр", False),
    ("проверка", False),
    
    # Опечатки и замены символов
    ("х@й", True),
    ("п!зда", True),
    ("е6ал", True),
    ("бляdь", True),
    ("суkа", True),
    ("г0ндон", True),
    ("муdак", True),
    ("залуп@", True),
    ("шлюxа", True),
    ("пиd0р", True),
    ("xyй", True),
    ("пiзда", True),
    ("ебaл", True),
    ("бл9дь", True),
    ("сyка", True),
    ("гандон", True),
    ("муд@к", True),
    ("залупa", True),
    ("шльуха", True),
    ("пiдор", True),
    
    # Разделение символами
    ("х у й", True),
    ("п-изда", True),
    ("еб@л", True),
    ("бл*ядь", True),
    ("с у к а", True),
    ("г о н д о н", True),
    ("м у д а к", True),
    ("з а л у п а", True),
    ("ш л ю х а", True),
    ("п и д о р", True),
    ("х.у.й", True),
    ("п!з!д!а", True),
    ("е#б@а@л", True),
    ("б$л%я^дь", True),
    ("с*у*к*а", True),
    
    # Повторения символов
    ("хуууй", True),
    ("пппизда", True),
    ("ееебал", True),
    ("бляяядь", True),
    ("сууука", True),
    ("гооондон", True),
    ("муудак", True),
    ("залууупа", True),
    ("шлюююха", True),
    ("пииидор", True),
    ("ххххх", True),
    ("ппппп", True),
    ("еееее", True),
    ("ббббб", True),
    ("ссссс", True),
    
    # Смешанные языки
    ("hуй", True),
    ("pизда", True),
    ("eбал", True),
    ("blять", True),
    ("cyка", True),
    ("gондон", True),
    ("mудак", True),
    ("zалупа", True),
    ("шlюха", True),
    ("pидор", True),
    ("xуj", True),
    ("пiзdа", True),
    ("ебa1", True),
    ("бл9dь", True),
    ("суkа", True),
    
    # Краткие формы и производные
    ("хер", True),
    ("хрен", True),
    ("пизд", True),
    ("еб", False),
    ("бля", True),
    ("сук", True),
    ("гон", True),
    ("муд", True),
    ("зал", True),
    ("пид", True),
    ("хуев", True),
    ("пиздец", True),
    ("ебанутый", True),
    ("блядский", True),
    ("сучара", True),
    ("гандонский", True),
    ("мудацкий", True),
    ("залупиться", True),
    ("шлюшиный", True),
    ("пидорасина", True),
    
    # Обход через Unicode (гомоглифы)
    ("хᥙй", True),
    ("пізда", True),
    ("ебɑл", True),
    ("бⅼядь", True),
    ("ѕука", True),
    ("ɡондон", True),
    ("ｍудак", True),
    ("ᴢалупа", True),
    ("шɭюха", True),
    ("рідоｒ", True),
    ("һуй", True),
    ("рizdа", True),
    ("еьал", True),
    ("ьлядь", True),
    ("ѕцка", True),
    
    # Проблемные кейсы (ложные срабатывания)
    ("художник", False),
    ("познание", False),
    ("белый", False),
    ("суккулент", False),
    ("голубой", False),
    ("мудачок", False),
    ("шлюмберье", False),
    ("пиджаки", False),
    ("херсонес", False),
    ("хулиган", False),
    
    # Сложные комбинации
    ("датыдинах@й", True),
    ("подпизд@шить", True),
    ("разъебашить", True),
    ("ублюдоксуч@", True),
    ("гандоноподобный", True),
    ("мудаковатый", True),
    ("залупиноголовый", True),
    ("шлюхомойка", True),
    ("пидорашка", True),
    ("херосрач", True),
    ("пиздабол", True),
    ("ебануться", True),
    ("блядослов", True),
    ("сукоёб", True),
    ("гандономат", True),
    ("мудакоид", True),
    ("залупоглаз", True),
    ("шлюходроч", True),
    ("пидорванец", True),
    ("херомантия", True),
    
    # Граничные кейсы
    ("", False),
    (" ", False),
    ("   ", False),
    ("!@#$%", False),
    ("12345", False),
    ("абвгд", False),
    ("х", False),
    ("ху", False),
    ("хую", True),
    ("хуюш", True),
    ("а", False),
    ("б", False),
    ("в", False),
    ("г", False),
    ("д", False),
    ("е", False),
    ("ё", False),
    ("ж", False),
    ("з", False),
    ("и", False),
    
    # Длинные тексты с матом
    ("Это текст с хуём посередине", True),
    ("Вот такая пиздец ситуация", True),
    ("Ну ты и блядь", True),
    ("Сучка ты конченная", True),
    ("Гандон ты ебаный", True),
    ("Мудак вонючий", True),
    ("Залупа кривая", True),
    ("Шлюха ты тупая", True),
    ("Пидор несчастный", True),
    ("Хуй тебе а не ответ", True),
    
    # Текст без мата (не должен триггерить)
    ("Это нормальный текст без оскорблений", False),
    ("Просто проверка работы фильтра", False),
    ("Никаких плохих слов здесь нет", False),
    ("Хороший день для программирования", False),
    ("Фильтр должен пропустить этот текст", False),
    
    # Эвфемизмы и завуалированные оскорбления
    ("х****й", True),
    ("п****а", True),
    ("******", False),
    ("б****ь", True),
    ("с***а", True),
    ("****он", True),
    ("м***к", True),
    ("з****а", True),
    ("ш***а", True),
    ("п****р", True),
    ("х*й", True),
    ("п*зда", True),
    ("*бал", True),
    ("бл*дь", True),
    ("с*ка", True),
    ("г*ндон", True),
    ("м*дак", True),
    ("з*лупа", True),
    ("ш*люха", True),
    ("п*дор", True),
    
    # Творческие написания
    ("хуйландия", True),
    ("пиздаболище", True),
    ("ебанько", True),
    ("блядюга", True),
    ("сукодел", False),
    ("гандончик", True),
    ("мудачина", True),
    ("залупень", True),
    ("шлюшенция", True),
    ("пидорама", True),
    ("хуяк", True),
    ("пиздак", True),
    ("ебаклак", True),
    ("блямба", True),
    ("сукотник", True),
    ("гандонюк", True),
    ("мудачье", True),
    ("залупляндия", True),
    ("шлюхенция", True),
    ("пидорюга", True),
    
    # Проверка минимальной длины
    ("хер", True),
    ("жоп", False),
    ("дро", False),
    ("суч", False),
    ("гнд", False),
    ("мдк", False),
    ("злп", False),
    ("шлх", False),
    ("пдр", False),
    ("хй", False),
    
    # Числовые замены (leet speak)
    ("xy1", True),
    ("p1zd@", True),
    ("3ba7", True),
    ("6149b", True),
    ("cyk@", True),
    ("607d0h", False),
    ("myd@k", True),
    ("241upa", False),
    ("sh1ux@", True),
    ("nud0p", True),
    ("x|_|й", True),
    ("|o|зда", True),
    ("ёьа1", True),
    ("6ля9ь", True),
    ("(_)ка", True),
    
    # Комбинации с разрешенными словами
    ("ахуенный", True),
    ("пиздатый", True),
    ("ебануться", True),
    ("блядский", True),
    ("сука ты", True),
    ("гандонский", True),
    ("мудаковатый", True),
    ("залупиться", True),
    ("шлюшиный", True),
    ("пидорашка", True),
    ("охуеть", True),
    ("распиздеться", True),
    ("доебываться", True),
    ("ублядок", True),
    ("подсука", True),
    ("гандончик", True),
    ("мудачина", True),
    ("залупень", True),
    ("шлюшенция", True),
    ("пидорама", True),
    
    # Иностранные слова (не должны триггерить)
    ("hello", False),
    ("shit", True),
    ("fuck", True),
    ("bitch", True),
    ("asshole", True),
    ("damn", True),
    ("cunt", True),
    ("dick", True),
    ("pussy", True),
    ("bastard", True),
    
    # Сложные юникод-кейсы
    ("х\u0435р", True),
    ("п\u0456зда", True),
    ("\u0435бал", True),
    ("бл\u044fдь", True),
    ("с\u0443ка", True),
    ("\u0433ондон", True),
    ("м\u0443дак", True),
    ("з\u0430лупа", True),
    ("ш\u043bюха", True),
    ("п\u0438дор", True),
    ("х\u200bуй", True),
    ("п\u200cизда", True),
    ("е\u200dбал", True),
    ("б\u200eлядь", True),
    ("с\u200fука", True),
    
    # Эмодзи и символы
    ("хуй 😈", True),
    ("пизда 🔥", True),
    ("ебал 🖕", True),
    ("блядь 💩", True),
    ("сука 👹", True),
    ("гандон 👺", True),
    ("мудак 🤡", True),
    ("залупа 👻", True),
    ("шлюха 🍑", True),
    ("пидор 🏳️‍🌈", True),
    ("😈 хуй", True),
    ("🔥 пизда", True),
    ("🖕 ебал", True),
    ("💩 блядь", True),
    ("👹 сука", True),
    
    # Граничные кейсы длины
    ("а" * 1000, False),
    ("хуй" * 300, True),
    ("пизда" * 200, True),
    ("блядь" * 150, True),
    ("сука" * 250, True),
    ("п" * 400 + "изда", True),
    ("е" * 300 + "бал", True),
    ("б" * 200 + "лядь", True),
    ("с" * 100 + "ука", True),
    
    # Реальные примеры обхода фильтров
    ("хуюшки-плюшки", True),
    ("пиздато-блядский", True),
    ("ебашиловка", True),
    ("блядюшник", True),
    ("сукодельник", False),
    ("гандонометр", True),
    ("мудакоскоп", True),
    ("залупоглот", True),
    ("шлюходрочка", True),
    ("пидорвалье", True)]

BAD_WORDS_PATH = Path(__file__).parent.parent / "badwords.json"


class TestProfanityFilter:
    
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
                    logger_tests.debug(f'Добавляются слова')
                    profanity.add_censor_words(self.bad_words)
            
            except (FileNotFoundError, json.JSONDecodeError) as err:
                logger_tests.error(
                    f"Ошибка загрузки файла {bad_words_file}:{err}")
                self.bad_words = []
            except Exception as err:
                logger_tests.error(f'Ошибка чтения JSON: {err}', exc_info=True)
        
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
        text = text.replace(" ", "")
        normalized_text = self._normalize_text(text)
        text_lower = str(normalized_text).lower()
        
        # Fast check
        if len(text_lower.strip()) < 3:
            return False
        
        # 1. Быстрая проверка по better_profanity
        if profanity.contains_profanity(text_lower):
            logger_tests.warning(
                'Фильтр 1 better_profanity(полное '
                'совпадение)')
            return True
        
        # 2. Проверка по регулярным выражениям
        if self.base_pattern.search(text_lower):
            logger_tests.warning('Фильтр 2  re1')
            return True
        
        for pattern in self.additional_patterns:
            if pattern.search(text_lower):
                logger_tests.warning('Фильтр 3 re2')
                return True
        
        # 3. Проверка по списку слов (с учетом опечаток)
        words = re.findall(r'\w+', text_lower)
        if any(word in self.bad_words for word in words):
            logger_tests.warning('Фильтр 4 с учетом опечаток')
            return True
        
        # 4. Дополнительные проверки (опционально)
        if self._check_levenshtein(text_lower):
            logger_tests.warning('Фильтр 5 "Levenshtein"')
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
        if len(bad_word) <= 4:
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
                    logger_tests.warning(f'Точное совпадение: {bad_word}')
                    return True
                
                # Проверка расстояния Левенштейна с учетом контекста
                if self._is_valid_match(candidate, bad_word):
                    logger_tests.warning(
                        f'Найдено по Левенштейну: {bad_word} '
                        f'(кандидат: {candidate}, расстояние: {distance(candidate, bad_word)})')
                    return True
        
        return False

def test_comment_filter():
    profanity_filter = TestProfanityFilter()
    passed = 0
    
    for comment, expected in test_cases:
        result = profanity_filter.is_profanity(text=comment)
        if result == expected:
            passed += 1
            print(f'Найдено: {comment}')
        else:
            print(
                f"Тест провален: '{comment}' | Ожидалось: {expected}, Получено: {result}")
    
    print(f"\nРезультат: {passed} из {len(test_cases)} тестов пройдено")
    print(f"Процент успеха: {passed / len(test_cases) * 100:.2f}%")


if __name__ == "__main__":
    test_comment_filter()
