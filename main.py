import asyncio
import logging

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from db import bot
from handlers.command_handlers import command_router
from handlers.text_handlers import text_router
import oauthServer


# Ставим сервер для доступа по URL (нужно для гуг-авторизации)
def set_oauth_server():
    oauthServer.start_flask_server()
    oauthServer.set_bot(bot)


async def main():
    set_oauth_server()

    # Запуск бота
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(command_router)
    dp.include_router(text_router)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Вырубаюсь брат")
