from aiogram import Router

from bot.handlers.user import get_user_router
from bot.handlers.admin import get_admin_router


def get_main_router() -> Router:
    router = Router()
    router.include_router(get_admin_router())
    router.include_router(get_user_router())
    return router
