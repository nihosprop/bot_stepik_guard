import logging
from dataclasses import dataclass, field
from typing import Any

from utils.stepik import StepikAPIClient

logger_tasks = logging.getLogger(__name__)


@dataclass
class StepikTasks:
    stepik_client: StepikAPIClient
    stepik_courses_ids: list[int] = field(default_factory=list)
    
    async def check_comments(self):
        
        comments = []
        
        for course_id in self.stepik_courses_ids:
            last_comments: dict[str, Any] = await (
                self.stepik_client.get_comments(
                    course_id=course_id, lesson_id=5))
            
            comments.append(last_comments.get("comments", []))
        
        logger_tasks.debug(f'{comments=}')
        
        banned_words = ['плохое слово']
        users_url = 'https://stepik.org/users/'
        
        for comment in comments:
            logger_tasks.debug(f'Data: {comment=}')
            
            user_stepik_id: int = comment.get('user')
            logger_tasks.debug(f'{user_stepik_id=}')
            
            user = await self.stepik_client.get_user(user_id=user_stepik_id)
            logger_tasks.debug(f'{user=}')
            
            link_to_user_profile: str = f'{users_url}{user_stepik_id}/profile'
            lesson_id = comment.get('target')
            logger_tasks.debug(f'{lesson_id=}')
            comment_id = comment.get('id')
            logger_tasks.debug(f'{comment_id=}')
            
            comment_text = comment.get('text')
            user_name = user.get('full_name')
            reputation: int = user.get('reputation')
            count_steps: int = user.get('solved_steps_count')
            reputation_rank: int = user.get('reputation_rank')
            link_to_comment = 'None'
            
            # https://stepik.org/lesson/1631463/step/1?discussion=12012236&unit=1653744
            # https://stepik.org/lesson/<lesson_id>/step/1?discussion=<comment_id>&unit=<unit_id>
            
            user_info = f'User: {user_name}\n'
            f'  Reputation: {reputation}\n'
            f'  Reputation Rank: {reputation_rank}\n'
            f'  Сount steps: {count_steps}\n'
            f'  Link to user: {link_to_user_profile}\n'
            f'  Link to comment: {link_to_comment}\n'
            f'  Comment: {comment_text}'
            
            logger_tasks.debug(f'{user_info=}')
            
            if await self.stepik_client.analyze_comment_text(
            comment_text, banned_words):
                await self.stepik_client.delete_comment(comment_id=comment_id)
                logger_tasks.warning(
                f"Found problematic comment: "
                f"ID_[{comment_id}]\n"
                f"Text: {comment_text}\n"
                f"{user_info}")
