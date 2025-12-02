from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.database import get_available_bots, get_bot, create_payment, get_payment_by_invoice, create_purchase, get_user_balance, add_balance
from bot.keyboards import catalog_kb, bot_detail_kb, payment_kb, back_kb, payment_options_kb
from bot.services import cryptobot_service

router = Router()


@router.callback_query(F.data == "catalog")
async def callback_catalog(callback: CallbackQuery):
    """Каталог ботов"""
    bots = await get_available_bots()

    if not bots:
        await callback.message.edit_text(
            "😔 <b>Каталог пуст</b>\n\nПока нет доступных ботов для покупки.",
            reply_markup=back_kb("start"),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = "🛒 <b>Каталог ботов</b>\n\nВыберите бота для просмотра:"

    await callback.message.edit_text(text, reply_markup=catalog_kb(bots), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("catalog:"))
async def callback_catalog_page(callback: CallbackQuery):
    """Пагинация каталога"""
    page = int(callback.data.split(":")[1])
    bots = await get_available_bots()

    text = "🛒 <b>Каталог ботов</b>\n\nВыберите бота для просмотра:"

    await callback.message.edit_text(text, reply_markup=catalog_kb(bots, page), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("bot:"))
async def callback_bot_detail(callback: CallbackQuery):
    """Детали бота"""
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)

    if not bot or bot.is_sold:
        await callback.answer("Бот уже продан или не найден", show_alert=True)
        return

    text = (
        f"🤖 <b>@{bot.username}</b>\n\n"
        f"<b>Название:</b> {bot.name}\n"
    )

    if bot.description:
        text += f"<b>Описание:</b> {bot.description}\n"

    text += f"\n💰 <b>Цена:</b> {bot.price} {bot.currency}"

    await callback.message.edit_text(text, reply_markup=bot_detail_kb(bot), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("buy:"))
async def callback_buy_bot(callback: CallbackQuery):
    """Покупка бота - выбор способа оплаты"""
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)

    if not bot or bot.is_sold:
        await callback.answer("Бот уже продан или не найден", show_alert=True)
        return

    balance = await get_user_balance(callback.from_user.id)

    text = (
        f"💳 <b>Оплата</b>\n\n"
        f"Бот: @{bot.username}\n"
        f"Сумма: {bot.price} {bot.currency}\n\n"
        f"Выберите способ оплаты:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=payment_options_kb(bot_id, bot.price, balance),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "not_enough")
async def callback_not_enough(callback: CallbackQuery):
    """Недостаточно средств"""
    await callback.answer("Недостаточно средств на балансе. Пополните баланс или оплатите через CryptoBot.", show_alert=True)


@router.callback_query(F.data.startswith("pay_balance:"))
async def callback_pay_balance(callback: CallbackQuery):
    """Оплата с баланса"""
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)

    if not bot or bot.is_sold:
        await callback.answer("Бот уже продан или не найден", show_alert=True)
        return

    balance = await get_user_balance(callback.from_user.id)

    if balance < bot.price:
        await callback.answer("Недостаточно средств на балансе!", show_alert=True)
        return

    # Списываем с баланса
    await add_balance(callback.from_user.id, -bot.price)

    # Создаём покупку
    await create_purchase(
        user_id=callback.from_user.id,
        bot_id=bot_id,
        invoice_id=f"balance_{callback.from_user.id}_{bot_id}"
    )

    text = (
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"Вы приобрели бота @{bot.username}\n"
        f"Списано с баланса: {bot.price} {bot.currency}\n\n"
        f"🔑 <b>Токен:</b>\n<code>{bot.token}</code>\n\n"
        f"Теперь вы можете управлять им в разделе «Мои боты»"
    )

    await callback.message.edit_text(text, reply_markup=back_kb("my_bots"), parse_mode="HTML")
    await callback.answer("Оплата с баланса успешна!", show_alert=True)


@router.callback_query(F.data.startswith("pay_crypto:"))
async def callback_pay_crypto(callback: CallbackQuery):
    """Оплата через CryptoBot"""
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)

    if not bot or bot.is_sold:
        await callback.answer("Бот уже продан или не найден", show_alert=True)
        return

    # Создаём счёт в CryptoBot
    try:
        invoice = await cryptobot_service.create_invoice(
            amount=bot.price,
            currency=bot.currency,
            description=f"Покупка бота @{bot.username}",
            payload=f"{callback.from_user.id}:{bot_id}",
            expires_in=3600
        )

        invoice_id = str(invoice["invoice_id"])
        pay_url = cryptobot_service.get_invoice_url(invoice)

        # Сохраняем платёж
        await create_payment(
            user_id=callback.from_user.id,
            bot_id=bot_id,
            invoice_id=invoice_id,
            amount=bot.price,
            currency=bot.currency
        )

        text = (
            f"💳 <b>Оплата через CryptoBot</b>\n\n"
            f"Бот: @{bot.username}\n"
            f"Сумма: {bot.price} {bot.currency}\n\n"
            f"Нажмите кнопку ниже для оплаты.\n"
            f"После оплаты нажмите «Проверить оплату»."
        )

        await callback.message.edit_text(
            text,
            reply_markup=payment_kb(pay_url, bot_id, invoice_id),
            parse_mode="HTML"
        )

    except Exception as e:
        await callback.answer(f"Ошибка создания счёта: {e}", show_alert=True)


@router.callback_query(F.data.startswith("check_payment:"))
async def callback_check_payment(callback: CallbackQuery):
    """Проверка оплаты"""
    parts = callback.data.split(":")
    bot_id = int(parts[1])
    invoice_id = parts[2]

    bot = await get_bot(bot_id)
    if not bot:
        await callback.answer("Бот не найден", show_alert=True)
        return

    if bot.is_sold:
        await callback.answer("Бот уже продан", show_alert=True)
        return

    try:
        is_paid = await cryptobot_service.check_invoice_paid(int(invoice_id))

        if is_paid:
            # Создаём покупку
            from bot.database import update_payment_status
            await update_payment_status(invoice_id, "paid")
            await create_purchase(
                user_id=callback.from_user.id,
                bot_id=bot_id,
                invoice_id=invoice_id
            )

            text = (
                f"✅ <b>Оплата прошла успешно!</b>\n\n"
                f"Вы приобрели бота @{bot.username}\n\n"
                f"🔑 <b>Токен:</b>\n<code>{bot.token}</code>\n\n"
                f"Теперь вы можете управлять им в разделе «Мои боты»"
            )

            await callback.message.edit_text(text, reply_markup=back_kb("my_bots"), parse_mode="HTML")
            await callback.answer("Оплата подтверждена!", show_alert=True)
        else:
            await callback.answer("Оплата ещё не получена. Попробуйте позже.", show_alert=True)

    except Exception as e:
        await callback.answer(f"Ошибка проверки: {e}", show_alert=True)
