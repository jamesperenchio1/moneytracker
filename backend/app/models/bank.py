from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class BankName(str, enum.Enum):
    BANGKOK_BANK = "bangkok_bank"
    KASIKORN = "kasikorn"
    SCB = "scb"
    KRUNGSRI = "krungsri"
    KRUNGTHAI = "krungthai"
    TTB = "ttb"
    OTHER = "other"


class Bank(Base):
    __tablename__ = "banks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[BankName] = mapped_column(SQLEnum(BankName), nullable=False)
    country: Mapped[str] = mapped_column(String(10), default="TH")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    accounts = relationship("BankAccount", back_populates="bank")


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=True)
    account_name: Mapped[str] = mapped_column(String(255), nullable=True)
    balance: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    currency: Mapped[str] = mapped_column(String(10), default="THB")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="bank_accounts")
    bank = relationship("Bank", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="bank_account", cascade="all, delete-orphan")
