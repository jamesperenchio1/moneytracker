"""Base parser interface for all statement parsers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ParsedBankTransaction:
    transaction_date: datetime
    amount: float
    transaction_type: str  # credit, debit, transfer
    description: Optional[str] = None
    sender: Optional[str] = None
    receiver: Optional[str] = None
    reference: Optional[str] = None
    currency: str = "THB"


@dataclass
class ParsedStatement:
    """Wraps parser output to include statement-level metadata."""
    transactions: list[ParsedBankTransaction] = field(default_factory=list)
    closing_balance: Optional[float] = None  # positive=asset, negative=liability (CC)


@dataclass
class ParsedPortfolioTransaction:
    transaction_date: datetime
    action: str  # buy, sell, dividend, deposit, withdrawal, fee
    total_amount: float
    symbol: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    fees: float = 0
    currency: str = "USD"
    description: Optional[str] = None


class BaseBankParser(ABC):
    """Base class for bank statement parsers."""

    institution_code: str = ""
    institution_name: str = ""

    @abstractmethod
    def parse(self, file_path: str) -> ParsedStatement:
        """Parse a bank statement file and return a ParsedStatement with transactions and closing balance."""
        ...

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        """Check if this parser can handle the given file."""
        return False


class BaseBrokerageParser(ABC):
    """Base class for brokerage statement parsers."""

    institution_code: str = ""
    institution_name: str = ""

    @abstractmethod
    def parse(self, file_path: str) -> list[ParsedPortfolioTransaction]:
        """Parse a brokerage statement and return normalized transactions."""
        ...

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        """Check if this parser can handle the given file."""
        return False
