import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp
from redis.asyncio import Redis

logger_stepik = logging.getLogger(__name__)


@dataclass
class StepikAPIClient:
    client_id: str
    client_secret: str
    redis_client: Redis
    
    async def reset_stepik_token(self) -> None:
        await self.redis_client.delete('stepik_token')
        logger_stepik.info('Stepik_token is cleared')
    
    async def _get_access_token(self) -> str:
        """
        Получает токен доступа для Stepik API.
        :return str: Токен доступа
        :raises: RuntimeError, если не удалось получить токен.
        """
        
        cached_token = await self.redis_client.get('stepik_token')
        url = 'https://stepik.org/oauth2/token/'
        
        if cached_token:
            # logger_stepik.debug('Используется кэшированный токен из Redis.')
            return cached_token
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret}
        
        try:
            async with (aiohttp.ClientSession() as session):
                async with session.post(
                    url=url, data=data, allow_redirects=True) as resp:
                    if resp.status != 200:
                        error_message = await resp.text()
                        logger_stepik.error(
                            f'Ошибка при запросе токена: {error_message}',
                            exc_info=True)
                        raise RuntimeError(
                            f'Не удалось получить токен: {error_message}')
                    response = await resp.json()
                    access_token = response.get('access_token')
                    if not access_token:
                        raise RuntimeError('Токен не найден в ответе API.')
                    try:
                        # Сохраняем токен в Redis с TTL
                        await self.redis_client.set(
                            'stepik_token', access_token, ex=35000)
                        logger_stepik.info(
                            'Токен успешно получен и сохранён в Redis.')
                    except Exception as e:
                        logger_stepik.error(
                            f'Ошибка сохранения токена в '
                            f'Redis: {e}')
                        raise
                    return access_token
        
        except aiohttp.ClientError as err:
            logger_stepik.error(
                f'Ошибка сети при запросе токена: {err}', exc_info=True)
            raise RuntimeError(f'Ошибка сети: {err}')
        
        except Exception as err:
            logger_stepik.error(
                f'Неожиданная ошибка при запросе токена: {err}', exc_info=True)
            raise RuntimeError(f'Неожиданная ошибка: {err}')
    
    async def make_api_request(self,
                               method: str,
                               endpoint: str,
                               params: Optional[Dict[str, Any]] = None,
                               json_data: Optional[Dict[str, Any]] = None) -> \
        Dict[str, Any]:
        """Базовый метод для выполнения API-запросов"""
        
        url = f"https://stepik.org/api/{endpoint.lstrip('/')}"
        headers = {"Authorization": f"Bearer {await self._get_access_token()}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data) as response:
                if response.status == 200:
                    return await response.json()
                
                # Попробуем прочитать тело для диагностики
                try:
                    body_text = await response.text()
                except Exception:
                    body_text = "<no-body>"
                
                # Точное различение статусов
                if response.status == 404:
                    logger_stepik.info(
                        f"Stepik API 404 on {method} {url}. Body: {body_text}")
                    raise ValueError("not_found")
                if response.status in (401, 403):
                    logger_stepik.warning(
                        f"Stepik API {response.status} on {method} {url}. Body: {body_text}")
                    raise PermissionError(f"forbidden:{response.status}")
                if response.status == 429:
                    logger_stepik.warning(
                        f"Stepik API 429 on {method} {url}. Body: {body_text}")
                    raise Exception("too_many_requests")
                
                logger_stepik.error(
                    f"API request failed: {response.status}. Body: {body_text}")
                raise Exception(f"API request failed: {response.status}")
    
    async def get_user(self, user_id: int) -> Dict[str, Any] | None:
        """
        Get user data through a common client with retrays.
        Returns a user dictionary or None with an error/absence.
        
        """
        try:
            data = await self.make_api_request('GET', f'users/{user_id}')
            users = data.get('users') or []
            return users[0] if users else None
        except ValueError:
            # not_found
            logger_stepik.info(f"User not found: id={user_id}")
            return None
        except PermissionError as e:
            logger_stepik.warning(f"Forbidden while fetching user id={user_id}: {e}")
            return None
        except Exception as e:
            logger_stepik.error(f"Failed to fetch user id={user_id}: {e}")
            return None
    
    async def get_username(self, user_id: int) -> str | None:
        user = await self.get_user(user_id)
        return (user or {}).get('full_name') or None
    
    async def get_course(self, course_id: int):
        course = await self.make_api_request('GET', f'courses/{course_id}')
        return course
    
    async def get_course_title(self, course_id: int) -> str | None:
        course_data = await self.get_course(course_id)
        return course_data.get('courses')[0].get('title')
    
    async def get_section(self, course_id: int) -> List[int]:
        sections_data = await self.make_api_request(
            method='GET', endpoint=f'courses/{course_id}')
        sections = sections_data['courses'][0]['sections']
        return sections
    
    async def get_unit(self, section_id: int) -> List[int]:
        units_data = await self.make_api_request(
            method='GET', endpoint=f'sections/{section_id}')
        unit = units_data['sections'][0]['units']
        return unit
    
    async def get_step_data(self, target_id: int) -> Dict[str, Any]:
        return await self.make_api_request('GET', f'steps/{target_id}')
    
    async def get_step(self, comment_id) -> int:
        comment_data = await self.get_comment_data(comment_id)
        comment = comment_data.get('comments')[0]
        target_id = comment.get('target')
        step_data = await self.get_step_data(target_id=target_id)
        return step_data.get('steps')[0]
    
    async def get_comment_data(self, comment_id: int) -> Dict[str, Any]:
        comment = await self.make_api_request('GET', f'comments/{comment_id}')
        return comment
    
    async def get_target_id(self, comment_id: int) -> int | None:
        comment = await self.get_comment_data(comment_id=comment_id)
        target_id = comment['comments'][0]['target']
        return target_id
    
    async def get_lesson_id(self, unit_id: int) -> Optional[int]:
        lesson_data = await self.make_api_request('GET', f'units/{unit_id}')
        lesson_id = lesson_data['units'][0]['lesson']
        return lesson_id
    
    async def get_comment_url(self, comment_id: int) -> str:
        
        try:
            # Получаем данные комментария
            comment_data = await self.get_comment_data(comment_id)
            if not comment_data or not comment_data.get('comments'):
                return f"https://stepik.org/discussion/comments/{comment_id}/"
            
            comment = comment_data['comments'][0]
            parent_id = comment.get('parent')
            thread_type = comment.get('thread', 'discussion')
            
            # Получаем данные шага
            target_id = comment.get('target')
            if not target_id:
                return f"https://stepik.org/discussion/comments/{comment_id}/"
            
            step_data = await self.get_step_data(target_id)
            if not step_data or not step_data.get('steps'):
                return f"https://stepik.org/discussion/comments/{comment_id}/"
            
            step = step_data['steps'][0]
            lesson_id = step.get('lesson')
            step_position = step.get('position', 1)
            unit_id = step.get('unit')
            
            # Базовые параметры URL
            base_url = f'https://stepik.org/lesson/{lesson_id}/step/{step_position}?'
            
            # Определяем параметры в зависимости от типа комментария
            params = []
            
            if thread_type == 'solutions':
                if parent_id:
                    # Для ответов в решениях используем parent_id в discussion
                    params.append(f"discussion={parent_id}")
                    params.append(f"reply={comment_id}")
                else:
                    # Для корневых комментариев в решениях
                    params.append(f"discussion={comment_id}")
                params.append("thread=solutions")
                
            # Обработка обычных комментариев
            else:
                discussion_param = parent_id if parent_id else comment_id
                params.append(f"discussion={discussion_param}")
                if parent_id:
                    params.append(f"reply={comment_id}")
            
            if unit_id:
                params.append(f"unit={unit_id}")
                
                # Собираем итоговый URL
            query_string = '&'.join(params)
            return f"{base_url}{query_string}"
        
        except Exception as e:
            logging.error(
                f"Error generating URL for comment {comment_id}: {str(e)}",
                exc_info=True)
            return f"https://stepik.org/discussion/comments/{comment_id}/"
    
    async def get_comments(self, course_id: int, limit: int = 100) -> Dict[
        str, Any]:
        """
        Получение списка комментариев по ID курса
        :param course_id:
        :param limit:
        :return:
        """
        params = {
            "page_size": limit,
            "course": course_id,
            'sort': 'time',
            "order": "desc"}
        
        comments = await self.make_api_request(
            "GET", "comments", params=params)
        
        return comments
    
    @staticmethod
    async def analyze_comment_text(text: str, banned_words: list) -> bool:
        """Анализ текста комментария на наличие запрещенных слов"""
        return any(bad_word.lower() in text.lower() for bad_word in banned_words)
    
    async def delete_comment(self, comment_id: int) -> bool:
        """Удаление комментария через DELETE-запрос"""
        
        url = f"https://stepik.org/api/comments/{comment_id}"
        headers = {"Authorization": f"Bearer {await self._get_access_token()}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status in (200, 204):
                    logger_stepik.warning('Удален подозрительный коммент')
                    return True
                logger_stepik.error(
                    f"Ошибка удаления: {response.status} {await response.text()}")
                return False
