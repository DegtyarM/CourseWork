from aiogram import Bot, Dispatcher
from aiogram.methods import DeleteWebhook
from aiogram.types import BotCommandScopeAllPrivateChats
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage

from database import *
from handlers import routers
from configuration import conf
from data.commands import commands
from filters import ChatTypeFilter
from middlwares import middlewares_message, middlewares_callback
from data.description import bot_name, bot_description, bot_short_description

import asyncio
from redis.asyncio import Redis

bot = Bot(token=conf.bot.token, default=DefaultBotProperties(parse_mode='markdown'))
redis = Redis(db=conf.redis.db, host=conf.redis.host, password=conf.redis.passwd,
              username=conf.redis.username, port=conf.redis.port)
dp = Dispatcher(storage=RedisStorage(redis=redis), state_ttl=conf.redis.state_ttl, data_ttl=conf.redis.data_ttl)


async def on_startup():
    try:
        await redis.ping()
        print("Connected to Redis!")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        await bot.session.close()
        quit()

    groups = {
        "gid_complaints": -1002579616238,
        "gid_med_exam": -1002635910382,
        "gid_Kashirinykh": -1002678519460,
        "gid_Tatishcheva": -1002643148337,
        "gid_Polyanka": -1002609588226,
        "gid_Korolova": -1002669962540,
        "gid_Zavodskaya": -1002676156719,
        "gid_Pobedy": -1002609502850,
        "gid_Privilegiya": -1002337044144,
        "gid_rest": -1002433146323
    }

    for group_name, group_id in groups.items():
        current_value = await redis.get(name=group_name)
        if not current_value or int(current_value) != group_id:
            await redis.set(name=group_name, value=group_id)
            print(f"Значение группы {group_id} установлено в Redis под названием '{group_name}'")
        else:
            print(f"Группа '{group_name}' уже актуальна в Redis.")

    print("Бот был успешно запущен")


async def on_shutdown():
    print("Бот упал/был успешно остановлен")
    try:
        await bot.session.close()  # Закрываем соединение с Telegram API
    except Exception as e:
        print(f"Ошибка при закрытии сессии: {e}")


async def main() -> None:
    async_engine = create_async_engine(url=conf.db.build_connection_str())
    await proceed_schemas(async_engine, BaseModel.metadata)

    await bot.set_my_name(name=bot_name)
    await bot.set_my_description(description=bot_description)
    await bot.set_my_short_description(short_description=bot_short_description)
    await bot.set_my_commands(commands=commands, scope=BotCommandScopeAllPrivateChats())
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await bot(DeleteWebhook(drop_pending_updates=True))
    dp.message.filter(ChatTypeFilter(["private"]))
    for middleware in middlewares_message:
        dp.message.middleware(middleware)
    for middleware in middlewares_callback:
        dp.callback_query.middleware(middleware)
    for router in routers:
        dp.include_router(router)
    await dp.start_polling(bot, session_maker=get_session_maker(async_engine), redis=redis)

if __name__ == "__main__":
    asyncio.run(main())
