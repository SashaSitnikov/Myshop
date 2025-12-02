from aiogram import Router

from bot.handlers.user.start import router as start_router
from bot.handlers.user.catalog import router as catalog_router
from bot.handlers.user.my_bots import router as my_bots_router
from bot.handlers.user.deposit import router as deposit_router


def get_user_router() -> Router:
    router = Router()
    router.include_router(start_router)
    router.include_router(catalog_router)
    router.include_router(my_bots_router)
    router.include_router(deposit_router)
    return router
