import logging
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timedelta

from utils.stepik import StepikAPIClient

logger_tasks = logging.getLogger(__name__)


@dataclass
class StepikTasks:
    stepik_client: StepikAPIClient
    stepik_courses_ids: list[int] = field(default_factory=list)
    
    async def check_comments(self):
        logger_tasks.info("🟢 Начало проверки комментариев")
        
        all_comments = []
        
        for course_id in self.stepik_courses_ids:
            logger_tasks.debug(f'Поиск в {course_id=}')
            
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
            new_comments = []
            max_comments_time = time_last_comment
            
            for comment in course_comments:
                comment_time_str = comment.get("time")
                
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
        
        banned_words = ['плохое слово']
        users_url = 'https://stepik.org/users/'
        
        for comment in all_comments:
            # logger_tasks.debug(f'Data: {comment=}')
            
            user_stepik_id: int = comment.get('user')
            # logger_tasks.debug(f'{user_stepik_id=}')
            
            user = await self.stepik_client.get_user(user_id=user_stepik_id)
            # logger_tasks.debug(f'{user=}')
            
            link_to_user_profile: str = f'{users_url}{user_stepik_id}/profile'
            lesson_id = comment.get('target')
            comment_id = comment.get('id')
            comment_text = comment.get('text')
            user_name = user.get('full_name')
            reputation: int = user.get('reputation')
            count_steps: int = user.get('solved_steps_count')
            reputation_rank: int = user.get('reputation_rank')
            link_to_comment = 'None'
            
            # TODO добавить инфу название курса, ссылку на коммент
            user_info = (f'User: {user_name}\n'
                         f'Reputation: {reputation}\n'
                         f'Reputation Rank: {reputation_rank}\n'
                         f'Сount steps: {count_steps}\n'
                         f'Link to user: {link_to_user_profile}\n'
                         f'Link to comment: {link_to_comment}\n'
                         f'Comment: {comment_text}')
            
            logger_tasks.debug(user_info)
            
            if await self.stepik_client.analyze_comment_text(
                comment_text, banned_words):
                await self.stepik_client.delete_comment(comment_id=comment_id)
                logger_tasks.warning(
                    f"Found problematic comment: "
                    f"ID_[{comment_id}]\n"
                    f"Text: {comment_text}\n"
                    f"{user_info}")
