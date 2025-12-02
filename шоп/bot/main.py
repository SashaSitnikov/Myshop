import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.database import init_db
from bot.handlers import get_main_router
from bot.services import session_manager


async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logging.info("Инициализация базы данных...")
    await init_db()

    # Уведомляем админов о запуске
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🚀 Бот запущен!")
        except Exception:
            pass

    logging.info("Бот успешно запущен!")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logging.info("Отключение сессий...")
    await session_manager.disconnect_all()

    # Уведомляем админов
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🔴 Бот остановлен")
        except Exception:
            pass

    logging.info("Бот остановлен")


async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout
    )

    # Проверка конфигурации
    if not config.BOT_TOKEN:
        logging.error("BOT_TOKEN не указан в .env файле!")
        return

    if not config.CRYPTOBOT_TOKEN:
        logging.warning("CRYPTOBOT_TOKEN не указан - оплата не будет работать!")

    if not config.ADMIN_IDS:
        logging.warning("ADMIN_IDS не указаны - админ-панель будет недоступна!")

    # Создание бота и диспетчера
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(get_main_router())

    # Регистрация событий
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запуск
    try:
        logging.info("Запуск бота...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
