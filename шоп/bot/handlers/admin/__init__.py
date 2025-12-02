from aiogram import Router

from bot.handlers.admin.panel import router as panel_router


def get_admin_router() -> Router:
    router = Router()
    router.include_router(panel_router)
    return router
