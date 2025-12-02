from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from bot.config import config
from bot.database.models import Base, User, Session, Bot, Purchase, Payment, Deposit


engine = create_async_engine(f"sqlite+aiosqlite:///{config.DATABASE_PATH}", echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ============ USERS ============

async def get_or_create_user(user_id: int, username: str | None, full_name: str) -> User:
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            user = User(id=user_id, username=username, full_name=full_name)
            session.add(user)
            await session.commit()
        return user


async def get_user(user_id: int) -> User | None:
    async with async_session() as session:
        return await session.get(User, user_id)


async def add_balance(user_id: int, amount: float) -> User | None:
    """Начислить баланс пользователю"""
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            user.balance += amount
            await session.commit()
            await session.refresh(user)
        return user


async def set_balance(user_id: int, amount: float) -> User | None:
    """Установить баланс пользователю"""
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            user.balance = amount
            await session.commit()
            await session.refresh(user)
        return user


async def get_user_balance(user_id: int) -> float:
    """Получить баланс пользователя"""
    async with async_session() as session:
        user = await session.get(User, user_id)
        return user.balance if user else 0.0


# ============ SESSIONS ============

async def add_session(phone: str, session_file: str) -> Session:
    async with async_session() as session:
        tg_session = Session(phone=phone, session_file=session_file)
        session.add(tg_session)
        await session.commit()
        await session.refresh(tg_session)
        return tg_session


async def get_all_sessions() -> list[Session]:
    async with async_session() as session:
        result = await session.execute(select(Session).where(Session.is_active == True))
        return list(result.scalars().all())


async def get_session(session_id: int) -> Session | None:
    async with async_session() as session:
        return await session.get(Session, session_id)


async def delete_session(session_id: int):
    async with async_session() as session:
        tg_session = await session.get(Session, session_id)
        if tg_session:
            await session.delete(tg_session)
            await session.commit()


# ============ BOTS ============

async def add_bot(username: str, token: str, name: str, price: float,
                  currency: str = "USDT", description: str = None,
                  session_id: int = None) -> Bot:
    async with async_session() as session:
        bot = Bot(
            username=username,
            token=token,
            name=name,
            price=price,
            currency=currency,
            description=description,
            session_id=session_id
        )
        session.add(bot)
        await session.commit()
        await session.refresh(bot)
        return bot


async def get_available_bots() -> list[Bot]:
    async with async_session() as session:
        result = await session.execute(
            select(Bot).where(Bot.is_sold == False).order_by(Bot.created_at.desc())
        )
        return list(result.scalars().all())


async def get_bot(bot_id: int) -> Bot | None:
    async with async_session() as session:
        result = await session.execute(
            select(Bot).where(Bot.id == bot_id)
        )
        return result.scalar_one_or_none()


async def get_bot_with_session(bot_id: int) -> Bot | None:
    async with async_session() as session:
        result = await session.execute(
            select(Bot).where(Bot.id == bot_id)
        )
        bot = result.scalar_one_or_none()
        if bot and bot.session_id:
            await session.refresh(bot, ["session"])
        return bot


async def mark_bot_sold(bot_id: int):
    async with async_session() as session:
        await session.execute(
            update(Bot).where(Bot.id == bot_id).values(is_sold=True)
        )
        await session.commit()


async def delete_bot(bot_id: int):
    async with async_session() as session:
        bot = await session.get(Bot, bot_id)
        if bot:
            await session.delete(bot)
            await session.commit()


async def get_all_bots() -> list[Bot]:
    async with async_session() as session:
        result = await session.execute(select(Bot).order_by(Bot.created_at.desc()))
        return list(result.scalars().all())


# ============ PURCHASES ============

async def create_purchase(user_id: int, bot_id: int, invoice_id: str = None) -> Purchase:
    async with async_session() as session:
        purchase = Purchase(user_id=user_id, bot_id=bot_id, invoice_id=invoice_id)
        session.add(purchase)
        await session.execute(
            update(Bot).where(Bot.id == bot_id).values(is_sold=True)
        )
        await session.commit()
        await session.refresh(purchase)
        return purchase


async def get_user_purchases(user_id: int) -> list[Purchase]:
    async with async_session() as session:
        result = await session.execute(
            select(Purchase).where(Purchase.user_id == user_id)
        )
        purchases = list(result.scalars().all())
        for p in purchases:
            await session.refresh(p, ["bot"])
        return purchases


async def get_user_bots(user_id: int) -> list[Bot]:
    async with async_session() as session:
        result = await session.execute(
            select(Bot)
            .join(Purchase)
            .where(Purchase.user_id == user_id)
        )
        bots = list(result.scalars().all())
        for bot in bots:
            if bot.session_id:
                await session.refresh(bot, ["session"])
        return bots


# ============ PAYMENTS ============

async def create_payment(user_id: int, bot_id: int, invoice_id: str,
                         amount: float, currency: str) -> Payment:
    async with async_session() as session:
        payment = Payment(
            user_id=user_id,
            bot_id=bot_id,
            invoice_id=invoice_id,
            amount=amount,
            currency=currency
        )
        session.add(payment)
        await session.commit()
        return payment


async def update_payment_status(invoice_id: str, status: str):
    async with async_session() as session:
        await session.execute(
            update(Payment).where(Payment.invoice_id == invoice_id).values(status=status)
        )
        await session.commit()


async def get_payment_by_invoice(invoice_id: str) -> Payment | None:
    async with async_session() as session:
        result = await session.execute(
            select(Payment).where(Payment.invoice_id == invoice_id)
        )
        return result.scalar_one_or_none()


# ============ DEPOSITS ============

async def create_deposit(user_id: int, amount: float, method: str, invoice_id: str = None) -> Deposit:
    """Создать запись о пополнении"""
    async with async_session() as session:
        deposit = Deposit(
            user_id=user_id,
            amount=amount,
            method=method,
            invoice_id=invoice_id
        )
        session.add(deposit)
        await session.commit()
        await session.refresh(deposit)
        return deposit


async def get_deposit_by_invoice(invoice_id: str) -> Deposit | None:
    """Получить депозит по invoice_id"""
    async with async_session() as session:
        result = await session.execute(
            select(Deposit).where(Deposit.invoice_id == invoice_id)
        )
        return result.scalar_one_or_none()


async def update_deposit_status(invoice_id: str, status: str):
    """Обновить статус депозита"""
    async with async_session() as session:
        await session.execute(
            update(Deposit).where(Deposit.invoice_id == invoice_id).values(status=status)
        )
        await session.commit()


async def get_user_deposits(user_id: int, limit: int = 10) -> list[Deposit]:
    """Получить историю пополнений пользователя"""
    async with async_session() as session:
        result = await session.execute(
            select(Deposit)
            .where(Deposit.user_id == user_id, Deposit.status == "paid")
            .order_by(Deposit.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def get_user_orders(user_id: int, limit: int = 10) -> list[Purchase]:
    """Получить историю заказов пользователя (последние N)"""
    async with async_session() as session:
        result = await session.execute(
            select(Purchase)
            .where(Purchase.user_id == user_id)
            .order_by(Purchase.paid_at.desc())
            .limit(limit)
        )
        purchases = list(result.scalars().all())
        for p in purchases:
            await session.refresh(p, ["bot"])
        return purchases


async def get_user_total_orders(user_id: int) -> float:
    """Получить общую сумму заказов пользователя"""
    async with async_session() as session:
        purchases = await session.execute(
            select(Purchase).where(Purchase.user_id == user_id)
        )
        total = 0.0
        for p in purchases.scalars().all():
            await session.refresh(p, ["bot"])
            if p.bot:
                total += p.bot.price
        return total


async def get_all_users() -> list[User]:
    """Получить всех пользователей"""
    async with async_session() as session:
        result = await session.execute(select(User))
        return list(result.scalars().all())
