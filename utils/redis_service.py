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
        tg_id (str): The key for the user's Telegram ID in the Redis database.
        tg_username (str): The key for the user's Telegram username in the
            Redis database.
        user_tag (str): The tag for the user's hash in the Redis database.
        users_list_set (str): The key for the set of users in the Redis database.
        owner_tag (str): The tag for the owner's hash in the Redis database.
        owners_list_set (str): The key for the set of owners in the Redis database.
        stepik_course_id (str): The key for the Stepik course ID in the Redis database.
        stepik_ids_set (str): The key for the set of Stepik course IDs in the Redis database.
    
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
    
    tg_id: str = 'tg_id'
    tg_username: str = 'tg_username'
    
    user_tag: str = 'bot:user'
    users_list_set: str = 'bot:users'
    
    owner_tag: str = 'bot:owner'
    owners_list_set: str = 'bot:owners'
    
    stepik_course_id: str = 'stepik_course_id'
    stepik_ids_set: str = 'bot:stepik_course_ids'
    
    async def add_user(self, tg_user_id: int):
        """
        Adds a user to the Redis database.
        Args:
            tg_user_id (int): The unique identifier of the user to be added.
        """
        
        user_key = f'{self.user_tag}:{tg_user_id}'
        
        pipe = self.redis.pipeline(transaction=True)
        await pipe.hset(
            name=user_key, mapping={self.tg_id: tg_user_id})
        await pipe.sadd(self.users_list_set, str(tg_user_id))
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
        
        user_key = f'{self.user_tag}:{tg_user_id}'
        await self.redis.hset(
            name=user_key,
            mapping={self.tg_username: tg_nickname, 'tg_link': tg_link})
    
    async def remove_user(self, tg_user_id: int):
        """
        Removes a user from the Redis database.
        Args:
            tg_user_id (int): The unique identifier of the user to be removed.
        """
        if not await self.check_user(tg_user_id):
            return
        
        user_key = f'{self.user_tag}:{tg_user_id}'
        await self.redis.delete(user_key)
        await self.redis.srem(self.users_list_set, str(tg_user_id))
    
    async def check_user(self, tg_user_id: int) -> bool:
        """
        Checks if a user exists in the Redis database.
        Args:
            tg_user_id (int): The unique identifier of the user to be checked.
        Returns:
            bool: True if the user exists, False otherwise.
        """
        return await self.redis.hexists(
            name=f'{self.user_tag}:{tg_user_id}', key=self.tg_id)
    
    async def get_tg_users_ids(self) -> list[int]:
        """
        Returns a list of all users in the Redis database.
        Returns:
            list[int]: A list of unique user identifiers.
        """
        users = await self.redis.smembers(self.users_list_set)
        return [int(user) for user in users]
    
    async def get_users_info(self) -> str:
        """
        Returns a string containing information about all users in the Redis
            database.
        Returns:
            str: A string containing information about all users in the Redis
            database.
        """
        users_ids = await self.redis.smembers(self.users_list_set)
        if not users_ids:
            return ''
        
        str_users_ids = [str(user_id) for user_id in users_ids]
        keys = [f'{self.user_tag}:{user_id}' for user_id in str_users_ids]
        
        pipe = self.redis.pipeline(transaction=False)
        
        for key in keys:
            await pipe.hgetall(key)
        
        users: list[dict] = await pipe.execute()
        
        row_users = ''
        
        for user in users:
            username = user.get(self.tg_username)
            tg_id = int(user.get(self.tg_id))
            
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
            self.stepik_ids_set, str(course_id))
        return bool(result)
    
    async def add_stepik_course_id(self, course_id: int) -> bool:
        """
        Adds a Stepik course ID to the Redis database.
        Args:
            course_id (int): The unique identifier of the Stepik course.
        Returns:
            bool: True if the course ID was added, False otherwise.
        """
        if await self.check_stepik_course_id(course_id):
            return False
        
        try:
            data = await self.stepik_client.get_course(course_id)
            if not data or not data.get('courses'):
                return False
        except Exception as e:
            logger.error(
                f'Error adding course ID:{course_id} to Redis: {e}',
                exc_info=True)
            return False
        
        await self.redis.sadd(self.stepik_ids_set, str(course_id))
        logger.info(f'Course ID:{course_id} added to Redis')
        return True
    
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
        
        await self.redis.srem(self.stepik_ids_set, str(course_id))
        logger.info(f'Course ID:{course_id} removed from Redis')
        return True
    
    async def get_stepik_course_ids(self) -> list[int]:
        """
        Returns a list of all Stepik course IDs in the Redis database.
        Returns:
            list[int]: A list of unique course identifiers.
        """
        return [int(course_id) for course_id in
            (await self.redis.smembers(self.stepik_ids_set))]
    
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
        
        owner_key = f'{self.owner_tag}:{tg_user_id}'
        pipe = self.redis.pipeline(transaction=True)
        
        await pipe.hset(
            name=owner_key,
            mapping={
                self.tg_id: tg_user_id,
                self.tg_username: tg_nickname,
                'tg_link': tg_link})
        
        await pipe.sadd(self.owners_list_set, str(tg_user_id))
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
        owner_ids = await self.redis.smembers(self.owners_list_set)
        
        if not owner_ids:
            return ''
        
        keys = [f'{self.owner_tag}:{owner_id}' for owner_id in owner_ids]
        
        pipe = self.redis.pipeline(transaction=False)
        for key in keys:
            await pipe.hgetall(key)
        
        owners_hashes: list[dict] = await pipe.execute()
        rows: list[str] = []
        
        for owner in owners_hashes:
            username = owner.get(self.tg_username)
            tg_id_raw = owner.get(self.tg_id)
            link = owner.get('tg_link') or ''
            
            if not link:
                if tg_id_raw:
                    link = f'tg://user?id={tg_id_raw}'
            
            # Без id формировать строку не имеет смысла
            if tg_id_raw and link:
                text = f'{username}'
                rows.append(f'👑 <a href="{link}">{text}</a>')
        
        return '\n'.join(rows)
