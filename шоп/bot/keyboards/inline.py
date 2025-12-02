from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import Bot, Session


# ============ ГЛАВНОЕ МЕНЮ ============

def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню пользователя"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 Товары", callback_data="catalog")
    )
    builder.row(
        InlineKeyboardButton(text="💳 Пополнение", callback_data="deposit")
    )
    builder.row(
        InlineKeyboardButton(text="❓ FAQ", callback_data="faq"),
        InlineKeyboardButton(text="💬 Поддержка", callback_data="support")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
    )
    return builder.as_markup()


def profile_kb() -> InlineKeyboardMarkup:
    """Клавиатура профиля"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="deposit")
    )
    builder.row(
        InlineKeyboardButton(text="📥 История пополнений", callback_data="deposit_history"),
        InlineKeyboardButton(text="📦 История заказов", callback_data="order_history")
    )
    builder.row(
        InlineKeyboardButton(text="« Главное меню", callback_data="start")
    )
    return builder.as_markup()


def deposit_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора способа пополнения"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🤖 CryptoBot", callback_data="deposit:cryptobot")
    )
    builder.row(
        InlineKeyboardButton(text="💎 Lolz", callback_data="deposit:lolz")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="start")
    )
    return builder.as_markup()


def deposit_amount_kb(method: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора суммы пополнения"""
    builder = InlineKeyboardBuilder()
    amounts = [5, 10, 25, 50, 100]
    for i in range(0, len(amounts), 3):
        row = amounts[i:i+3]
        builder.row(*[
            InlineKeyboardButton(text=f"💵 {amt} USDT", callback_data=f"deposit_amount:{method}:{amt}")
            for amt in row
        ])
    builder.row(
        InlineKeyboardButton(text="✏️ Своя сумма", callback_data=f"deposit_custom:{method}")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="deposit")
    )
    return builder.as_markup()


def check_deposit_kb(method: str, invoice_id: str, pay_url: str = None) -> InlineKeyboardMarkup:
    """Клавиатура проверки оплаты пополнения"""
    builder = InlineKeyboardBuilder()
    if pay_url:
        builder.row(
            InlineKeyboardButton(text="💳 Оплатить", url=pay_url)
        )
    builder.row(
        InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_deposit:{method}:{invoice_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="deposit")
    )
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    """Меню администратора"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить бота", callback_data="admin:add_bot")
    )
    builder.row(
        InlineKeyboardButton(text="📱 Сессии", callback_data="admin:sessions"),
        InlineKeyboardButton(text="🤖 Все боты", callback_data="admin:all_bots")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Начислить баланс", callback_data="admin:add_balance")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="start")
    )
    return builder.as_markup()


# ============ КАТАЛОГ ============

def catalog_kb(bots: list[Bot], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Каталог ботов с пагинацией"""
    builder = InlineKeyboardBuilder()

    start = page * per_page
    end = start + per_page
    page_bots = bots[start:end]

    for bot in page_bots:
        builder.row(
            InlineKeyboardButton(
                text=f"🤖 @{bot.username} — {bot.price} {bot.currency}",
                callback_data=f"bot:{bot.id}"
            )
        )

    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"catalog:{page-1}"))
    if end < len(bots):
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"catalog:{page+1}"))
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="« Главное меню", callback_data="start")
    )

    return builder.as_markup()


def bot_detail_kb(bot: Bot) -> InlineKeyboardMarkup:
    """Детали бота"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"💳 Купить за {bot.price} {bot.currency}", callback_data=f"buy:{bot.id}")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="catalog")
    )
    return builder.as_markup()


def payment_kb(pay_url: str, bot_id: int, invoice_id: str) -> InlineKeyboardMarkup:
    """Клавиатура оплаты"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Оплатить", url=pay_url)
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_payment:{bot_id}:{invoice_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="catalog")
    )
    return builder.as_markup()


