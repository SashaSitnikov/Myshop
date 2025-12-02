from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from bot.config import config
from bot.database import (
    get_or_create_user, get_user_balance, get_user_purchases,
    get_user_deposits, get_user_orders, get_user_total_orders
)
from bot.keyboards import main_menu_kb, admin_menu_kb, back_kb, profile_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Стартовая команда"""
    await get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    text = (
        "🤖 <b>Магазин Telegram ботов</b>\n\n"
        "Здесь вы можете приобрести готовых ботов "
        "и управлять ими напрямую через наш сервис.\n\n"
        "Выберите действие:"
    )

    kb = main_menu_kb()

    # Добавляем кнопку админ-панели если админ
    if message.from_user.id in config.ADMIN_IDS:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton

        builder = InlineKeyboardBuilder()
        builder.attach(InlineKeyboardBuilder.from_markup(kb))
        builder.row(InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin"))
        kb = builder.as_markup()

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "start")
async def callback_start(callback: CallbackQuery):
    """Возврат в главное меню"""
    text = (
        "🤖 <b>Магазин Telegram ботов</b>\n\n"
        "Здесь вы можете приобрести готовых ботов "
        "и управлять ими напрямую через наш сервис.\n\n"
        "Выберите действие:"
    )

    kb = main_menu_kb()

    if callback.from_user.id in config.ADMIN_IDS:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton

        builder = InlineKeyboardBuilder()
        builder.attach(InlineKeyboardBuilder.from_markup(kb))
        builder.row(InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin"))
        kb = builder.as_markup()

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "profile")
async def callback_profile(callback: CallbackQuery):
    """Профиль пользователя"""
    user_id = callback.from_user.id
    username = callback.from_user.username or "не указан"
    balance = await get_user_balance(user_id)
    total_orders = await get_user_total_orders(user_id)

    text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📛 Username: @{username}\n"
        f"💰 Баланс: <b>{balance:.2f} USDT</b>\n"
        f"📦 Сумма заказов: <b>{total_orders:.2f} USDT</b>"
    )

    await callback.message.edit_text(text, reply_markup=profile_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "deposit_history")
async def callback_deposit_history(callback: CallbackQuery):
    """История пополнений"""
    user_id = callback.from_user.id
    deposits = await get_user_deposits(user_id, limit=10)

    if not deposits:
        text = "📥 <b>История пополнений</b>\n\nУ вас пока нет пополнений."
    else:
        text = "📥 <b>История пополнений</b>\n<i>(последние 10)</i>\n\n"
        for dep in deposits:
            date = dep.created_at.strftime("%d.%m.%Y %H:%M")
            method = "CryptoBot" if dep.method == "cryptobot" else "Lolz"
            text += f"• <b>{dep.amount:.2f} USDT</b> — {method}\n  {date}\n"

    await callback.message.edit_text(text, reply_markup=back_kb("profile"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "order_history")
async def callback_order_history(callback: CallbackQuery):
    """История заказов"""
    user_id = callback.from_user.id
    orders = await get_user_orders(user_id, limit=10)

    if not orders:
        text = "📦 <b>История заказов</b>\n\nУ вас пока нет заказов."
    else:
        text = "📦 <b>История заказов</b>\n<i>(последние 10)</i>\n\n"
        for order in orders:
            date = order.paid_at.strftime("%d.%m.%Y %H:%M")
            bot_name = f"@{order.bot.username}" if order.bot else "Удалён"
            price = order.bot.price if order.bot else 0
            text += f"• <b>{bot_name}</b> — {price:.2f} USDT\n  {date}\n"

    await callback.message.edit_text(text, reply_markup=back_kb("profile"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "faq")
async def callback_faq(callback: CallbackQuery):
    """FAQ"""
    text = (
        "❓ <b>FAQ</b>\n\n"
        "Текст будет добавлен позже..."
    )

    await callback.message.edit_text(text, reply_markup=back_kb("start"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "support")
async def callback_support(callback: CallbackQuery):
    """Поддержка"""
    text = (
        "💬 <b>Поддержка</b>\n\n"
        "Текст будет добавлен позже..."
    )

    await callback.message.edit_text(text, reply_markup=back_kb("start"), parse_mode="HTML")
    await callback.answer()
