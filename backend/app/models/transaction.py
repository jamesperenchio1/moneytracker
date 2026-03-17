from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, ForeignKey, Numeric, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class TransactionType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER = "transfer"


class CategoryName(str, enum.Enum):
    FOOD = "food"
    RENT = "rent"
    TRANSPORTATION = "transportation"
    UTILITIES = "utilities"
    SUBSCRIPTIONS = "subscriptions"
    INCOME = "income"
    TRANSFERS = "transfers"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    INVESTMENT = "investment"
    CREDIT_CARD_PAYMENT = "credit_card_payment"
    OTHER = "other"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[CategoryName] = mapped_column(SQLEnum(CategoryName), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=True)
    keywords: Mapped[str] = mapped_column(Text, nullable=True)  # comma-separated keywords for auto-categorization

    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bank_account_id: Mapped[int] = mapped_column(ForeignKey("bank_accounts.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=True)
    statement_id: Mapped[int] = mapped_column(ForeignKey("statements.id"), nullable=True)
    transaction_type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="THB")
    description: Mapped[str] = mapped_column(Text, nullable=True)
    sender: Mapped[str] = mapped_column(String(255), nullable=True)
    receiver: Mapped[str] = mapped_column(String(255), nullable=True)
    reference: Mapped[str] = mapped_column(String(255), nullable=True)
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    bank_account = relationship("BankAccount", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    statement = relationship("Statement", back_populates="transactions")
