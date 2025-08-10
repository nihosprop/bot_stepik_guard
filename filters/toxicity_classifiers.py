import re
from typing import Dict, List, Optional, Union
import asyncio
import logging

from transformers import Pipeline, pipeline

logger_classifier = logging.getLogger(__name__)


class RussianToxicityClassifier:
    def __init__(self, models: List[str], task: str = 'text-classification'):
        """
        Инициализация классификатора токсичности.

        :param models: Список моделей для попытки загрузки (в порядке приоритета)
        :param task: Тип задачи для pipeline (по умолчанию 'text-classification')
        """
        self.task = task
        self.models = models
        self.classifier: Pipeline | None = None
        self.loaded_model_name: str | None = None
    
    async def initialize(self) -> None:
        """Инициализирует классификатор (должен быть вызван перед использованием)"""
        for model_name in self.models:
            try:
                self.classifier = await asyncio.to_thread(
                    pipeline,
                    task="text-classification",
                    model=model_name,
                    tokenizer=model_name,
                    device="cpu",
                    framework="pt")
                self.loaded_model_name = model_name
                return
            except Exception as e:
                print(f"Failed to load {model_name}: {str(e)}")
                continue
        
        raise RuntimeError("All models failed to load")
    
    @staticmethod
    async def _normalized_text(text: str) -> str:
        normalized_text = re.sub(r'(.)\1+', r'\1', text)
        return normalized_text
    
    async def predict(self, text: str, threshold: float = 0.5) -> Dict[
        str, Union[str, float, bool]]:
        """
        Асинхронно предсказывает токсичность текста.

        :param text: Текст для анализа
        :param threshold: Порог уверенности для классификации
        :return: Словарь с результатом и метаданными.
        """
        if not self.classifier:
            raise RuntimeError("Classifier didn't initialize")
        
        try:
            result = await asyncio.to_thread(
                self.classifier,
                await self._normalized_text(text))
            logger_classifier.debug(f"{result=}")
            first_result = result[0]
            
            is_toxic = (
                first_result['label'] == 'toxic' if 'label' in first_result else
                first_result['label'] == 'LABEL_1')
            confidence = first_result['score']
            
            return {
                'text': text,
                'is_toxic': is_toxic and (confidence >= threshold),
                'confidence': confidence}
        
        except Exception as e:
            print(f"Prediction error: {str(e)}")
            return {
                'text': text,
                'error': str(e),
                'is_toxic': False,
                'confidence': 0.0}
    
    async def batch_predict(self, texts: List[str], threshold: float = 0.5) -> \
        List[Dict[str, Union[str, float, bool]]]:
        """
        Асинхронно обрабатывает список текстов.

        :param texts: Список текстов для анализа
        :param threshold: Порог уверенности для классификации
        :return: Список результатов
        """
        tasks = [self.predict(text, threshold) for text in texts]
        return await asyncio.gather(*tasks)
    
    async def get_model_info(self) -> Dict[str, Optional[str]]:
        """Возвращает информацию о загруженной модели."""
        if not self.loaded_model_name:
            return {}
        
        return {
            'model_name': self.loaded_model_name,
            'task': self.task,
            'status': 'loaded' if self.classifier else 'failed'}
