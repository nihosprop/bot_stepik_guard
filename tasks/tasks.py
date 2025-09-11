import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import LinkPreviewOptions
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiohttp import ClientError

from filters.filters import ProfanityFilter
from filters.toxicity_classifiers import RussianToxicityClassifier
from utils.redis_service import RedisService
from utils.stepik import StepikAPIClient
from utils.utils import clean_html_tags

logger_tasks = logging.getLogger(__name__)


@dataclass
class StepikTasks:
    bot: Bot
    stepik_client: StepikAPIClient
    redis_service: RedisService
    owners: list[int] = field(default_factory=list)
    storage: BaseStorage | None = None
    
    async def check_comments(self,
                             profanity_filter: ProfanityFilter,
                             toxicity_filter: RussianToxicityClassifier):
        logger_tasks.debug("🟢Начало проверки комментариев")
        
        all_comments = []
        stepik_courses_ids: list[
            int] = await self.redis_service.get_courses_ids()
        
        if not stepik_courses_ids:
            logger_tasks.info('Нет активных курсов')
            return
        
        redis_tg_users: list[int] = await self.redis_service.get_tg_users_ids()
        all_users: set[int] = set(self.owners + redis_tg_users)
        
        for course_id in stepik_courses_ids:
            try:
                logger_tasks.debug(f'Поиск в {course_id=}')
                
                # TODO: Object course!
                # course_obj = await self.stepik_client.get_course(course_id)
                # logger_tasks.debug(pformat(course_obj, indent=2))
                
                course_title = await self.stepik_client.get_course_title(
                    course_id=course_id)
                comments_data: dict[str, Any] = await (
                    self.stepik_client.get_comments(
                        course_id=course_id))
            except ClientError | TimeoutError as e:
                logger_tasks.warning(
                    f'Skip course {course_id} due to network'
                    f' error: {e}')
                
                # антиспам уведомлений на 7 минут
                key = f'notify_skip_course:{course_id}'
                already_notified = await self.stepik_client.redis_client.get(key)
                
                if not already_notified:
                    await self.stepik_client.redis_client.set(
                        key, '1', ex=420)
                    
                    text = (f'⚠️ Пропущен курс ID: {course_id}\n'
                            f'Причина: сетевая ошибка/таймаут.')
                    
                    for user_id in all_users:
                        try:
                            await self.bot.send_message(
                                chat_id=user_id, text=text)
                            await asyncio.sleep(0.3)
                        except (TelegramBadRequest, TelegramForbiddenError):
                            pass
                continue
            
            except Exception as e:
                logger_tasks.error(
                    f'Skip course {course_id} due to network'
                    f' error: {e}')
                key = f'notify_skip_course:{course_id}'
                already_notified = await self.stepik_client.redis_client.get(key)
                if not already_notified:
                    await self.stepik_client.redis_client.set(key, '1', ex=450)
                    text = (f'⚠️ Пропущен курс ID: {course_id}\n'
                            f'Причина: внутренняя ошибка.\n'
                            f'Обратитесь к разработчику.')
                    for user_id in all_users:  # или self.owners
                        try:
                            await self.bot.send_message(
                                chat_id=user_id, text=text)
                            await asyncio.sleep(0.3)
                        except (TelegramBadRequest, TelegramForbiddenError):
                            pass
                
                continue
            
            redis_key = f'{course_id}:time_last_comment'
            time_last_comment_str = await self.stepik_client.redis_client.get(
                redis_key)
            
            if time_last_comment_str is None:
                time_last_comment = datetime.now() - timedelta(hours=2)
            else:
                try:
                    time_last_comment: datetime = datetime.strptime(
                        time_last_comment_str, '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    time_last_comment = datetime.now() - timedelta(hours=2)
            
            course_comments = comments_data.get("comments", [])
            new_comments = []
            max_comments_time = time_last_comment
            
            for comment in course_comments:
                comment_time_str = comment.get("time")
                comment.update(
                    {'course_title': course_title, 'course_id': course_id})
                if not comment_time_str:
                    continue
                
                comment_time: datetime = datetime.strptime(
                    comment_time_str, '%Y-%m-%dT%H:%M:%SZ')
                
                if comment_time > time_last_comment:
                    new_comments.append(comment)
                    if comment_time > max_comments_time:
                        max_comments_time = comment_time
                    else:
                        break
            
            if new_comments:
                all_comments.extend(new_comments)
                # write last time on comment to redis
                await self.stepik_client.redis_client.set(
                    name=f'{course_id}:time_last_comment',
                    value=max_comments_time.strftime('%Y-%m-%dT%H:%M:%SZ'))
        
        logger_tasks.info(f"🔵Найдено {len(all_comments)} новых комментов")
        
        users_url = 'https://stepik.org/users/'
        
        for comment in all_comments:
            # logger_tasks.debug(f'Data: {comment=}')
            
            user_stepik_id: int = comment.get('user')
            # logger_tasks.debug(f'{user_stepik_id=}')
            
            user = await self.stepik_client.get_user(user_id=user_stepik_id)
            if not user:
                user = {
                    'full_name': 'Unknown',
                    'reputation': '?',
                    'solved_steps_count': '?',
                    'reputation_rank': '?'}
            
            link_to_user_profile: str = f'{users_url}{user_stepik_id}/profile'
            course_title: str = comment.get('course_title')
            course_id = comment.get('course_id')
            comment_id = comment.get('id')
            link_to_comment: str = await self.stepik_client.get_comment_url(
                comment_id=comment_id)
            comment_text = clean_html_tags(comment.get('text'))
            user_name = user.get('full_name')
            reputation: int | str = user.get('reputation')
            count_steps: int | str = user.get('solved_steps_count')
            reputation_rank: int | str = user.get('reputation_rank')
            comment_time = datetime.strptime(
                comment.get('time'), '%Y-%m-%dT%H:%M:%SZ')
            
            full_user_info = (f'\n<b>{course_title}</b>\n'
                              f'🧑‍🎓 <a href="{link_to_user_profile}">'
                              f' {user_name}</a>\n'
                              f'<b>Reputation:</b> {reputation}\n'
                              f'<b>Reputation Rank:</b> {reputation_rank}\n'
                              f'<b>Сount steps:</b> {count_steps}\n'
                              f'<b>Course ID:</b> {course_id}\n'
                              f'<b>Comment time:</b> {comment_time}UTC\n'
                              f'🔗 <a href="{link_to_comment}">Comment ID'
                              f'[{comment_id}]</a>\n\n'
                              f'{comment_text}')
            
            light_user_info = (f'\n<b>{course_title}</b>\n'
                               f'🧑‍🎓 <a href="{link_to_user_profile}">'
                               f' {user_name}</a>\n'
                               f'🔗 <a href="{link_to_comment}">Comment ID'
                               f'[{comment_id}]</a>\n\n'
                               f'{comment_text}')
            
            result_profanity_filter: bool = await profanity_filter.is_profanity(
                text=comment_text)
            logger_tasks.debug(f'{result_profanity_filter=}')
            
            text_solution_low = 'Решения 🟡\n'
            text_solution_high = 'Решения 🟢\n'
            text_comment_low = '🟡'
            text_comment_high = '🟢'
            text_remove = f"🚨 Удалить! 🚨\n"
            
            flag_low_comment: bool = (len(set(comment_text)) <= 2) or (len(
                comment_text) <= 3)
            res_text: str = (text_comment_high, text_comment_low)[
                flag_low_comment]
            
            if result_profanity_filter and len(comment_text) >= 12:
                result_toxicity_classifier = await toxicity_filter.predict(
                    comment_text.lower(), threshold=0.82)
                logger_tasks.debug(f'{result_toxicity_classifier=}')
                
                if result_toxicity_classifier.get('is_toxic'):
                    full_user_info = text_remove + full_user_info
                    logger_tasks.warning(f'Toxicity filter: {full_user_info}')
                else:
                    full_user_info = res_text + full_user_info
                    logger_tasks.debug(f'{full_user_info}')
            elif result_profanity_filter:
                full_user_info = text_remove + full_user_info
                logger_tasks.warning(f'Profanity filter: {full_user_info}')
            else:
                full_user_info = res_text + full_user_info
            
            lpw_options = LinkPreviewOptions(is_disabled=True)
            
            if not flag_low_comment:
                lpw_options = None
            else:
                light_user_info = res_text + light_user_info
            
            for owner in all_users:
                # Если у пользователя активно любое FSM-состояние — пропускаем отправку
                try:
                    if self.storage is not None:
                        key = StorageKey(
                            bot_id=self.bot.id, chat_id=owner, user_id=owner)
                        state = await self.storage.get_state(key)
                        if state:
                            logger_tasks.debug(
                                f"Skip notify tg_id={owner} due to active FSM state: {state}")
                            continue
                except Exception as e:
                    logger_tasks.debug(
                        f"FSM state check failed for tg_id={owner}: {e}")
                try:
                    await self.bot.send_message(
                        link_preview_options=lpw_options,
                        chat_id=owner,
                        text=light_user_info if flag_low_comment else full_user_info)
                    await asyncio.sleep(0.5)
                
                except TelegramBadRequest as err:
                    
                    if 'chat not found' in err.message.lower():
                        logger_tasks.warning(
                            f'Chat not found for: tg_id={owner}')
                    elif 'message is too long' in err.message.lower():
                        logger_tasks.warning(
                            f'Message too long for: tg_id={owner}')
                
                except TelegramForbiddenError as err:
                    logger_tasks.warning(f'Forbidden for tg_id={owner}: {err}')
