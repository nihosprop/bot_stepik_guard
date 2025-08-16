import logging
from dataclasses import dataclass

from aiogram.fsm.storage.redis import Redis

logger = logging.getLogger(__name__)

@dataclass
class RedisService:
    """
    A class for interacting with Redis database.
    """
    redis: Redis
    tg_id: str = 'tg_id'
    stepik_id: str = 'stepik_id'
    user_tag: str = 'bot:user'
    users_list_set: str = 'bot:users'
    stepik_ids_set: str = 'bot:stepik_ids'
    
    async def add_user(self, tg_user_id: int):
        """
        Adds a user to the Redis database.
        Args:
            tg_user_id (int): The unique identifier of the user to be added.
        """
        user_key = f'{self.user_tag}:{tg_user_id}'
        if await self.check_user(tg_user_id):
            return
        
        await self.redis.hset(name=user_key, mapping={self.tg_id: tg_user_id})
        await self.redis.sadd(self.users_list_set, str(tg_user_id))
    
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
    
    async def get_users(self) -> list[int]:
        """
        Returns a list of all users in the Redis database.
        Returns:
            list[int]: A list of unique user identifiers.
        """
        users = await self.redis.smembers(self.users_list_set)
        return [int(user) for user in users]
    
    async def add_stepik_id(self, tg_user_id: int, user_stepik_id: int) -> None:
        """
        Adds a Stepik ID to a user's hash.
        Args:
            tg_user_id (int): The unique identifier of the Telegram user.
            user_stepik_id (int): The Stepik ID to be added.
        """
        if not await self.check_user(tg_user_id):
            await self.add_user(tg_user_id)
        await self.redis.hset(
            f'{self.user_tag}:{tg_user_id}', self.stepik_id, str(user_stepik_id))
        await self.redis.sadd(self.stepik_ids_set, str(user_stepik_id))
    
    async def remove_stepik_id(self, tg_user_id: int) -> None:
        """
        Removes the Stepik ID associated with a Telegram user from Redis.
        This method deletes the Stepik ID from the user's hash and removes it
        from the global set of Stepik IDs.
        
        Args:
            tg_user_id (int): The unique identifier of the Telegram user.
        """
        user_stepik_id = await self.redis.hget(
            f'{self.user_tag}:{tg_user_id}', self.stepik_id)
        
        if user_stepik_id is None:
            return
        
        pipe = self.redis.pipeline(transaction=True)
        await pipe.hdel(f'{self.user_tag}:{tg_user_id}', self.stepik_id)
        await pipe.srem(self.stepik_ids_set, str(user_stepik_id))
        await pipe.execute()
    
    async def get_stepik_ids(self) -> list[int]:
        """
        Returns a list of all Stepik IDs in the Redis database.
        Returns:
            list[int]: A list of unique Stepik IDs.
        """
        stepik_ids = await self.redis.smembers(self.stepik_ids_set)
        return [int(stepik_id) for stepik_id in stepik_ids]
