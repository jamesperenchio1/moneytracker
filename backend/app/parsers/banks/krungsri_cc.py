"""Krungsri credit card statement parser (PDF).

Format: Krungsriayudhya Card Company billing statements.
Each transaction line: DD/MM/YY DD/MM/YY DESCRIPTION AMOUNT
Positive amounts = purchases (DEBIT), negative = payments/cashback (CREDIT).
"""

import re
import pdfplumber
from datetime import datetime

from app.parsers.base import BaseBankParser, ParsedBankTransaction, ParsedStatement

# Main transaction line: DD/MM/YY DD/MM/YY DESCRIPTION AMOUNT
_TX_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})\s+(.+?)\s+([-]?[\d,]+\.\d{2})\s*$"
)

# Installment-detail lines have an installment-fraction like "008/010" — skip them
_INSTALL_RE = re.compile(r"\d{3}/\d{3}")

# Thai/English lines to skip
_SKIP_PATTERNS = [
    "ยอดเรียกเก็บของรอบบัญชีที่แล้ว",  # previous balance carry-forward
    "SUBTOTAL FOR",
    "SUBTOTAL OF",
    "ยอดรวมรายการใช้จ่าย",
    "ยอดรวมการชำ",
    "ยอดรวมปรับปรุง",
    "ยอดรวมผ่อนชำ",
    "ยอดรวมที่ต้องชำ",
    "Transaction Amount",
    "Installment Amount",
    "Adjustment Amount",
    "Total Payment",
]


class KrungsriCreditCardParser(BaseBankParser):
    institution_code = "krungsri_cc"
    institution_name = "Krungsri"

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        if not file_path.lower().endswith(".pdf"):
            return False
        return (
            "Krungsriayudhya Card" in content_sample
            or "บัตรเครดิต กรุงศรี" in content_sample
        )

    # Regex to extract Total Payment Due amount from the summary line
    _TOTAL_DUE_RE = re.compile(
        r"(?:ยอดรวมที่ต้องชำระสำหรับบัตรเครดิต|Total Payment Due For Credit Card)\s+([\d,]+\.\d{2})"
    )

    def parse(self, file_path: str) -> ParsedStatement:
        transactions = []
        total_payment_due: float | None = None

        with pdfplumber.open(file_path) as pdf:
            full_text = "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )

        in_transactions = False
        for line in full_text.splitlines():
            line = line.strip()
            if not line:
                continue

            # Extract Total Payment Due before skip-pattern check
            m_due = self._TOTAL_DUE_RE.search(line)
            if m_due:
                try:
                    total_payment_due = float(m_due.group(1).replace(",", ""))
                except ValueError:
                    pass

            # Enter transaction section after the column-header line
            if "Transaction Date" in line and "Posting Date" in line:
                in_transactions = True
                continue

            if not in_transactions:
                continue

            # Skip known non-transaction lines
            if any(pat in line for pat in _SKIP_PATTERNS):
                continue

            m = _TX_RE.match(line)
            if not m:
                continue

            tx_date_str, _post_date, description, amount_str = m.groups()
            description = description.strip()

            # Skip installment summary lines (e.g. "008/010 3,090.00")
            if _INSTALL_RE.search(description):
                continue

            try:
                tx_date = datetime.strptime(tx_date_str, "%d/%m/%y")
                amount = float(amount_str.replace(",", ""))
            except ValueError:
                continue

            # Negative = payment / cashback = CREDIT; positive = purchase = DEBIT
            if amount < 0:
                txn_type = "credit"
                amount = abs(amount)
            else:
                txn_type = "debit"

            transactions.append(
                ParsedBankTransaction(
                    transaction_date=tx_date,
                    description=description,
                    amount=amount,
                    transaction_type=txn_type,
                    currency="THB",
                )
            )

        # Credit card balance is a liability — store as negative so total_cash subtracts it
        closing_balance = -total_payment_due if total_payment_due is not None else None
        return ParsedStatement(transactions=transactions, closing_balance=closing_balance)
