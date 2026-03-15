from datetime import datetime, date, timezone
from sqlalchemy import String, DateTime, Integer, ForeignKey, Numeric, Enum as SQLEnum, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class AssetType(str, enum.Enum):
    STOCK = "stock"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    BOND = "bond"
    CRYPTO = "crypto"
    OPTION = "option"
    OTHER = "other"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    asset_type: Mapped[AssetType] = mapped_column(SQLEnum(AssetType), nullable=False, default=AssetType.STOCK)
    exchange: Mapped[str] = mapped_column(String(50), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    current_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=True)
    last_price_update: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    holdings = relationship("Holding", back_populates="asset")
    portfolio_transactions = relationship("PortfolioTransaction", back_populates="asset")
    historical_prices = relationship("HistoricalPrice", back_populates="asset", cascade="all, delete-orphan")


class HistoricalPrice(Base):
    __tablename__ = "historical_prices"
    __table_args__ = (UniqueConstraint("asset_id", "price_date", name="uq_asset_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    price_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=True)
    high_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=True)
    low_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=True)
    close_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=True)

    asset = relationship("Asset", back_populates="historical_prices")
