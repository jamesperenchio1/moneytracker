from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class TradeAction(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    FEE = "fee"
    SPLIT = "split"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brokerage_account_id: Mapped[int] = mapped_column(ForeignKey("brokerage_accounts.id"), nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False, default=0)
    avg_cost_basis: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_cost_basis: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    brokerage_account = relationship("BrokerageAccount", back_populates="holdings")
    asset = relationship("Asset", back_populates="holdings")


class PortfolioTransaction(Base):
    __tablename__ = "portfolio_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brokerage_account_id: Mapped[int] = mapped_column(ForeignKey("brokerage_accounts.id"), nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=True)
    statement_id: Mapped[int] = mapped_column(ForeignKey("statements.id"), nullable=True)
    action: Mapped[TradeAction] = mapped_column(SQLEnum(TradeAction), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 8), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=True)
    total_amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    fees: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    brokerage_account = relationship("BrokerageAccount", back_populates="portfolio_transactions")
    asset = relationship("Asset", back_populates="portfolio_transactions")
    statement = relationship("Statement", back_populates="portfolio_transactions")
