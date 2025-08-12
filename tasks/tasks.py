import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timedelta

from aiogram import Bot

from filters.filters import ProfanityFilter
from filters.toxicity_classifiers import RussianToxicityClassifier
from utils.stepik import StepikAPIClient
from utils.utils import clean_html_tags

logger_tasks = logging.getLogger(__name__)


@dataclass
class StepikTasks:
    stepik_client: StepikAPIClient
    bot: Bot
    owners: list[int] = field(default_factory=list)
    stepik_courses_ids: list[int] = field(default_factory=list)
    
    async def check_comments(self,
                             profanity_filter: ProfanityFilter,
                             toxicity_filter: RussianToxicityClassifier):
        logger_tasks.debug("🟢Начало проверки комментариев")
        
        all_comments = []
        
        for course_id in self.stepik_courses_ids:
            logger_tasks.debug(f'Поиск в {course_id=}')
            
            course_title = await self.stepik_client.get_course_title(
                course_id=course_id)
            # logger_tasks.debug(f'Course title: {course_title}')
            
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
            
            comments_data: dict[str, Any] = await (
                self.stepik_client.get_comments(
                    course_id=course_id))
            
            course_comments = comments_data.get("comments", [])
            # logger_tasks.debug(f'{course_comments=}')
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
                
                # logger_tasks.debug(
                #     f'Comment_time:{comment_time.strftime("%Y-%m-%d %H:%M:%S")}')
                # logger_tasks.debug(
                #     f'Time_last_comment{time_last_comment.strftime("%Y-%m-%d %H:%M:%S")}')
                
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
            
            user_info = (f'\n🧑‍🎓<a href={link_to_user_profile}>'
                         f'User: {user_name}</a>\n'
                         f'Reputation: {reputation}\n'
                         f'Reputation Rank: {reputation_rank}\n'
                         f'Сount steps: {count_steps}\n'
                         f'Course title: {course_title}\n'
                         f'Course ID: {course_id}\n'
                         f'Comment ID: {comment_id}\n'
                         f'Comment time: {comment_time}\n'
                         f'👉<a href={link_to_comment}>GO to Comment</a>\n'
                         f'Comment: {comment_text}')
            
            result_profanity_filter: bool = await profanity_filter.is_profanity(
                text=comment_text)
            logger_tasks.debug(f'{result_profanity_filter=}')
            
            if result_profanity_filter and len(comment_text) >= 12:
                result_toxicity_classifier = await toxicity_filter.predict(
                    comment_text.lower(), threshold=0.82)
                logger_tasks.debug(f'{result_toxicity_classifier=}')
                
                if result_toxicity_classifier.get('is_toxic'):
                    temp_text = f"Kомментарий для удаления!\n"
                    user_info = temp_text + user_info
                    logger_tasks.warning(f'Toxicity filter: {user_info}')
                else:
                    logger_tasks.debug(f'Чисто\n{user_info}')
            
            for owner in self.owners:
                await self.bot.send_message(chat_id=owner, text=user_info)
                await asyncio.sleep(0.3)
