from aiogram import Router

from src.handlers.midlleware.auth import AuthMiddleware

router = Router()

router.message.middleware(AuthMiddleware())
