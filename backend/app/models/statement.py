from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class StatementType(str, enum.Enum):
    BANK = "bank"
    BROKERAGE = "brokerage"
    CREDIT_CARD = "credit_card"


class StatementStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    statement_type: Mapped[StatementType] = mapped_column(SQLEnum(StatementType), nullable=False)
    institution_code: Mapped[str] = mapped_column(String(50), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # csv, pdf, xlsx
    status: Mapped[StatementStatus] = mapped_column(SQLEnum(StatementStatus), default=StatementStatus.PENDING)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    audit_log: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array of processing steps
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="statements")
    transactions = relationship("Transaction", back_populates="statement")
    portfolio_transactions = relationship("PortfolioTransaction", back_populates="statement")
