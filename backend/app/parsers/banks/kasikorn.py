"""Kasikorn Bank (KBank) statement parser.

Supports CSV exports from KBank e-statement / K PLUS, and PDF e-statements.
PDF format: DD-MM-YY HH:MM DESCRIPTION AMOUNT BALANCE CHANNEL DETAILS
"""

import re
import pandas as pd
import pdfplumber
from datetime import datetime
from typing import Optional

from app.parsers.base import BaseBankParser, ParsedBankTransaction


# Known KBank PDF channels — ordered by length (longest first) to avoid partial matches.
_KBANK_CHANNELS = [
    "Internet/Mobile", "EDC/K SHOP", "K PLUS", "ATM/CDM", "BCMS", "ATM", "EDC",
]

# Regex for a KBank PDF transaction line (channel extracted separately):
# 16-04-25 17:15 Payment 343.00 2,480.50 EDC/K SHOP Paid for Ref X4665...
_KBANK_TX_RE = re.compile(
    r"^(\d{2}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+"  # date  time
    r"(.+?)\s+"                                    # description (non-greedy)
    r"([\d,]+\.\d{2})\s+"                          # amount
    r"([\d,]+\.\d{2})\s*"                          # balance
    r"(.*)$"                                        # channel + details (parsed below)
)

_CREDIT_KEYWORDS = {"deposit", "transfer deposit", "qr transfer deposit", "interest"}
_DEBIT_KEYWORDS  = {"payment", "transfer withdrawal", "withdrawal", "fee", "charge"}


def _split_channel_details(remainder: str) -> tuple[str, str]:
    """Strip a known channel prefix from the remainder, return (channel, details)."""
    for ch in _KBANK_CHANNELS:
        if remainder.startswith(ch):
            return ch, remainder[len(ch):].strip()
    # Fallback: first token is the channel
    parts = remainder.split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


class KasikornParser(BaseBankParser):
    institution_code = "kasikorn"
    institution_name = "Kasikorn Bank"

    EXPECTED_COLUMNS = {"date", "description", "withdrawal", "deposit"}

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        content = content_sample.lower()
        if "kasikorn" in content or "kbank" in content or "k plus" in content:
            return True
        if file_path.lower().endswith(".csv"):
            try:
                df = pd.read_csv(file_path, nrows=2)
                cols = {c.strip().lower() for c in df.columns}
                return cls.EXPECTED_COLUMNS.issubset(cols)
            except Exception:
                pass
        return False

    def parse(self, file_path: str) -> list[ParsedBankTransaction]:
        df = pd.read_csv(file_path)
        df.columns = [c.strip().lower() for c in df.columns]

        transactions = []
        for _, row in df.iterrows():
            try:
                date_str = str(row.get("date", "")).strip()
                time_str = str(row.get("time", "00:00")).strip()
                dt = self._parse_date(date_str, time_str)

                withdrawal = self._to_float(row.get("withdrawal", 0))
                deposit = self._to_float(row.get("deposit", 0))

                if withdrawal > 0:
                    txn_type = "debit"
                    amount = withdrawal
                elif deposit > 0:
                    txn_type = "credit"
                    amount = deposit
                else:
                    continue

                transactions.append(
                    ParsedBankTransaction(
                        transaction_date=dt,
                        amount=amount,
                        transaction_type=txn_type,
                        description=str(row.get("description", "")).strip(),
                        reference=str(row.get("reference", "")).strip() if "reference" in row else None,
                    )
                )
            except Exception:
                continue

        return transactions

    def _parse_date(self, date_str: str, time_str: str) -> datetime:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(f"{date_str} {time_str}", f"{fmt} %H:%M")
            except ValueError:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        raise ValueError(f"Cannot parse date: {date_str}")

    def _to_float(self, value) -> float:
        if pd.isna(value):
            return 0
        try:
            return abs(float(str(value).replace(",", "").strip()))
        except (ValueError, TypeError):
            return 0


class KasikornPDFParser(BaseBankParser):
    """Parser for Kasikorn PDF e-statements (STM_SA*.pdf format).

    Format per line: DD-MM-YY HH:MM DESCRIPTION AMOUNT BALANCE CHANNEL DETAILS
    """

    institution_code = "kasikorn_pdf"
    institution_name = "Kasikorn Bank (PDF)"

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        if not file_path.lower().endswith(".pdf"):
            return False
        content = content_sample.lower()
        # Exclude SCB files that may mention "k plus" in transfer descriptions
        if "siam commercial" in content or "saving account" in content:
            return False
        # KBank PDF e-statements have "k plus" as a transaction channel or header
        return "k plus" in content or "kasikorn" in content

    def parse(self, file_path: str) -> list[ParsedBankTransaction]:
        transactions = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                txns = self._parse_page_text(text)
                transactions.extend(txns)

        return transactions

    def _parse_page_text(self, text: str) -> list[ParsedBankTransaction]:
        transactions = []
        prev_balance: Optional[float] = None

        for raw_line in text.split("\n"):
            line = raw_line.strip()

            # Beginning Balance line — capture starting balance
            bb_match = re.match(r"(\d{2}-\d{2}-\d{2})\s+Beginning Balance\s+([\d,]+\.\d{2})", line)
            if bb_match:
                prev_balance = self._to_float(bb_match.group(2))
                continue

            m = _KBANK_TX_RE.match(line)
            if not m:
                continue

            date_str, time_str, desc, amount_str, balance_str, remainder = m.groups()
            channel, details = _split_channel_details((remainder or "").strip())
            amount = self._to_float(amount_str)
            balance = self._to_float(balance_str)

            if amount == 0:
                prev_balance = balance
                continue

            # Determine credit/debit from description keywords, fallback to balance delta
            desc_lower = desc.lower()
            if any(kw in desc_lower for kw in _CREDIT_KEYWORDS):
                txn_type = "credit"
            elif any(kw in desc_lower for kw in _DEBIT_KEYWORDS):
                txn_type = "debit"
            elif prev_balance is not None:
                txn_type = "credit" if balance > prev_balance else "debit"
            else:
                txn_type = "debit"

            try:
                dt = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%y %H:%M")
            except ValueError:
                prev_balance = balance
                continue

            full_desc = f"{desc} {(details or '').strip()}".strip()

            transactions.append(
                ParsedBankTransaction(
                    transaction_date=dt,
                    amount=amount,
                    transaction_type=txn_type,
                    description=full_desc,
                    reference=channel.strip() if channel else None,
                    currency="THB",
                )
            )
            prev_balance = balance

        return transactions

    def _to_float(self, value: str) -> float:
        try:
            return float(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0.0