def payment_options_kb(bot_id: int, price: float, balance: float) -> InlineKeyboardMarkup:
    """Выбор способа оплаты"""
    builder = InlineKeyboardBuilder()

    if balance >= price:
        builder.row(
            InlineKeyboardButton(text=f"💰 Оплатить с баланса ({balance:.2f} USDT)", callback_data=f"pay_balance:{bot_id}")
        )
    else:
        builder.row(
            InlineKeyboardButton(text=f"💰 Баланс: {balance:.2f} USDT (недостаточно)", callback_data="not_enough")
        )

    builder.row(
        InlineKeyboardButton(text="💳 Оплатить через CryptoBot", callback_data=f"pay_crypto:{bot_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="catalog")
    )
    return builder.as_markup()


# ============ МОИ БОТЫ ============

def my_bots_kb(bots: list[Bot]) -> InlineKeyboardMarkup:
    """Список купленных ботов"""
    builder = InlineKeyboardBuilder()

    for bot in bots:
        builder.row(
            InlineKeyboardButton(text=f"🤖 @{bot.username}", callback_data=f"manage:{bot.id}")
        )

    builder.row(
        InlineKeyboardButton(text="« Главное меню", callback_data="start")
    )
    return builder.as_markup()


def bot_manage_kb(bot_id: int) -> InlineKeyboardMarkup:
    """Меню управления ботом"""
    builder = InlineKeyboardBuilder()

    # Первый ряд
    builder.row(
        InlineKeyboardButton(text="✏️ Имя", callback_data=f"action:{bot_id}:setname"),
        InlineKeyboardButton(text="📝 About", callback_data=f"action:{bot_id}:setabouttext")
    )
    # Второй ряд
    builder.row(
        InlineKeyboardButton(text="📄 Описание", callback_data=f"action:{bot_id}:setdescription"),
        InlineKeyboardButton(text="🖼 Фото описания", callback_data=f"action:{bot_id}:setdescriptionpic")
    )
    # Третий ряд
    builder.row(
        InlineKeyboardButton(text="👤 Аватарка", callback_data=f"action:{bot_id}:setuserpic"),
        InlineKeyboardButton(text="📋 Команды", callback_data=f"action:{bot_id}:setcommands")
    )
    # Четвёртый ряд
    builder.row(
        InlineKeyboardButton(text="🔒 Privacy Policy", callback_data=f"action:{bot_id}:setprivacypolicy")
    )

    # Настройки
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"settings:{bot_id}")
    )

    # Опасные действия
    builder.row(
        InlineKeyboardButton(text="🔑 Показать токен", callback_data=f"show_token:{bot_id}"),
        InlineKeyboardButton(text="🔄 Новый токен", callback_data=f"action:{bot_id}:revoke")
    )

    builder.row(
        InlineKeyboardButton(text="« Мои боты", callback_data="my_bots")
    )

    return builder.as_markup()


def bot_settings_kb(bot_id: int) -> InlineKeyboardMarkup:
    """Настройки бота (переключатели)"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🔗 Inline Mode", callback_data=f"toggle:{bot_id}:inline"),
        InlineKeyboardButton(text="💼 Business Mode", callback_data=f"toggle:{bot_id}:business")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Allow Groups", callback_data=f"toggle:{bot_id}:groups"),
        InlineKeyboardButton(text="🔐 Group Privacy", callback_data=f"toggle:{bot_id}:privacy")
    )
    builder.row(
        InlineKeyboardButton(text="👑 Group Admin Rights", callback_data=f"action:{bot_id}:setgroupadminrights"),
        InlineKeyboardButton(text="📢 Channel Admin Rights", callback_data=f"action:{bot_id}:setchanneladminrights")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Payments", callback_data=f"action:{bot_id}:setpayments"),
        InlineKeyboardButton(text="🌐 Domain", callback_data=f"action:{bot_id}:setdomain")
    )
    builder.row(
        InlineKeyboardButton(text="📱 Menu Button", callback_data=f"action:{bot_id}:setmenubutton"),
        InlineKeyboardButton(text="🎮 Mini App", callback_data=f"action:{bot_id}:setminiapp")
    )
    builder.row(
        InlineKeyboardButton(text="📣 Paid Broadcast", callback_data=f"action:{bot_id}:paidbroadcast")
    )

    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data=f"manage:{bot_id}")
    )

    return builder.as_markup()


def toggle_kb(bot_id: int, action: str) -> InlineKeyboardMarkup:
    """Кнопки включения/выключения"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Включить", callback_data=f"do_toggle:{bot_id}:{action}:on"),
        InlineKeyboardButton(text="❌ Выключить", callback_data=f"do_toggle:{bot_id}:{action}:off")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data=f"settings:{bot_id}")
    )
    return builder.as_markup()


