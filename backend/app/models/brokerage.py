from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class BrokerageName(str, enum.Enum):
    WEBULL_USA = "webull_usa"
    WEBULL_TH = "webull_th"
    DIME = "dime"
    OTHER = "other"


class Brokerage(Base):
    __tablename__ = "brokerages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[BrokerageName] = mapped_column(SQLEnum(BrokerageName), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    api_supported: Mapped[bool] = mapped_column(default=False)
    scraping_supported: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    accounts = relationship("BrokerageAccount", back_populates="brokerage")


class BrokerageAccount(Base):
    __tablename__ = "brokerage_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    brokerage_id: Mapped[int] = mapped_column(ForeignKey("brokerages.id"), nullable=False)
    account_identifier: Mapped[str] = mapped_column(String(100), nullable=True)
    account_name: Mapped[str] = mapped_column(String(255), nullable=True)
    cash_balance: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="brokerage_accounts")
    brokerage = relationship("Brokerage", back_populates="accounts")
    holdings = relationship("Holding", back_populates="brokerage_account", cascade="all, delete-orphan")
    portfolio_transactions = relationship("PortfolioTransaction", back_populates="brokerage_account", cascade="all, delete-orphan")
