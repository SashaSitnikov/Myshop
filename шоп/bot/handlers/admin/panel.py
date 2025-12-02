from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Filter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import config
from bot.database import (
    get_all_sessions, get_session, delete_session, add_session,
    get_all_bots, get_bot, delete_bot, add_bot,
    add_balance, get_user, get_user_balance, get_all_users
)
from bot.keyboards import (
    admin_menu_kb, admin_sessions_kb, admin_session_detail_kb,
    admin_all_bots_kb, admin_bot_detail_kb, select_session_kb,
    back_kb, confirm_kb, cancel_kb, broadcast_photo_kb, broadcast_confirm_kb
)
from bot.services import session_manager

router = Router()


class AdminFilter(Filter):
    async def __call__(self, event) -> bool:
        user_id = event.from_user.id if hasattr(event, 'from_user') else None
        return user_id in config.ADMIN_IDS


class AddSession(StatesGroup):
    phone = State()
    code = State()
    password = State()


class AddBot(StatesGroup):
    username = State()
    token = State()
    name = State()
    price = State()
    session = State()


class AddBalance(StatesGroup):
    user_id = State()
    amount = State()


class Broadcast(StatesGroup):
    message = State()
    photo = State()
    confirm = State()


# Применяем фильтр ко всем хендлерам
router.callback_query.filter(AdminFilter())
router.message.filter(AdminFilter())


# ============ АДМИН МЕНЮ ============

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Команда /admin"""
    await state.clear()

    sessions = await get_all_sessions()
    bots = await get_all_bots()
    sold = sum(1 for b in bots if b.is_sold)

    text = (
        "⚙️ <b>Админ-панель</b>\n\n"
        f"📱 Сессий: {len(sessions)}\n"
        f"🤖 Ботов: {len(bots)} (продано: {sold})\n\n"
        "Выберите действие:"
    )

    await message.answer(text, reply_markup=admin_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin")
async def callback_admin(callback: CallbackQuery, state: FSMContext):
    """Админ панель"""
    await state.clear()

    sessions = await get_all_sessions()
    bots = await get_all_bots()
    sold = sum(1 for b in bots if b.is_sold)

    text = (
        "⚙️ <b>Админ-панель</b>\n\n"
        f"📱 Сессий: {len(sessions)}\n"
        f"🤖 Ботов: {len(bots)} (продано: {sold})\n\n"
        "Выберите действие:"
    )

    await callback.message.edit_text(text, reply_markup=admin_menu_kb(), parse_mode="HTML")
    await callback.answer()


# ============ СТАТИСТИКА ============

@router.callback_query(F.data == "admin:stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Статистика"""
    from bot.database.db import async_session
    from sqlalchemy import select, func
    from bot.database.models import User, Purchase, Bot
    from datetime import datetime, timedelta

    async with async_session() as session:
        # Кол-во пользователей
        users_count = await session.scalar(select(func.count(User.id)))

        # Покупки за всё время
        purchases_all = await session.execute(select(Purchase))
        purchases_list = list(purchases_all.scalars().all())

        # Продажи за сегодня
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        purchases_today = await session.execute(
            select(Purchase).where(Purchase.paid_at >= today)
        )
        purchases_today_list = list(purchases_today.scalars().all())

        # Считаем сумму продаж
        total_revenue = 0.0
        for p in purchases_list:
            await session.refresh(p, ["bot"])
            if p.bot:
                total_revenue += p.bot.price

        today_revenue = 0.0
        for p in purchases_today_list:
            await session.refresh(p, ["bot"])
            if p.bot:
                today_revenue += p.bot.price

    text = (
        "📊 <b>Статистика магазина</b>\n\n"
        f"👥 Пользователей: {users_count}\n\n"
        f"<b>Продажи за всё время:</b>\n"
        f"📦 Заказов: {len(purchases_list)}\n"
        f"💵 Сумма: {total_revenue:.2f} USDT\n\n"
        f"<b>Продажи за сегодня:</b>\n"
        f"📦 Заказов: {len(purchases_today_list)}\n"
        f"💵 Сумма: {today_revenue:.2f} USDT"
    )

    await callback.message.edit_text(text, reply_markup=back_kb("admin"), parse_mode="HTML")
    await callback.answer()