def cancel_kb(callback_data: str = "start") -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=callback_data)
    )
    return builder.as_markup()


def back_kb(callback_data: str) -> InlineKeyboardMarkup:
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data=callback_data)
    )
    return builder.as_markup()


def skip_kb(bot_id: int, action: str) -> InlineKeyboardMarkup:
    """Кнопка пропустить/очистить"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Очистить", callback_data=f"clear:{bot_id}:{action}")
    )
    builder.row(
        InlineKeyboardButton(text="« Отмена", callback_data=f"manage:{bot_id}")
    )
    return builder.as_markup()


# ============ АДМИН ============

def admin_sessions_kb(sessions: list[Session]) -> InlineKeyboardMarkup:
    """Список сессий"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Добавить сессию", callback_data="admin:add_session")
    )

    for session in sessions:
        builder.row(
            InlineKeyboardButton(
                text=f"📱 {session.phone}",
                callback_data=f"admin:session:{session.id}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="admin")
    )
    return builder.as_markup()


def admin_session_detail_kb(session_id: int) -> InlineKeyboardMarkup:
    """Детали сессии"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:delete_session:{session_id}")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="admin:sessions")
    )
    return builder.as_markup()


def admin_all_bots_kb(bots: list[Bot]) -> InlineKeyboardMarkup:
    """Все боты (админ)"""
    builder = InlineKeyboardBuilder()

    for bot in bots:
        status = "✅" if not bot.is_sold else "💰"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} @{bot.username} — {bot.price} {bot.currency}",
                callback_data=f"admin:bot:{bot.id}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="admin")
    )
    return builder.as_markup()


def admin_bot_detail_kb(bot: Bot) -> InlineKeyboardMarkup:
    """Детали бота (админ)"""
    builder = InlineKeyboardBuilder()

    if not bot.is_sold:
        builder.row(
            InlineKeyboardButton(text="✏️ Изменить цену", callback_data=f"admin:edit_price:{bot.id}")
        )
        builder.row(
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:delete_bot:{bot.id}")
        )

    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="admin:all_bots")
    )
    return builder.as_markup()


def select_session_kb(sessions: list[Session], bot_id: int = None) -> InlineKeyboardMarkup:
    """Выбор сессии для бота"""
    builder = InlineKeyboardBuilder()

    for session in sessions:
        cb = f"admin:select_session:{session.id}"
        if bot_id:
            cb = f"admin:link_session:{bot_id}:{session.id}"
        builder.row(
            InlineKeyboardButton(text=f"📱 {session.phone}", callback_data=cb)
        )

    builder.row(
        InlineKeyboardButton(text="« Отмена", callback_data="admin:add_bot" if not bot_id else "admin:all_bots")
    )
    return builder.as_markup()


def confirm_kb(yes_callback: str, no_callback: str) -> InlineKeyboardMarkup:
    """Подтверждение"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=yes_callback),
        InlineKeyboardButton(text="❌ Нет", callback_data=no_callback)
    )
    return builder.as_markup()


def broadcast_photo_kb() -> InlineKeyboardMarkup:
    """Клавиатура для рассылки - добавить/пропустить фото"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏭ Пропустить фото", callback_data="broadcast:skip_photo")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin")
    )
    return builder.as_markup()


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение рассылки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Начать рассылку", callback_data="broadcast:start")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin")
    )
    return builder.as_markup()
