import asyncio

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI

from config.settings import settings
from src.api.router import router
from src.bot import setup_bot, setup_dp
from src.handlers.callback.router import router as callback_router
from src.handlers.command.router import router as command_router
from src.handlers.message.router import router as message_router
from src.log_config import logging
from src.logger import set_correlation_id
from src.storage.redis import setup_redis

logger = logging.getLogger('backend_logger')


async def lifespan(app: FastAPI):
    dp = Dispatcher()
    dp.include_router(command_router)
    dp.include_router(callback_router)
    dp.include_router(message_router)
    setup_dp(dp)
    bot = Bot(settings.BOT_TOKEN)
    setup_bot(bot)

    logger.info('Устанавливается webhook для бота...')
    await bot.set_webhook(settings.BOT_WEBHOOK_URL)
    logger.info(f'Webhook установлен на {settings.BOT_WEBHOOK_URL}')

    yield

    await bot.delete_webhook()


def create_app() -> FastAPI:
    correlation_id = set_correlation_id()
    app = FastAPI(docs_url='/swagger', lifespan=lifespan)
    app.include_router(router)
    logger.info(f'Приложение создано [{correlation_id}]')
    return app


async def start_polling():
    logger.info('Запуск режима polling...')
    redis = setup_redis()
    storage = RedisStorage(redis)

    dp = Dispatcher(storage=storage)
    dp.include_router(command_router)
    dp.include_router(callback_router)
    dp.include_router(message_router)

    setup_dp(dp)
    default = DefaultBotProperties(parse_mode=ParseMode.HTML)
    bot = Bot(settings.BOT_TOKEN, default=default)
    setup_bot(bot)

    await bot.delete_webhook()
    await dp.start_polling(bot)
    logger.info('Завершение режима polling...')


if __name__ == '__main__':
    if settings.BOT_WEBHOOK_URL:
        logger.info('Запуск приложения с webhook...')
        uvicorn.run('src.app:create_app', factory=True, host='0.0.0.0', port=8000, workers=1)
    else:
        logger.info('Запуск приложения с polling...')
        asyncio.run(start_polling())
