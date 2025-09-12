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
            logger_tasks.debug(f'{user=}')
            
            link_to_user_profile: str = f'{users_url}{user_stepik_id}/profile'
            course_title: str = comment.get('course_title')
            course_id = comment.get('course_id')
            
            link_to_course: str = await self.stepik_client.get_link_to_course(
                course_id=course_id)
            
            comment_id = comment.get('id')
            
            section_position, lesson_position, step_position = await (
                self.stepik_client.get_comment_context(comment_id))
            
            lesson_position = f'{section_position}.{lesson_position}'
            
            link_to_comment: str = await self.stepik_client.get_comment_url(
                comment_id=comment_id)
            
            comment_text = await clean_html_tags(comment.get('text'))
            user_name = user.get('full_name')
            reputation: int | str = user.get('reputation')
            count_steps: int | str = user.get('solved_steps_count')
            comment_time = datetime.strptime(
                comment.get('time'), '%Y-%m-%dT%H:%M:%SZ')
            
            full_user_info = (f'<b><a href="{link_to_course}"'
                              f'>{course_title}</a></b>\n'
                              f'🧑‍🎓 <a href="{link_to_user_profile}">'
                              f' {user_name}</a>\n'
                              f'<b>Progress:</b> {count_steps}\n'
                              f'<b>Reputation:</b> {reputation}\n'
                              f'🕘 <b>Comment time</b>: {comment_time}UTC\n'
                              f'🔗 <a href="{link_to_comment}">Comment ID'
                              f'[{comment_id}]</a>\n'
                              f'({lesson_position} шаг {step_position})\n\n'
                              f'{comment_text}')
            
            light_user_info = (f'<b>{course_title}</b>\n'
                               f'🧑‍🎓 <a href="{link_to_user_profile}">'
                               f' {user_name}</a>\n'
                               f'🔗 <a href="{link_to_comment}">Comment ID'
                               f'[{comment_id}]</a>\n\n'
                               f'{comment_text}')
            
            result_profanity_filter: bool = await profanity_filter.is_profanity(
                text=comment_text)
            logger_tasks.debug(f'{result_profanity_filter=}')
            
            text_solution_low = 'Решение 🟡\n'
            text_solution_high = 'Решение 🟢\n'
            text_comment_low = 'Комментарий 🟡\n'
            text_comment_high = 'Комментарий 🟢\n'
            text_remove = f"🚨 Удалить! 🚨\n"
            
            flag_low_comment: bool = (len(set(comment_text)) <= 2) or (len(
                comment_text) <= 3)
            
            flag_solution_comment: bool = 'thread=solutions' in link_to_comment
            if not flag_solution_comment:
                res_text: str = (text_comment_high, text_comment_low)[
                    flag_low_comment]
            else:
                res_text: str = (text_solution_high, text_solution_low)[
                    flag_low_comment]
            
            lpw_options = LinkPreviewOptions(is_disabled=True)
            have_avatar = await self.stepik_client.check_user_avatar(
                user_stepik_id)
            
            comment_statuses: list[str] = []
            if flag_low_comment:
                comment_statuses.append('solution')
            if not flag_low_comment:
                comment_statuses.append('informative')
                if have_avatar:
                    lpw_options = LinkPreviewOptions(
                        is_disabled=False, url=link_to_user_profile)
            else:
                comment_statuses.append('uninformative')
                light_user_info = res_text + light_user_info
            
            if result_profanity_filter and len(comment_text) >= 12:
                result_toxicity_classifier = await toxicity_filter.predict(
                    comment_text.lower(), threshold=0.82)
                logger_tasks.debug(f'{result_toxicity_classifier=}')
                
                if result_toxicity_classifier.get('is_toxic'):
                    full_user_info = text_remove + full_user_info
                    comment_statuses.append('toxic')
                    logger_tasks.warning(f'Toxicity filter: {full_user_info}')
                else:
                    full_user_info = res_text + full_user_info
                    logger_tasks.debug(f'{full_user_info}')
            elif result_profanity_filter:
                full_user_info = text_remove + full_user_info
                comment_statuses.append('toxic')
                logger_tasks.warning(f'Profanity filter: {full_user_info}')
            else:
                full_user_info = res_text + full_user_info
            
            for user in all_users:
                # Если у пользователя активно любое FSM-состояние — пропускаем отправку
                try:
                    if self.storage is not None:
                        key = StorageKey(
                            bot_id=self.bot.id, chat_id=user, user_id=user)
                        state = await self.storage.get_state(key)
                        if state:
                            logger_tasks.info(
                                f"Skip notify tg_id={user} due to active FSM state: {state}")
                            continue
                except Exception as e:
                    logger_tasks.debug(
                        f"FSM state check failed for tg_id={user}: {e}")
                
                user_notifications: dict[str, bool] = await (
                    self.redis_service.get_user_notif(tg_user_id=user))
                
                if 'toxic' in comment_statuses:
                    pass
                else:
                    if ('solution' in comment_statuses
                        and not user_notifications.get(
                            'is_notif_solution', True)):
                        continue
                    if ('uninformative' in comment_statuses
                        and not user_notifications.get(
                        'is_notif_uninformative', True)):
                        continue
                
                try:
                    await self.bot.send_message(
                        link_preview_options=lpw_options,
                        chat_id=user,
                        text=light_user_info if flag_low_comment else full_user_info)
                    await asyncio.sleep(0.5)
                
                except TelegramBadRequest as err:
                    
                    if 'chat not found' in err.message.lower():
                        logger_tasks.warning(
                            f'Chat not found for: tg_id={user}')
                    elif 'message is too long' in err.message.lower():
                        logger_tasks.warning(
                            f'Message too long for: tg_id={user}')
                
                except TelegramForbiddenError as err:
                    logger_tasks.warning(f'Forbidden for tg_id={user}: {err}')
