from aiogram import types, BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.utils.chat_action import ChatActionSender

from database import User

import asyncio
from cachetools import TTLCache
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from typing import Union, Dict, Any, Callable, Awaitable


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, time_limit: int = 2):
        self.limit = TTLCache(maxsize=10000, ttl=time_limit)

    async def __call__(
            self,
            handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: Dict[str, Any]
    ):
        flag = get_flag(data, "throttle")

        if not flag:
            return await handler(event, data)

        if isinstance(event, types.Message):
            user_id = event.chat.id
            if user_id in self.limit:
                msg = await event.reply("⛔ В боте работает анти-спам система для корректной обработки запросов. "
                                        "*Пожалуйста, подождите пару секунд и повторите ввод!*")
                await asyncio.sleep(3)
                await msg.delete()
                await event.delete()
                return
            self.limit[user_id] = None

        # CallbackQuery
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
            if user_id in self.limit:
                await event.answer("⛔ Пожалуйста, не отвечайте слишком быстро - так мы лучше обрабатываем "
                                   "ваши действия!\n\n⏳ Повторите нажатие кнопки через пару секунд.", show_alert=True)
                return
            self.limit[user_id] = None
        return await handler(event, data)


class AlbumMiddleware(BaseMiddleware):
    def __init__(self, latency: Union[int, float] = 0.1):
        # Initialize latency and album_data dictionary
        self.latency = latency
        self.album_data = {}

    async def collect_album_messages(self, event: types.Message, redis):
        """
        Collect messages of the same media group.
        """
        # Check if media_group_id exists in album_data
        if event.media_group_id not in self.album_data:
            # Create a new entry for the media group
            self.album_data[event.media_group_id] = {"messages": []}

        # Append the new message to the media group
        self.album_data[event.media_group_id]["messages"].append(event)

        # Add the message ID to the global del_mes_list for deletion
        await redis.lpush(f"del_tech_{str(event.from_user.id)}", *[event.message_id])

        # Return the total number of messages in the current media group
        return len(self.album_data[event.media_group_id]["messages"])

    async def __call__(self, handler, event: types.Message, data: Dict[str, Any]) -> Any:
        """
        Main middleware logic.
        """
        redis = data["redis"]
        # If the event has no media_group_id, pass it to the handler immediately
        if not event.media_group_id:
            return await handler(event, data)

        # Collect messages of the same media group
        total_before = await self.collect_album_messages(event, redis)

        # Wait for a specified latency period
        await asyncio.sleep(self.latency)

        # Check the total number of messages after the latency
        total_after = len(self.album_data[event.media_group_id]["messages"])

        # If new messages were added during the latency, exit
        if total_before != total_after:
            return

        # Sort the album messages by message_id and add to data
        album_messages = self.album_data[event.media_group_id]["messages"]
        album_messages.sort(key=lambda x: x.message_id)
        data["album"] = album_messages

        # Remove the media group from tracking to free up memory
        del self.album_data[event.media_group_id]
        # Call the original event handler
        return await handler(event, data)


class RegisterCheck(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
            event: Union[types.Message, types.callback_query, types.BotCommand],
            data: Dict[str, Any]):
        redis = data["redis"]
        res = await redis.get(name="Active today user: " + str(event.from_user.id))
        if not res:
            session_maker: sessionmaker = data["session_maker"]
            async with session_maker() as session:
                async with session.begin():
                    user = await User.user_exists(event, session)
                    if user is not None:
                        user.upd_date = datetime.today()
                        user.username = event.from_user.username
                        user.first_name = event.from_user.first_name
                        user.last_name = event.from_user.last_name
                        await redis.set(name="Active today user: " + str(event.from_user.id), value=1 if user else 0,
                                        ex=(datetime.combine(datetime.now().date() + timedelta(days=1),
                                                             datetime.min.time()) - datetime.now()).seconds)
                    else:
                        user = User(
                            user_id=event.from_user.id,
                            username=event.from_user.username,
                            first_name=event.from_user.first_name,
                            last_name=event.from_user.last_name
                        )
                        await session.merge(user)
        return await handler(event, data)


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
            event: Union[types.Message, types.CallbackQuery],
            data: Dict[str, Any]):
        flag = get_flag(data, "database")

        if not flag:
            return await handler(event, data)
        session_maker: sessionmaker = data["session_maker"]
        # Создаем сессию и добавляем ее в data
        async with session_maker() as session:
            async with session.begin():
                data["session"] = session
                return await handler(event, data)


class RedisMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
            event: Union[types.Message, types.CallbackQuery],
            data: Dict[str, Any]):
        self.redis = data["redis"]
        return await handler(event, data)


class ChatActionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: Union[types.Message, types.callback_query, types.BotCommand],
        data: Dict[str, Any],
    ) -> Any:
        bot = data["bot"]

        chat_action = get_flag(data, "chat_action") or "typing"
        kwargs = {}
        if isinstance(chat_action, dict):
            if initial_sleep := chat_action.get("initial_sleep"):
                kwargs["initial_sleep"] = initial_sleep
            if interval := chat_action.get("interval"):
                kwargs["interval"] = interval
            if action := chat_action.get("action"):
                kwargs["action"] = action
        elif isinstance(chat_action, bool):
            kwargs["action"] = "typing"
        else:
            kwargs["action"] = chat_action
        kwargs["message_thread_id"] = (
            event.message_thread_id
            if isinstance(event, types.Message) and event.is_topic_message
            else None
        )
        async with ChatActionSender(
                bot=bot,
                chat_id=event.chat.id if isinstance(event, types.Message) else event.message.chat.id,
                **kwargs):
            return await handler(event, data)
