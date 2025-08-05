import logging
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timedelta

from aiogram import Bot

from filters.filters import ProfanityFilter
from utils.stepik import StepikAPIClient
from utils.utils import clean_html_tags

logger_tasks = logging.getLogger(__name__)


@dataclass
class StepikTasks:
    stepik_client: StepikAPIClient
    bot: Bot
    owners: list[int] = field(default_factory=list)
    stepik_courses_ids: list[int] = field(default_factory=list)
    
    async def check_comments(self, profanity_filter: ProfanityFilter):
        logger_tasks.info("🟢 Начало проверки комментариев")
        
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
                time_last_comment = datetime.now() - timedelta(hours=12)
            else:
                try:
                    time_last_comment: datetime = datetime.strptime(
                        time_last_comment_str, '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    time_last_comment = datetime.now() - timedelta(hours=12)
            
            comments_data: dict[str, Any] = await (
                self.stepik_client.get_comments(
                    course_id=course_id, limit=2))
            
            course_comments = comments_data.get("comments", [])
            # logger_tasks.debug(f'{course_comments=}')
            new_comments = []
            max_comments_time = time_last_comment
            
            for comment in course_comments:
                comment_time_str = comment.get("time")
                comment.update({'course_title': course_title,
                                'course_id': course_id})
                if not comment_time_str:
                    continue
                
                comment_time: datetime = datetime.strptime(
                    comment_time_str, '%Y-%m-%dT%H:%M:%SZ')
                
                logger_tasks.debug(
                    f'Comment_time:{comment_time.strftime("%Y-%m-%d %H:%M:%S")}')
                logger_tasks.debug(
                    f'Time_last_comment{time_last_comment.strftime("%Y-%m-%d %H:%M:%S")}')
                
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
        
        logger_tasks.info(f"🔵 Найдено {len(all_comments)} новых комментов")
        
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
            comment_text = clean_html_tags(comment.get('text'))
            user_name = user.get('full_name')
            reputation: int = user.get('reputation')
            count_steps: int = user.get('solved_steps_count')
            reputation_rank: int = user.get('reputation_rank')
            comment_time = datetime.strptime(
                comment.get('time'), '%Y-%m-%dT%H:%M:%SZ')
            
            user_info = (f'\nUser: {user_name}\n'
                         f'Course title: {course_title}\n'
                         f'Course ID: {course_id}\n'
                         f'Comment ID: {comment_id}\n'
                         f'Comment time: {comment_time}\n'
                         f'Reputation: {reputation}\n'
                         f'Reputation Rank: {reputation_rank}\n'
                         f'Сount steps: {count_steps}\n'
                         f'Link to user: {link_to_user_profile}\n'
                         f'Comment: {comment_text}')
            
            if await profanity_filter.is_profanity(text=comment_text):
                await self.stepik_client.delete_comment(comment_id=comment_id)
                logger_tasks.warning(
                    f"Problematic comment!!!"
                    f"{user_info}")
                for owner in self.owners:
                    await self.bot.send_message(chat_id=owner,
                                                text=user_info)
            else:
                logger_tasks.debug(user_info)
