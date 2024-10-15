from contextlib import asynccontextmanager

import uvicorn
import asyncio
from aiogram import Dispatcher, Bot
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI
from sqlalchemy.util import await_only

from config.settings import settings
from script.init_db import init_models
from src.api.login import router
from src.bot import setup_dp, setup_bot
from src.storage.redis import setup_redis
from src.logger import set_correlation_id
from src.log_config import logging
from src.handlers.command.router import router as command_router

logger = logging.getLogger('backend_logger')


async def lifespan(app: FastAPI):
    dp = Dispatcher()
    dp.include_router(command_router)
    setup_dp(dp)
    bot = Bot(settings.BOT_TOKEN)
    setup_bot(bot)

    logger.info('Устанавливается webhook для бота...')
    try:
        await bot.set_webhook(settings.BOT_WEBHOOK_URL)
        logger.info(f'Webhook установлен на {settings.BOT_WEBHOOK_URL}')
    except Exception as e:
        logger.error(f'Ошибка при установке webhook: {e}')

    yield

    logger.info('Удаляется webhook...')
    try:
        await bot.delete_webhook()
        logger.info('Webhook удалён.')
    except Exception as e:
        logger.error(f'Ошибка при удалении webhook: {e}')


def create_app() -> FastAPI:
    correlation_id = set_correlation_id()
    app = FastAPI(docs_url='/swagger', lifespan=lifespan)
    app.include_router(router)
    logger.info(f'Приложение создано [{correlation_id}]')
    return app


async def start_polling():
    logger.info('Запуск режима polling...')
    try:
        redis = setup_redis()
        storage = RedisStorage(redis)

        dp = Dispatcher(storage=storage)
        setup_dp(dp)

        dp.include_router(command_router)

        bot = Bot(settings.BOT_TOKEN)
        setup_bot(bot)

        await bot.delete_webhook()
        await dp.start_polling(bot)
        logger.info('Polling запущен.')
    except Exception as e:
        logger.error(f'Ошибка при запуске polling: {e}')


if __name__ == '__main__':
    # asyncio.run(init_models())
    if settings.BOT_WEBHOOK_URL:
        logger.info('Запуск приложения с webhook...')
        uvicorn.run('src.app:create_app', factory=True, host='0.0.0.0', port=8000, workers=1)
    else:
        logger.info('Запуск приложения с polling...')
        asyncio.run(start_polling())
