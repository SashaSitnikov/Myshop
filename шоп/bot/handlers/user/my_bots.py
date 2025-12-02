import os
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.database import get_user_bots, get_bot_with_session
from bot.keyboards import (
    my_bots_kb, bot_manage_kb, bot_settings_kb, toggle_kb,
    back_kb, skip_kb
)
from bot.services import botfather_service

router = Router()


class BotAction(StatesGroup):
    waiting_value = State()
    waiting_photo = State()


# ============ СПИСОК БОТОВ ============

@router.callback_query(F.data == "my_bots")
async def callback_my_bots(callback: CallbackQuery, state: FSMContext):
    """Мои боты"""
    await state.clear()

    bots = await get_user_bots(callback.from_user.id)

    if not bots:
        await callback.message.edit_text(
            "😔 <b>У вас нет ботов</b>\n\nПриобретите бота в каталоге!",
            reply_markup=back_kb("start"),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = "🤖 <b>Ваши боты</b>\n\nВыберите бота для управления:"

    await callback.message.edit_text(text, reply_markup=my_bots_kb(bots), parse_mode="HTML")
    await callback.answer()


# ============ УПРАВЛЕНИЕ БОТОМ ============

@router.callback_query(F.data.startswith("manage:"))
async def callback_manage_bot(callback: CallbackQuery, state: FSMContext):
    """Меню управления ботом"""
    await state.clear()

    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot_with_session(bot_id)

    if not bot:
        await callback.answer("Бот не найден", show_alert=True)
        return

    session_status = "✅ Подключена" if bot.session else "❌ Не подключена"

    text = (
        f"🤖 <b>@{bot.username}</b>\n\n"
        f"<b>Имя:</b> {bot.name}\n"
        f"<b>Сессия:</b> {session_status}\n\n"
        "Выберите действие для редактирования:"
    )

    await callback.message.edit_text(text, reply_markup=bot_manage_kb(bot_id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("settings:"))
async def callback_bot_settings(callback: CallbackQuery):
    """Настройки бота"""
    bot_id = int(callback.data.split(":")[1])

    text = "⚙️ <b>Настройки бота</b>\n\nВыберите параметр:"

    await callback.message.edit_text(text, reply_markup=bot_settings_kb(bot_id), parse_mode="HTML")
    await callback.answer()


# ============ ПОКАЗАТЬ ТОКЕН ============

@router.callback_query(F.data.startswith("show_token:"))
async def callback_show_token(callback: CallbackQuery):
    """Показать токен"""
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot_with_session(bot_id)

    if not bot:
        await callback.answer("Бот не найден", show_alert=True)
        return

    text = (
        f"🔑 <b>Токен бота @{bot.username}</b>\n\n"
        f"<code>{bot.token}</code>\n\n"
        "⚠️ Не передавайте токен третьим лицам!"
    )

    await callback.message.edit_text(text, reply_markup=back_kb(f"manage:{bot_id}"), parse_mode="HTML")
    await callback.answer()


# ============ TOGGLE ACTIONS ============

@router.callback_query(F.data.startswith("toggle:"))
async def callback_toggle(callback: CallbackQuery):
    """Переключатель настроек"""
    parts = callback.data.split(":")
    bot_id = int(parts[1])
    action = parts[2]

    action_names = {
        "inline": "Inline Mode",
        "business": "Business Mode",
        "groups": "Allow Groups",
        "privacy": "Group Privacy"
    }

    name = action_names.get(action, action)
    text = f"⚙️ <b>{name}</b>\n\nВыберите действие:"

    await callback.message.edit_text(text, reply_markup=toggle_kb(bot_id, action), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("do_toggle:"))
async def callback_do_toggle(callback: CallbackQuery):
    """Выполнить toggle"""
    parts = callback.data.split(":")
    bot_id = int(parts[1])
    action = parts[2]
    value = parts[3] == "on"

    bot = await get_bot_with_session(bot_id)
    if not bot or not bot.session:
        await callback.answer("Сессия не подключена!", show_alert=True)
        return

    await callback.answer("Выполняю...", show_alert=False)

    action_map = {
        "inline": botfather_service.set_inline,
        "groups": botfather_service.set_join_groups,
        "privacy": botfather_service.set_privacy,
    }

    func = action_map.get(action)
    if func:
        success, result = await func(bot.session.session_file, bot.username, value)
        if success:
            await callback.answer("✅ Готово!", show_alert=True)
        else:
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True)
    else:
        await callback.answer("Действие не поддерживается", show_alert=True)

    # Возвращаемся к настройкам
    await callback_bot_settings(callback)


# ============ TEXT/PHOTO ACTIONS ============

@router.callback_query(F.data.startswith("action:"))
async def callback_action(callback: CallbackQuery, state: FSMContext):
    """Действие требующее ввода"""
    parts = callback.data.split(":")
    bot_id = int(parts[1])
    action = parts[2]

    bot = await get_bot_with_session(bot_id)
    if not bot:
        await callback.answer("Бот не найден", show_alert=True)
        return

    if not bot.session:
        await callback.answer("Сессия не подключена! Обратитесь к админу.", show_alert=True)
        return

    # Действия с фото
    photo_actions = ["setuserpic", "setdescriptionpic"]

    action_prompts = {
        "setname": "✏️ Введите новое имя бота (до 64 символов):",
        "setabouttext": "📝 Введите новый About текст (до 120 символов):",
        "setdescription": "📄 Введите новое описание (до 512 символов):",
        "setuserpic": "👤 Отправьте новое фото для аватарки:",
        "setdescriptionpic": "🖼 Отправьте фото для описания:",
        "setcommands": "📋 Введите команды в формате:\ncommand1 - описание 1\ncommand2 - описание 2",
        "setprivacypolicy": "🔒 Введите URL Privacy Policy:",
        "setdomain": "🌐 Введите домен:",
        "setmenubutton": "📱 Введите URL для Menu Button (или /empty для удаления):",
        "revoke": "🔄 Будет создан новый токен. Текущий перестанет работать!",
    }

    prompt = action_prompts.get(action, "Введите значение:")

    if action == "revoke":
        # Сразу выполняем
        await callback.answer("Генерирую новый токен...", show_alert=False)
        success, new_token = await botfather_service.revoke_token(bot.session.session_file, bot.username)

        if success and ":" in new_token:
            # Обновляем токен в БД
            from bot.database.db import async_session
            from sqlalchemy import update
            from bot.database.models import Bot as BotModel

            async with async_session() as session:
                await session.execute(
                    update(BotModel).where(BotModel.id == bot_id).values(token=new_token)
                )
                await session.commit()

            text = f"✅ <b>Новый токен:</b>\n\n<code>{new_token}</code>"
        else:
            text = f"❌ Ошибка: {new_token}"

        await callback.message.edit_text(text, reply_markup=back_kb(f"manage:{bot_id}"), parse_mode="HTML")
        return

    await state.set_state(BotAction.waiting_photo if action in photo_actions else BotAction.waiting_value)
    await state.update_data(bot_id=bot_id, action=action)

    await callback.message.edit_text(
        prompt,
        reply_markup=skip_kb(bot_id, action),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("clear:"))
async def callback_clear_action(callback: CallbackQuery, state: FSMContext):
    """Очистить значение"""
    parts = callback.data.split(":")
    bot_id = int(parts[1])
    action = parts[2]

    bot = await get_bot_with_session(bot_id)
    if not bot or not bot.session:
        await callback.answer("Ошибка", show_alert=True)
        return

    await callback.answer("Очищаю...", show_alert=False)

    # Отправляем /empty
    success, result = await botfather_service.execute_action(
        bot.session.session_file, bot.username, action, "/empty"
    )

    await state.clear()

    if success:
        await callback.answer("✅ Очищено!", show_alert=True)
    else:
        await callback.answer(f"❌ Ошибка: {result}", show_alert=True)

    # Возвращаемся
    await callback_manage_bot(callback, state)


# ============ ОБРАБОТКА ВВОДА ============

@router.message(BotAction.waiting_value)
async def process_text_value(message: Message, state: FSMContext, bot: Bot):
    """Обработка текстового значения"""
    data = await state.get_data()
    bot_id = data.get("bot_id")
    action = data.get("action")

    db_bot = await get_bot_with_session(bot_id)
    if not db_bot or not db_bot.session:
        await message.answer("❌ Ошибка: сессия не найдена")
        await state.clear()
        return

    await message.answer("⏳ Выполняю...")

    success, result = await botfather_service.execute_action(
        db_bot.session.session_file, db_bot.username, action, message.text
    )

    await state.clear()

    if success:
        text = f"✅ <b>Готово!</b>\n\n{result[:200]}"
    else:
        text = f"❌ <b>Ошибка:</b> {result}"

    from bot.keyboards import back_kb
    await message.answer(text, reply_markup=back_kb(f"manage:{bot_id}"), parse_mode="HTML")


@router.message(BotAction.waiting_photo, F.photo)
async def process_photo_value(message: Message, state: FSMContext, bot: Bot):
    """Обработка фото"""
    data = await state.get_data()
    bot_id = data.get("bot_id")
    action = data.get("action")

    db_bot = await get_bot_with_session(bot_id)
    if not db_bot or not db_bot.session:
        await message.answer("❌ Ошибка: сессия не найдена")
        await state.clear()
        return

    await message.answer("⏳ Загружаю фото...")

    # Скачиваем фото
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)

    temp_path = f"temp_{message.from_user.id}_{photo.file_id}.jpg"
    await bot.download_file(file.file_path, temp_path)

    try:
        success, result = await botfather_service.execute_action(
            db_bot.session.session_file, db_bot.username, action, photo_path=temp_path
        )

        if success:
            text = "✅ <b>Фото обновлено!</b>"
        else:
            text = f"❌ <b>Ошибка:</b> {result}"
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.remove(temp_path)

    await state.clear()

    from bot.keyboards import back_kb
    await message.answer(text, reply_markup=back_kb(f"manage:{bot_id}"), parse_mode="HTML")


@router.message(BotAction.waiting_photo)
async def process_photo_invalid(message: Message):
    """Неверный формат - ожидали фото"""
    await message.answer("❌ Пожалуйста, отправьте фото")
