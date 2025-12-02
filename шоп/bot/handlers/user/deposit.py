from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.database import (
    create_deposit, get_deposit_by_invoice, update_deposit_status, add_balance
)
from bot.keyboards import deposit_kb, deposit_amount_kb, check_deposit_kb, back_kb
from bot.services.cryptobot import cryptobot_service

router = Router()


class DepositState(StatesGroup):
    amount = State()


# ============ ВЫБОР МЕТОДА ============

@router.callback_query(F.data == "deposit")
async def callback_deposit(callback: CallbackQuery, state: FSMContext):
    """Выбор способа пополнения"""
    await state.clear()

    text = (
        "💳 <b>Пополнение баланса</b>\n\n"
        "Выберите способ пополнения:"
    )

    await callback.message.edit_text(text, reply_markup=deposit_kb(), parse_mode="HTML")
    await callback.answer()


# ============ CRYPTOBOT ============

@router.callback_query(F.data == "deposit:cryptobot")
async def callback_deposit_cryptobot(callback: CallbackQuery, state: FSMContext):
    """Пополнение через CryptoBot - выбор суммы"""
    await state.clear()

    text = (
        "🤖 <b>Пополнение через CryptoBot</b>\n\n"
        "Выберите сумму или введите свою:"
    )

    await callback.message.edit_text(text, reply_markup=deposit_amount_kb("cryptobot"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("deposit_amount:cryptobot:"))
async def callback_deposit_amount_cryptobot(callback: CallbackQuery):
    """Создание счёта CryptoBot с выбранной суммой"""
    amount = float(callback.data.split(":")[2])
    user_id = callback.from_user.id

    await callback.message.edit_text("⏳ Создаю счёт...", parse_mode="HTML")

    try:
        invoice = await cryptobot_service.create_invoice(
            amount=amount,
            currency="USDT",
            description=f"Пополнение баланса {amount} USDT",
            payload=f"deposit:{user_id}",
            expires_in=3600
        )

        invoice_id = str(invoice["invoice_id"])
        pay_url = cryptobot_service.get_invoice_url(invoice)

        # Создаём запись о пополнении
        await create_deposit(
            user_id=user_id,
            amount=amount,
            method="cryptobot",
            invoice_id=invoice_id
        )

        text = (
            f"🤖 <b>Счёт создан!</b>\n\n"
            f"💵 Сумма: <b>{amount} USDT</b>\n"
            f"⏱ Срок оплаты: 1 час\n\n"
            f"Нажмите кнопку ниже для оплаты:"
        )

        await callback.message.edit_text(
            text,
            reply_markup=check_deposit_kb("cryptobot", invoice_id, pay_url),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка создания счёта: {e}",
            reply_markup=back_kb("deposit"),
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data == "deposit_custom:cryptobot")
async def callback_deposit_custom_cryptobot(callback: CallbackQuery, state: FSMContext):
    """Ввод своей суммы для CryptoBot"""
    await state.set_state(DepositState.amount)
    await state.update_data(method="cryptobot")

    text = (
        "✏️ <b>Введите сумму пополнения</b>\n\n"
        "Минимум: 1 USDT\n"
        "Пример: 15.5"
    )

    await callback.message.edit_text(text, reply_markup=back_kb("deposit:cryptobot"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("check_deposit:cryptobot:"))
async def callback_check_deposit_cryptobot(callback: CallbackQuery):
    """Проверка оплаты CryptoBot"""
    invoice_id = callback.data.split(":")[2]
    user_id = callback.from_user.id

    try:
        is_paid = await cryptobot_service.check_invoice_paid(int(invoice_id))

        if is_paid:
            # Получаем депозит и начисляем баланс
            deposit = await get_deposit_by_invoice(invoice_id)
            if deposit and deposit.status == "pending":
                await update_deposit_status(invoice_id, "paid")
                await add_balance(user_id, deposit.amount)

                await callback.message.edit_text(
                    f"✅ <b>Оплата получена!</b>\n\n"
                    f"💵 Зачислено: <b>{deposit.amount} USDT</b>\n\n"
                    f"Баланс обновлён.",
                    reply_markup=back_kb("profile"),
                    parse_mode="HTML"
                )
            else:
                await callback.answer("Этот платёж уже обработан", show_alert=True)
        else:
            await callback.answer("❌ Оплата не найдена. Попробуйте позже.", show_alert=True)

    except Exception as e:
        await callback.answer(f"Ошибка проверки: {e}", show_alert=True)


# ============ LOLZ ============

@router.callback_query(F.data == "deposit:lolz")
async def callback_deposit_lolz(callback: CallbackQuery, state: FSMContext):
    """Пополнение через Lolz - выбор суммы"""
    await state.clear()

    text = (
        "💎 <b>Пополнение через Lolz</b>\n\n"
        "Выберите сумму или введите свою:"
    )

    await callback.message.edit_text(text, reply_markup=deposit_amount_kb("lolz"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("deposit_amount:lolz:"))
async def callback_deposit_amount_lolz(callback: CallbackQuery):
    """Создание ссылки для пополнения через Lolz"""
    amount = float(callback.data.split(":")[2])
    user_id = callback.from_user.id

    # Генерируем уникальный ID для платежа
    import uuid
    invoice_id = f"lolz_{uuid.uuid4().hex[:12]}"

    # Создаём запись о пополнении
    await create_deposit(
        user_id=user_id,
        amount=amount,
        method="lolz",
        invoice_id=invoice_id
    )

    # Ссылка на маркет Lolz (заглушка - нужно настроить под ваш аккаунт)
    # Формат: https://lolz.live/market/balance/transfer?user_id=YOUR_ID&amount=AMOUNT&comment=INVOICE_ID
    lolz_url = f"https://lolz.live/market/"

    text = (
        f"💎 <b>Пополнение через Lolz</b>\n\n"
        f"💵 Сумма: <b>{amount} USDT</b>\n"
        f"🔑 Код платежа: <code>{invoice_id}</code>\n\n"
        f"<b>Инструкция:</b>\n"
        f"1. Перейдите на Lolz Market\n"
        f"2. Переведите {amount}₽ на аккаунт продавца\n"
        f"3. В комментарии укажите код: <code>{invoice_id}</code>\n"
        f"4. Нажмите «Проверить оплату»\n\n"
        f"⚠️ Курс: 1 USDT = 100 RUB (примерно)"
    )

    await callback.message.edit_text(
        text,
        reply_markup=check_deposit_kb("lolz", invoice_id, lolz_url),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "deposit_custom:lolz")
async def callback_deposit_custom_lolz(callback: CallbackQuery, state: FSMContext):
    """Ввод своей суммы для Lolz"""
    await state.set_state(DepositState.amount)
    await state.update_data(method="lolz")

    text = (
        "✏️ <b>Введите сумму пополнения</b>\n\n"
        "Минимум: 1 USDT\n"
        "Пример: 15.5"
    )

    await callback.message.edit_text(text, reply_markup=back_kb("deposit:lolz"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("check_deposit:lolz:"))
async def callback_check_deposit_lolz(callback: CallbackQuery):
    """Проверка оплаты Lolz (ручная проверка админом)"""
    invoice_id = callback.data.split(":")[2]

    deposit = await get_deposit_by_invoice(invoice_id)
    if deposit and deposit.status == "pending":
        await callback.answer(
            "⏳ Ожидает подтверждения администратором.\n"
            "Обычно это занимает до 30 минут.",
            show_alert=True
        )
    elif deposit and deposit.status == "paid":
        await callback.answer("✅ Оплата уже подтверждена!", show_alert=True)
    else:
        await callback.answer("❌ Платёж не найден", show_alert=True)


# ============ ВВОД СВОЕЙ СУММЫ ============

@router.message(DepositState.amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    """Обработка введённой суммы"""
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount < 1:
            await message.answer("❌ Минимальная сумма: 1 USDT")
            return
        if amount > 10000:
            await message.answer("❌ Максимальная сумма: 10000 USDT")
            return
    except ValueError:
        await message.answer("❌ Введите корректное число. Например: 15.5")
        return

    data = await state.get_data()
    method = data.get("method", "cryptobot")
    user_id = message.from_user.id

    await state.clear()

    if method == "cryptobot":
        await message.answer("⏳ Создаю счёт...")

        try:
            invoice = await cryptobot_service.create_invoice(
                amount=amount,
                currency="USDT",
                description=f"Пополнение баланса {amount} USDT",
                payload=f"deposit:{user_id}",
                expires_in=3600
            )

            invoice_id = str(invoice["invoice_id"])
            pay_url = cryptobot_service.get_invoice_url(invoice)

            await create_deposit(
                user_id=user_id,
                amount=amount,
                method="cryptobot",
                invoice_id=invoice_id
            )

            text = (
                f"🤖 <b>Счёт создан!</b>\n\n"
                f"💵 Сумма: <b>{amount} USDT</b>\n"
                f"⏱ Срок оплаты: 1 час\n\n"
                f"Нажмите кнопку ниже для оплаты:"
            )

            await message.answer(
                text,
                reply_markup=check_deposit_kb("cryptobot", invoice_id, pay_url),
                parse_mode="HTML"
            )
        except Exception as e:
            await message.answer(
                f"❌ Ошибка создания счёта: {e}",
                reply_markup=back_kb("deposit"),
                parse_mode="HTML"
            )
    else:
        # Lolz
        import uuid
        invoice_id = f"lolz_{uuid.uuid4().hex[:12]}"

        await create_deposit(
            user_id=user_id,
            amount=amount,
            method="lolz",
            invoice_id=invoice_id
        )

        lolz_url = f"https://lolz.live/market/"

        text = (
            f"💎 <b>Пополнение через Lolz</b>\n\n"
            f"💵 Сумма: <b>{amount} USDT</b>\n"
            f"🔑 Код платежа: <code>{invoice_id}</code>\n\n"
            f"<b>Инструкция:</b>\n"
            f"1. Перейдите на Lolz Market\n"
            f"2. Переведите сумму на аккаунт продавца\n"
            f"3. В комментарии укажите код: <code>{invoice_id}</code>\n"
            f"4. Нажмите «Проверить оплату»"
        )

        await message.answer(
            text,
            reply_markup=check_deposit_kb("lolz", invoice_id, lolz_url),
            parse_mode="HTML"
        )
