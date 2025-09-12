import logging
from dataclasses import dataclass

from redis.asyncio import Redis

from utils.stepik import StepikAPIClient

logger = logging.getLogger(__name__)


@dataclass
class RedisService:
    """
    RedisService class for interacting with Redis database.
    
    Attributes:
        redis (Redis): An instance of the Redis class for interacting with
            Redis database.
        stepik_client (StepikAPIClient): An instance of the StepikAPIClient
            class for interacting with Stepik API.
        TG_ID (str): The key for the user's Telegram ID in the Redis database.
        TG_USERNAME (str): The key for the user's Telegram username in the
            Redis database.
        USER_TAG (str): The tag for the user's hash in the Redis database.
        USERS_LIST_SET (str): The key for the set of users in the Redis database.
        OWNER_TAG (str): The tag for the owner's hash in the Redis database.
        OWNERS_LIST_SET (str): The key for the set of owners in the Redis database.
        STEPIK_COURSE_ID (str): The key for the Stepik course ID in the Redis database.
        STEPIK_IDS_SET (str): The key for the set of Stepik course IDs in the Redis database.
    
    Methods:
        add_user(self, tg_user_id: int): Adds a user to the Redis database.
        update_user_username(self, tg_user_id: int, tg_nickname: str): Updates the username of a user in the Redis database.
        add_owner(self, tg_user_id: int, tg_nickname: str): Adds an owner to the Redis database.
        remove_user(self, tg_user_id: int): Removes a user from the Redis database.
        check_user(self, tg_user_id: int): Checks if a user exists in the Redis database.
        get_tg_users_ids(self): Returns a list of all users in the Redis database.
        get_users_info(self): Returns a string containing information about all users in the Redis database.
        get_owners_info(self): Returns a string containing information about all owners in the Redis database.
        check_stepik_course_id(self, course_id: int): Checks if a Stepik course ID exists in the Redis database.
        add_stepik_course_id(self, course_id: int): Adds a Stepik course ID to the Redis database.
        remove_stepik_course_id(self, course_id: int): Removes a Stepik course ID from the Redis database.
        get_stepik_course_ids(self): Returns a list of all Stepik course IDs in the Redis database.
        
    """
    redis: Redis
    stepik_client: StepikAPIClient
    
    TG_ID: str = 'tg_id'
    TG_USERNAME: str = 'tg_username'
    
    IS_NOTIF_SOLUTION: str = 'is_notif_solution'
    IS_NOTIF_UNINFORMATIVE: str = 'is_notif_uninformative'
    
    USER_TAG: str = 'bot:user'
    USERS_LIST_SET: str = 'bot:users'
    
    OWNER_TAG: str = 'bot:owner'
    OWNERS_LIST_SET: str = 'bot:owners'
    
    STEPIK_COURSE_ID: str = 'stepik_course_id'
    STEPIK_IDS_SET: str = 'bot:stepik_course_ids'
    
    async def add_user(self, tg_user_id: int):
        """
        Adds a user to the Redis database.
        Args:
            tg_user_id (int): The unique identifier of the user to be added.
        """
        
        user_key = f'{self.USER_TAG}:{tg_user_id}'
        
        pipe = self.redis.pipeline(transaction=True)
        await pipe.hset(
            name=user_key,
            mapping={
                self.TG_ID: tg_user_id,
                self.IS_NOTIF_SOLUTION: '1',
                self.IS_NOTIF_UNINFORMATIVE: '1'})
        await pipe.sadd(self.USERS_LIST_SET, str(tg_user_id))
        await pipe.execute()
        logger.info(f'User TG_ID:{tg_user_id} added to Redis')
    
    async def update_user_username(self,
                                   tg_user_id: int,
                                   tg_nickname: str | None) -> None:
        """
        Updates the username of a user in the Redis database.
        Args:
            tg_user_id (int): The unique identifier of the user to be updated.
            tg_nickname (str | None): The new nickname of the user.
        Returns:
            None
        """
        
        if not await self.check_user(tg_user_id):
            return
        
        if tg_nickname and tg_nickname.startswith('@'):
            tg_link = f'https://t.me/{tg_nickname[1:]}'
        else:
            tg_link = f'tg://user?id={tg_user_id}'
        
        user_key = f'{self.USER_TAG}:{tg_user_id}'
        await self.redis.hset(
            name=user_key,
            mapping={self.TG_USERNAME: tg_nickname, 'tg_link': tg_link})
    
    async def remove_user(self, tg_user_id: int):
        """
        Removes a user from the Redis database.
        Args:
            tg_user_id (int): The unique identifier of the user to be removed.
        """
        if not await self.check_user(tg_user_id):
            return
        
        user_key = f'{self.USER_TAG}:{tg_user_id}'
        await self.redis.delete(user_key)
        await self.redis.srem(self.USERS_LIST_SET, str(tg_user_id))
    
    async def check_user(self, tg_user_id: int) -> bool:
        """
        Checks if a user exists in the Redis database.
        Args:
            tg_user_id (int): The unique identifier of the user to be checked.
        Returns:
            bool: True if the user exists, False otherwise.
        """
        return await self.redis.hexists(
            name=f'{self.USER_TAG}:{tg_user_id}', key=self.TG_ID)
    
    async def get_tg_users_ids(self) -> list[int]:
        """
        Returns a list of all users in the Redis database.
        Returns:
            list[int]: A list of unique user identifiers.
        """
        users = await self.redis.smembers(self.USERS_LIST_SET)
        return [int(user) for user in users]
    
    async def update_notif_flag(self,
                                tg_user_id: int,
                                is_notif_solution: bool = None,
                                is_notif_uninformative: bool = None) -> bool:
        """
        Updates the notification flags for a user in the Redis database.
        
        Args:
            tg_user_id (int): The unique identifier of the user to be updated.
            is_notif_solution (bool): The new value of the is_notif_solution flag.
            is_notif_uninformative (bool): The new value of the is_notif_uninformative flag.
        Returns:
            bool: True if the update was successful, False otherwise.
        Example:
            await update_notification_flag(tg_user_id=123456789,
                                          is_notif_solution=True,
                                          is_notif_uninformative=False)
        """
        if not await self.check_user(tg_user_id):
            logger.warning(
                f'User {tg_user_id} not found when updating notification flags')
            return False
        
        # Check that at least one flag has been transferred
        if all(f is None for f in [is_notif_solution, is_notif_uninformative]):
            logger.warning('No flags provided for update')
            return False
        user_key = f'{self.USER_TAG}:{tg_user_id}'
        
        updates = {}
        
        # Updates only for the transferred flags
        if is_notif_solution is not None:
            updates[self.IS_NOTIF_SOLUTION] = '1' if is_notif_solution else '0'
            logger.debug(
                f'Updating {self.IS_NOTIF_SOLUTION} to {is_notif_solution}')
        
        if is_notif_uninformative is not None:
            updates[
                self.IS_NOTIF_UNINFORMATIVE] = '1' if is_notif_uninformative else '0'
            logger.debug(
                f'Updating {self.IS_NOTIF_UNINFORMATIVE} to {is_notif_uninformative}')
        
        # Update all flags
        if updates:
            await self.redis.hset(user_key, mapping=updates)
            logger.info(
                f'Updated notification flags for user {tg_user_id}: {updates}')
            return True
        return False
    
    async def get_notif_flag(self, tg_user_id: int) -> bool | dict[str, bool]:
        """
        Returns the notification flags for a user in the Redis database.
        Args:
            tg_user_id (int): The unique identifier of the user to be checked.
        Returns:
            bool | dict[str, bool]: The notification flags for the user.
        """
        if not await self.check_user(tg_user_id):
            logger.warning(
                f'User {tg_user_id} was not found when receiving notifications settings')
            return False
        
        user_key = f'{self.USER_TAG}:{tg_user_id}'
        
        flags = await self.redis.hmget(
            name=user_key, keys=[
                self.IS_NOTIF_SOLUTION, self.IS_NOTIF_UNINFORMATIVE])
        return {
            'is_notif_solution':
                flags[0] == '1' if flags[0] is not None else True,
            'is_notif_uninformative':
                flags[1] == '1' if flags[1] is not None else True}
    
    async def get_users_info(self) -> str:
        """
        Returns a string containing information about all users in the Redis
            database.
        Returns:
            str: A string containing information about all users in the Redis
            database.
        """
        users_ids = await self.redis.smembers(self.USERS_LIST_SET)
        if not users_ids:
            return ''
        
        str_users_ids = [str(user_id) for user_id in users_ids]
        keys = [f'{self.USER_TAG}:{user_id}' for user_id in str_users_ids]
        
        pipe = self.redis.pipeline(transaction=False)
        
        for key in keys:
            await pipe.hgetall(key)
        
        users: list[dict] = await pipe.execute()
        
        row_users = ''
        
        for user in users:
            username = user.get(self.TG_USERNAME)
            tg_id = int(user.get(self.TG_ID))
            
            link = user.get('tg_link') or ''
            
            if not tg_id:
                continue
            if not link:
                link = f'tg://user?id={tg_id}'
            
            row_users += f'👨‍🎓\n<a href="{link}">{username}:{tg_id}</a>\n'
        
        return row_users
    
    async def check_stepik_course_id(self, course_id: int) -> bool:
        """
        Checks if a Stepik course ID exists in the Redis database.
        Args:
            course_id (int): The unique identifier of the Stepik course.
        Returns:
            bool: True if the course ID exists, False otherwise.
        """
        result: int = await self.redis.sismember(
            self.STEPIK_IDS_SET, str(course_id))
        return bool(result)
    
    async def add_stepik_course_id(self, course_id: int) -> bool | str:
        """
        Adds a Stepik course ID to the Redis database.
        Args:
            course_id (int): The unique identifier of the Stepik course.
        Returns:
            bool | str: True if the course ID was added, False otherwise.
        """
        
        # check if course_id in Redis
        if await self.check_stepik_course_id(course_id):
            logger.info(f'Course ID:{course_id} already exists in Redis')
            return 'Курс уже добавлен'
        
        # check if course_id in Stepik API
        try:
            data = await self.stepik_client.get_course(course_id)
            logger.debug(f'Checked in Stepik API:{data}')
            if not data or not data.get('courses'):
                logger.info(f'Course ID:{course_id} not found in Stepik API')
                return 'Курс не найден на Stepik'
        
        except ValueError as e:
            # Специальная метка из StepikAPIClient.make_api_request
            if str(e) == 'not_found':
                logger.info(
                    f'Course ID:{course_id} not found (404) in Stepik API')
                return 'Курс не найден на Stepik'
            logger.error(
                f'Unexpected ValueError while adding course ID:{course_id}: {e}',
                exc_info=True)
            return 'Ошибка проверки курса на Stepik.'
        
        except PermissionError as e:
            logger.warning(
                f'Permission error (401/403) for course ID:{course_id}: {e}')
            return 'Нет доступа к курсу на Stepik (приватный или недостаточные права).'
        
        except Exception as e:
            if str(e) == 'too_many_requests':
                logger.warning(
                    f'Too many requests to Stepik while adding course ID:{course_id}')
                return 'Слишком много запросов к Stepik. Повторите позже.'
            logger.error(
                f'Error adding course ID:{course_id} to Redis: {e}',
                exc_info=True)
            return 'Ошибка добавления курса, обратитесь к разработчику.'
        
        await self.redis.sadd(self.STEPIK_IDS_SET, str(course_id))
        logger.info(f'Course ID:{course_id} added to Redis')
        return 'added'
    
    async def remove_stepik_course_id(self, course_id: int) -> bool:
        """
        Removes a Stepik course ID from the Redis database.
        Args:
            course_id (int): The unique identifier of the Stepik course.
        Returns:
            bool: True if the course ID was removed, False otherwise.
        """
        if not await self.check_stepik_course_id(course_id):
            return False
        
        await self.redis.srem(self.STEPIK_IDS_SET, str(course_id))
        logger.info(f'Course ID:{course_id} removed from Redis')
        return True
    
    async def get_courses_ids(self) -> list[int]:
        """
        Returns a list of all Stepik course IDs in the Redis database.
        Returns:
            list[int]: A list of unique course identifiers.
        """
        return [int(course_id) for course_id in
            (await self.redis.smembers(self.STEPIK_IDS_SET))]
    
    async def add_owner(self, tg_user_id: int, tg_nickname: str) -> None:
        """
        Adds an owner to the Redis database.
        This method adds an owner to the Redis database with the specified
        Telegram user ID and nickname.

        Args:
            tg_user_id (int): The unique identifier of the Telegram user.
            tg_nickname (str): The nickname of the Telegram user.
        Example:
            await add_owner(tg_user_id=123456789, tg_nickname='username')
        """
        if tg_nickname and isinstance(
            tg_nickname, str) and tg_nickname.startswith('@'):
            tg_link = f'https://t.me/{tg_nickname[1:]}'
        else:
            tg_link = f'tg://user?id={tg_user_id}'
        
        owner_key = f'{self.OWNER_TAG}:{tg_user_id}'
        pipe = self.redis.pipeline(transaction=True)
        
        await pipe.hset(
            name=owner_key,
            mapping={
                self.TG_ID: tg_user_id,
                self.TG_USERNAME: tg_nickname,
                'tg_link': tg_link})
        
        await pipe.sadd(self.OWNERS_LIST_SET, str(tg_user_id))
        await pipe.execute()
    
    async def get_owners_info(self) -> str:
        """
        Returns a string containing information about all owners in the Redis
            database.
        Returns:
            str: A string containing information about all owners in the Redis
            database.
        Example:
            "👑 <a href="tg://user?id=123456789">123456789</a>\n"
            "👑 <a href="tg://user?id=987654321">987654321</a>\n"
    
        """
        owners = await self.redis.smembers(self.OWNERS_LIST_SET)
        
        if not owners:
            return ''
        
        keys = [f'{self.OWNER_TAG}:{owner_id}' for owner_id in owners]
        
        pipe = self.redis.pipeline(transaction=False)
        for key in keys:
            await pipe.hgetall(key)
        
        owners_hashes: list[dict] = await pipe.execute()
        rows: list[str] = []
        
        for owner in owners_hashes:
            username = owner.get(self.TG_USERNAME)
            tg_id = owner.get(self.TG_ID)
            link = owner.get('tg_link') or ''
            
            if not link:
                if tg_id:
                    link = f'tg://user?id={tg_id}'
            
            # Без id формировать строку не имеет смысла
            if tg_id and link:
                text = f'{username}'
                rows.append(f'👑 <a href="{link}">{text}</a>')
        
        return '\n'.join(rows)
