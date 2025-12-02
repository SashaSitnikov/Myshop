from datetime import datetime
from sqlalchemy import BigInteger, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(128))
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    purchases: Mapped[list["Purchase"]] = relationship(back_populates="user")


class Session(Base):
    """Telegram сессия для управления BotFather"""
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    session_file: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    bots: Mapped[list["Bot"]] = relationship(back_populates="session")


class Bot(Base):
    """Бот на продажу"""
    __tablename__ = "bots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    token: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USDT")
    is_sold: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id"), nullable=True)
    session: Mapped["Session | None"] = relationship(back_populates="bots")

    purchase: Mapped["Purchase | None"] = relationship(back_populates="bot", uselist=False)


class Purchase(Base):
    """Покупка бота"""
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id"), unique=True)
    invoice_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="purchases")
    bot: Mapped["Bot"] = relationship(back_populates="purchase")


class Payment(Base):
    """История платежей"""
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id"))
    invoice_id: Mapped[str] = mapped_column(String(64), unique=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Deposit(Base):
    """История пополнений баланса"""
    __tablename__ = "deposits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    amount: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(20))  # cryptobot, lolz
    invoice_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, paid, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
