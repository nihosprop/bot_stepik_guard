import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import LinkPreviewOptions

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
    
    async def check_comments(self,
                             profanity_filter: ProfanityFilter,
                             toxicity_filter: RussianToxicityClassifier):
        logger_tasks.debug("🟢Начало проверки комментариев")
        
        all_comments = []
        stepik_courses_ids: list[
            int] = await self.redis_service.get_stepik_course_ids()
        
        if not stepik_courses_ids:
            logger_tasks.info('Нет активных курсов')
            return
        
        redis_tg_users: list[int] = await self.redis_service.get_tg_users_ids()
        all_users: set[int] = set(self.owners + redis_tg_users)
        
        for course_id in stepik_courses_ids:
            logger_tasks.debug(f'Поиск в {course_id=}')
            
            course_title = await self.stepik_client.get_course_title(
                course_id=course_id)
            
            redis_key = f'{course_id}:time_last_comment'
            time_last_comment_str = await self.stepik_client.redis_client.get(
                redis_key)
            
            if time_last_comment_str is None:
                time_last_comment = datetime.now() - timedelta(hours=1)
            else:
                try:
                    time_last_comment: datetime = datetime.strptime(
                        time_last_comment_str, '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    time_last_comment = datetime.now() - timedelta(hours=1)
            
            comments_data: dict[str, Any] = await (
                self.stepik_client.get_comments(
                    course_id=course_id))
            
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
            # logger_tasks.debug(f'{user=}')
            
            link_to_user_profile: str = f'{users_url}{user_stepik_id}/profile'
            course_title: str = comment.get('course_title')
            course_id = comment.get('course_id')
            comment_id = comment.get('id')
            link_to_comment: str = await self.stepik_client.get_comment_url(
                comment_id=comment_id)
            comment_text = clean_html_tags(comment.get('text'))
            user_name = user.get('full_name')
            reputation: int = user.get('reputation')
            count_steps: int = user.get('solved_steps_count')
            reputation_rank: int = user.get('reputation_rank')
            comment_time = datetime.strptime(
                comment.get('time'), '%Y-%m-%dT%H:%M:%SZ')
            
            full_user_info = (f'\n<b>{course_title}</b>\n'
                              f'🧑‍🎓 <a href="{link_to_user_profile}">'
                              f' {user_name}</a>\n'
                              f'<b>Reputation:</b> {reputation}\n'
                              f'<b>Reputation Rank:</b> {reputation_rank}\n'
                              f'<b>Сount steps:</b> {count_steps}\n'
                              f'<b>Course ID:</b> {course_id}\n'
                              f'<b>Comment time:</b> {comment_time}\n'
                              f'<b>Comment ID:</b> {comment_id}\n'
                              f'🔗 <a href="{link_to_comment}">Link to Comment</a>\n\n'
                              f'<b>Comment:</b>\n{comment_text}')
            
            light_user_info = (f'\n<b>{course_title}</b>\n'
                               f'🧑‍🎓 <a href="{link_to_user_profile}">'
                               f' {user_name}</a>\n'
                               f'🔗 <a href="{link_to_comment}">Link to Comment</a>\n\n'
                               f'<b>Comment:</b>{comment_text}')
            
            result_profanity_filter: bool = await profanity_filter.is_profanity(
                text=comment_text)
            logger_tasks.debug(f'{result_profanity_filter=}')
            
            text_solution_low = 'Решения 🟡\n'
            text_solution_high = 'Решения 🟢\n'
            text_comment_low = 'Статус 🟡\n'
            text_comment_high = 'Статус 🟢\n'
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
            if flag_low_comment:
                lpw_options = None
            
            for owner in all_users:
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