# ============ СЕССИИ ============

@router.callback_query(F.data == "admin:sessions")
async def callback_admin_sessions(callback: CallbackQuery, state: FSMContext):
    """Список сессий"""
    await state.clear()
    sessions = await get_all_sessions()

    text = "📱 <b>Telegram сессии</b>\n\nСессии используются для управления ботами через BotFather."

    await callback.message.edit_text(text, reply_markup=admin_sessions_kb(sessions), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:session:"))
async def callback_session_detail(callback: CallbackQuery):
    """Детали сессии"""
    session_id = int(callback.data.split(":")[2])
    session = await get_session(session_id)

    if not session:
        await callback.answer("Сессия не найдена", show_alert=True)
        return

    # Проверяем активность
    client = await session_manager.load_session(session.session_file)
    status = "✅ Активна" if client else "❌ Неактивна"
    if client:
        await client.disconnect()

    text = (
        f"📱 <b>Сессия</b>\n\n"
        f"<b>Телефон:</b> {session.phone}\n"
        f"<b>Статус:</b> {status}\n"
        f"<b>Файл:</b> <code>{session.session_file}</code>"
    )

    await callback.message.edit_text(text, reply_markup=admin_session_detail_kb(session_id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete_session:"))
async def callback_delete_session(callback: CallbackQuery):
    """Удаление сессии"""
    session_id = int(callback.data.split(":")[2])
    await delete_session(session_id)
    await callback.answer("✅ Сессия удалена", show_alert=True)

    # Возврат к списку
    sessions = await get_all_sessions()
    text = "📱 <b>Telegram сессии</b>"
    await callback.message.edit_text(text, reply_markup=admin_sessions_kb(sessions), parse_mode="HTML")


# ============ ДОБАВЛЕНИЕ СЕССИИ ============

@router.callback_query(F.data == "admin:add_session")
async def callback_add_session(callback: CallbackQuery, state: FSMContext):
    """Начать добавление сессии"""
    await state.set_state(AddSession.phone)

    text = (
        "📱 <b>Добавление сессии</b>\n\n"
        "Введите номер телефона в международном формате:\n"
        "Например: +79001234567"
    )

    await callback.message.edit_text(text, reply_markup=cancel_kb("admin:sessions"), parse_mode="HTML")
    await callback.answer()


@router.message(AddSession.phone)
async def process_session_phone(message: Message, state: FSMContext):
    """Получение номера телефона"""
    phone = message.text.strip()

    if not phone.startswith("+"):
        phone = "+" + phone

    await message.answer("⏳ Отправляю код подтверждения...")

    try:
        client, phone_code_hash = await session_manager.send_code(phone)
        await state.update_data(phone=phone, phone_code_hash=phone_code_hash)
        await state.set_state(AddSession.code)

        await message.answer(
            f"✅ Код отправлен на {phone}\n\nВведите код из Telegram:",
            reply_markup=cancel_kb("admin:sessions")
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=back_kb("admin:sessions"))
        await state.clear()


@router.message(AddSession.code)
async def process_session_code(message: Message, state: FSMContext):
    """Получение кода подтверждения"""
    code = message.text.strip().replace(" ", "").replace("-", "")
    data = await state.get_data()

    phone = data["phone"]
    phone_code_hash = data["phone_code_hash"]

    success, result = await session_manager.sign_in(phone, code, phone_code_hash)

    if result == "NEED_2FA":
        await state.set_state(AddSession.password)
        await message.answer(
            "🔐 Требуется пароль двухфакторной аутентификации.\n\nВведите пароль:",
            reply_markup=cancel_kb("admin:sessions")
        )
        return

    if success:
        # Сохраняем в БД
        await add_session(phone, result)
        await message.answer(
            f"✅ Сессия успешно добавлена!\n\nФайл: <code>{result}</code>",
            reply_markup=back_kb("admin:sessions"),
            parse_mode="HTML"
        )
        await state.clear()
    else:
        await message.answer(f"❌ Ошибка: {result}", reply_markup=back_kb("admin:sessions"))
        await state.clear()


@router.message(AddSession.password)
async def process_session_password(message: Message, state: FSMContext):
    """Получение пароля 2FA"""
    password = message.text.strip()
    data = await state.get_data()
    phone = data["phone"]

    success, result = await session_manager.sign_in_2fa(phone, password)

    if success:
        await add_session(phone, result)
        await message.answer(
            f"✅ Сессия успешно добавлена!\n\nФайл: <code>{result}</code>",
            reply_markup=back_kb("admin:sessions"),
            parse_mode="HTML"
        )
    else:
        await message.answer(f"❌ Ошибка: {result}", reply_markup=back_kb("admin:sessions"))

    await state.clear()


# ============ БОТЫ ============

@router.callback_query(F.data == "admin:all_bots")
async def callback_admin_bots(callback: CallbackQuery, state: FSMContext):
    """Все боты"""
    await state.clear()
    bots = await get_all_bots()

    text = "🤖 <b>Все боты</b>\n\n✅ — доступен, 💰 — продан"

    await callback.message.edit_text(text, reply_markup=admin_all_bots_kb(bots), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:bot:"))
async def callback_admin_bot_detail(callback: CallbackQuery):
    """Детали бота (админ)"""
    bot_id = int(callback.data.split(":")[2])
    bot = await get_bot(bot_id)

    if not bot:
        await callback.answer("Бот не найден", show_alert=True)
        return

    status = "💰 Продан" if bot.is_sold else "✅ Доступен"
    session_info = f"📱 Сессия ID: {bot.session_id}" if bot.session_id else "❌ Сессия не привязана"

    text = (
        f"🤖 <b>@{bot.username}</b>\n\n"
        f"<b>Имя:</b> {bot.name}\n"
        f"<b>Цена:</b> {bot.price} {bot.currency}\n"
        f"<b>Статус:</b> {status}\n"
        f"<b>Сессия:</b> {session_info}\n\n"
        f"<b>Токен:</b>\n<code>{bot.token}</code>"
    )

    await callback.message.edit_text(text, reply_markup=admin_bot_detail_kb(bot), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete_bot:"))
async def callback_admin_delete_bot(callback: CallbackQuery):
    """Удаление бота"""
    bot_id = int(callback.data.split(":")[2])
    await delete_bot(bot_id)
    await callback.answer("✅ Бот удалён", show_alert=True)

    bots = await get_all_bots()
    text = "🤖 <b>Все боты</b>"
    await callback.message.edit_text(text, reply_markup=admin_all_bots_kb(bots), parse_mode="HTML")


# ============ ДОБАВЛЕНИЕ БОТА ============

@router.callback_query(F.data == "admin:add_bot")
async def callback_add_bot(callback: CallbackQuery, state: FSMContext):
    """Начать добавление бота"""
    await state.set_state(AddBot.username)

    text = (
        "🤖 <b>Добавление бота</b>\n\n"
        "Введите username бота (без @):\n"
        "Например: my_cool_bot"
    )

    await callback.message.edit_text(text, reply_markup=cancel_kb("admin"), parse_mode="HTML")
    await callback.answer()


@router.message(AddBot.username)
async def process_bot_username(message: Message, state: FSMContext):
    """Username бота"""
    username = message.text.strip().replace("@", "")
    await state.update_data(username=username)
    await state.set_state(AddBot.token)

    await message.answer(
        "🔑 Введите токен бота:",
        reply_markup=cancel_kb("admin")
    )


@router.message(AddBot.token)
async def process_bot_token(message: Message, state: FSMContext):
    """Токен бота"""
    token = message.text.strip()

    # Простая валидация токена
    if ":" not in token:
        await message.answer("❌ Неверный формат токена. Попробуйте снова:")
        return

    await state.update_data(token=token)
    await state.set_state(AddBot.name)

    await message.answer(
        "📝 Введите название бота (для каталога):",
        reply_markup=cancel_kb("admin")
    )


@router.message(AddBot.name)
async def process_bot_name(message: Message, state: FSMContext):
    """Название бота"""
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(AddBot.price)

    await message.answer(
        "💰 Введите цену в USDT:",
        reply_markup=cancel_kb("admin")
    )


@router.message(AddBot.price)
async def process_bot_price(message: Message, state: FSMContext):
    """Цена бота"""
    try:
        price = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer("❌ Введите число. Например: 10 или 10.5")
        return

    await state.update_data(price=price)
    await state.set_state(AddBot.session)

    # Показываем выбор сессии
    sessions = await get_all_sessions()

    if sessions:
        text = "📱 Выберите сессию для управления ботом:"
        kb = select_session_kb(sessions)
    else:
        text = "⚠️ Нет доступных сессий. Сначала добавьте сессию.\n\nБот будет добавлен без привязки к сессии."
        kb = confirm_kb("admin:save_bot_no_session", "admin")

    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("admin:select_session:"))
async def callback_select_session_for_bot(callback: CallbackQuery, state: FSMContext):
    """Выбор сессии для бота"""
    session_id = int(callback.data.split(":")[2])
    data = await state.get_data()

    # Сохраняем бота
    bot = await add_bot(
        username=data["username"],
        token=data["token"],
        name=data["name"],
        price=data["price"],
        session_id=session_id
    )

    await state.clear()

    text = (
        f"✅ <b>Бот добавлен!</b>\n\n"
        f"@{bot.username}\n"
        f"Цена: {bot.price} USDT\n"
        f"Сессия: #{session_id}"
    )

    await callback.message.edit_text(text, reply_markup=back_kb("admin:all_bots"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:save_bot_no_session")
async def callback_save_bot_no_session(callback: CallbackQuery, state: FSMContext):
    """Сохранить бота без сессии"""
    data = await state.get_data()

    bot = await add_bot(
        username=data["username"],
        token=data["token"],
        name=data["name"],
        price=data["price"]
    )

    await state.clear()

    text = (
        f"✅ <b>Бот добавлен!</b>\n\n"
        f"@{bot.username}\n"
        f"Цена: {bot.price} USDT\n"
        f"⚠️ Сессия не привязана"
    )

    await callback.message.edit_text(text, reply_markup=back_kb("admin:all_bots"), parse_mode="HTML")
    await callback.answer()
# ============ НАЧИСЛЕНИЕ БАЛАНСА ============

@router.callback_query(F.data == "admin:add_balance")
async def callback_add_balance(callback: CallbackQuery, state: FSMContext):
    """Начать начисление баланса"""
    await state.set_state(AddBalance.user_id)

    text = (
        "💰 <b>Начисление баланса</b>\n\n"
        "Введите Telegram ID пользователя:\n"
        "(можно узнать у @userinfobot)"
    )

    await callback.message.edit_text(text, reply_markup=cancel_kb("admin"), parse_mode="HTML")
    await callback.answer()


@router.message(AddBalance.user_id)
async def process_balance_user_id(message: Message, state: FSMContext):
    """Получение ID пользователя"""
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректный ID (число)")
        return

    user = await get_user(user_id)
    if not user:
        await message.answer(
            f"❌ Пользователь с ID {user_id} не найден в базе.\n"
            "Он должен сначала написать /start боту.",
            reply_markup=back_kb("admin")
        )
        await state.clear()
        return

    current_balance = await get_user_balance(user_id)
    await state.update_data(user_id=user_id, username=user.username, current_balance=current_balance)
    await state.set_state(AddBalance.amount)

    text = (
        f"👤 <b>Пользователь найден</b>\n\n"
        f"ID: <code>{user_id}</code>\n"
        f"Username: @{user.username or 'нет'}\n"
        f"Имя: {user.full_name}\n"
        f"Текущий баланс: {current_balance:.2f} USDT\n\n"
        "Введите сумму для начисления:"
    )

    await message.answer(text, reply_markup=cancel_kb("admin"), parse_mode="HTML")


@router.message(AddBalance.amount)
async def process_balance_amount(message: Message, state: FSMContext):
    """Получение суммы"""
    try:
        amount = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer("❌ Введите число. Например: 10 или 10.5")
        return

    data = await state.get_data()
    user_id = data["user_id"]
    username = data.get("username")
    old_balance = data["current_balance"]

    user = await add_balance(user_id, amount)
    new_balance = user.balance if user else old_balance + amount

    await state.clear()

    text = (
        f"✅ <b>Баланс начислен!</b>\n\n"
        f"👤 Пользователь: @{username or user_id}\n"
        f"💵 Начислено: {amount:+.2f} USDT\n"
        f"📊 Было: {old_balance:.2f} USDT\n"
        f"📊 Стало: {new_balance:.2f} USDT"
    )

    await message.answer(text, reply_markup=back_kb("admin"), parse_mode="HTML")


# ============ РАССЫЛКА ============

@router.callback_query(F.data == "admin:broadcast")
async def callback_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начать рассылку"""
    await state.set_state(Broadcast.message)

    text = (
        "📢 <b>Рассылка</b>\n\n"
        "Введите текст сообщения для рассылки.\n"
        "Поддерживается HTML разметка."
    )

    await callback.message.edit_text(text, reply_markup=cancel_kb("admin"), parse_mode="HTML")
    await callback.answer()


@router.message(Broadcast.message)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Получение текста рассылки"""
    await state.update_data(message_text=message.text, message_entities=message.entities)
    await state.set_state(Broadcast.photo)

    text = (
        "📷 <b>Добавить фото?</b>\n\n"
        "Отправьте фото для рассылки или нажмите «Пропустить»."
    )

    await message.answer(text, reply_markup=broadcast_photo_kb(), parse_mode="HTML")


@router.message(Broadcast.photo, F.photo)
async def process_broadcast_photo(message: Message, state: FSMContext):
    """Получение фото для рассылки"""
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)

    data = await state.get_data()
    text = data.get("message_text", "")

    users = await get_all_users()
    await state.update_data(users_count=len(users))

    preview_text = (
        "📢 <b>Предпросмотр рассылки</b>\n\n"
        f"<b>Текст:</b>\n{text[:500]}{'...' if len(text) > 500 else ''}\n\n"
        f"📷 Фото: прикреплено\n"
        f"👥 Получателей: {len(users)}\n\n"
        "Начать рассылку?"
    )

    await message.answer(preview_text, reply_markup=broadcast_confirm_kb(), parse_mode="HTML")


@router.callback_query(F.data == "broadcast:skip_photo", Broadcast.photo)
async def callback_skip_photo(callback: CallbackQuery, state: FSMContext):
    """Пропустить добавление фото"""
    await state.update_data(photo_id=None)

    data = await state.get_data()
    text = data.get("message_text", "")

    users = await get_all_users()
    await state.update_data(users_count=len(users))

    preview_text = (
        "📢 <b>Предпросмотр рассылки</b>\n\n"
        f"<b>Текст:</b>\n{text[:500]}{'...' if len(text) > 500 else ''}\n\n"
        f"📷 Фото: нет\n"
        f"👥 Получателей: {len(users)}\n\n"
        "Начать рассылку?"
    )

    await callback.message.edit_text(preview_text, reply_markup=broadcast_confirm_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "broadcast:start")
async def callback_start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Запуск рассылки"""
    data = await state.get_data()
    message_text = data.get("message_text", "")
    photo_id = data.get("photo_id")

    await state.clear()

    await callback.message.edit_text("⏳ Рассылка началась...", parse_mode="HTML")

    users = await get_all_users()
    success = 0
    failed = 0

    from aiogram import Bot
    bot: Bot = callback.bot

    for user in users:
        try:
            if photo_id:
                await bot.send_photo(
                    chat_id=user.id,
                    photo=photo_id,
                    caption=message_text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=user.id,
                    text=message_text,
                    parse_mode="HTML"
                )
            success += 1
        except Exception:
            failed += 1

        # Небольшая задержка чтобы не получить flood wait
        import asyncio
        await asyncio.sleep(0.05)

    result_text = (
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📨 Успешно: {success}\n"
        f"❌ Не доставлено: {failed}"
    )

    await callback.message.answer(result_text, reply_markup=back_kb("admin"), parse_mode="HTML")
