"""SCB (Siam Commercial Bank) statement parser.

Supports CSV exports from SCB Easy app and PDF e-statements.

PDF format (AcctSt_*.pdf):
  The table has 7 columns but all transaction data is merged into 3 cells:
    col[0]: newline-separated "DD/MM/YY HH:MM CODE CHANNEL AMOUNT"
    col[5]: newline-separated balance values
    col[6]: newline-separated "DESC :...\nNOTE :..." pairs
  Transaction type is inferred from balance delta (increase=credit, decrease=debit).
"""

import re
import pandas as pd
import pdfplumber
from datetime import datetime
from typing import Optional

from app.parsers.base import BaseBankParser, ParsedBankTransaction


class SCBParser(BaseBankParser):
    institution_code = "scb"
    institution_name = "Siam Commercial Bank"

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        if file_path.lower().endswith(".pdf"):
            return False  # Handled by SCBPDFParser
        content = content_sample.lower()
        if "scb" in content or "siam commercial" in content or "scb easy" in content:
            return True
        return False

    def parse(self, file_path: str) -> list[ParsedBankTransaction]:
        df = pd.read_csv(file_path)
        df.columns = [c.strip().lower() for c in df.columns]

        transactions = []
        for _, row in df.iterrows():
            try:
                dt = self._parse_date(row)
                amount, txn_type = self._parse_amount(row)
                if amount == 0:
                    continue
                transactions.append(
                    ParsedBankTransaction(
                        transaction_date=dt,
                        amount=amount,
                        transaction_type=txn_type,
                        description=str(row.get("description", row.get("details", ""))).strip(),
                        sender=str(row.get("sender", "")).strip() if "sender" in row.index else None,
                        receiver=str(row.get("receiver", "")).strip() if "receiver" in row.index else None,
                    )
                )
            except Exception:
                continue
        return transactions

    def _parse_date(self, row) -> datetime:
        for col in ("date", "transaction date", "transaction_date", "datetime"):
            if col in row.index:
                val = str(row[col]).strip()
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%d/%m/%Y %H:%M"):
                    try:
                        return datetime.strptime(val, fmt)
                    except ValueError:
                        continue
        raise ValueError("No date column found")

    def _parse_amount(self, row) -> tuple[float, str]:
        for debit_col in ("withdrawal", "debit", "amount_debit"):
            if debit_col in row.index:
                val = self._to_float(row[debit_col])
                if val > 0:
                    return val, "debit"
        for credit_col in ("deposit", "credit", "amount_credit"):
            if credit_col in row.index:
                val = self._to_float(row[credit_col])
                if val > 0:
                    return val, "credit"
        if "amount" in row.index:
            val = self._to_float(row["amount"])
            return abs(val), "debit" if val < 0 else "credit"
        return 0, "debit"

    def _to_float(self, value) -> float:
        if pd.isna(value):
            return 0
        try:
            return float(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0


class SCBPDFParser(BaseBankParser):
    """Parser for SCB PDF e-statements (AcctSt_*.pdf format).

    All transactions are in a single merged table cell, newline-separated.
    col[0]: "DD/MM/YY HH:MM CODE CHANNEL AMOUNT" per line
    col[5]: running balances per line
    col[6]: "DESC :...\\nNOTE :..." pairs
    """

    institution_code = "scb_pdf"
    institution_name = "Siam Commercial Bank (PDF)"

    _TX_LINE_RE = re.compile(
        r"^(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2})\s+"
        r"(\w+)\s+(\w+)\s+([\d,]+\.\d{2})$"
    )

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        if not file_path.lower().endswith(".pdf"):
            return False
        content = content_sample.lower()
        return "siam commercial" in content or ("scb" in content and "saving account" in content)

    def parse(self, file_path: str) -> list[ParsedBankTransaction]:
        transactions = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                for table in (page.extract_tables() or []):
                    transactions.extend(self._parse_table(table))
        return transactions

    def _parse_table(self, table: list) -> list[ParsedBankTransaction]:
        if not table or len(table) < 2:
            return []

        data_row = None
        for row in table[1:]:
            if row and row[0] and "\n" in str(row[0]):
                data_row = row
                break
        if data_row is None:
            return []

        tx_lines   = str(data_row[0]).split("\n") if data_row[0] else []
        bal_lines  = str(data_row[5]).split("\n") if len(data_row) > 5 and data_row[5] else []
        desc_raw   = str(data_row[6]).split("\n") if len(data_row) > 6 and data_row[6] else []

        # Build description list from "DESC :...\nNOTE :..." pairs
        descriptions: list[str] = []
        i = 0
        while i < len(desc_raw):
            line = desc_raw[i].strip()
            if line.startswith("DESC :"):
                desc_text = line[6:].strip()
                if i + 1 < len(desc_raw) and desc_raw[i + 1].strip().startswith("NOTE :"):
                    note = desc_raw[i + 1].strip()[6:].strip()
                    if note and note != "-":
                        desc_text = f"{desc_text} | {note}"
                    i += 2
                else:
                    i += 1
                descriptions.append(desc_text)
            else:
                i += 1

        # Parse transaction lines
        tx_entries = []
        for line in tx_lines:
            line = line.strip()
            if not line or "BALANCE BROUGHT FORWARD" in line:
                continue
            m = self._TX_LINE_RE.match(line)
            if m:
                date_s, time_s, code, channel, amt_s = m.groups()
                tx_entries.append((date_s, time_s, code, channel, self._to_float(amt_s)))

        balance_values = [self._to_float(b) for b in bal_lines if b.strip()]
        tx_balances = balance_values[1:] if len(balance_values) > 1 else balance_values
        prev_balance = balance_values[0] if balance_values else 0.0

        transactions: list[ParsedBankTransaction] = []
        for idx, (date_s, time_s, code, channel, amount) in enumerate(tx_entries):
            curr_balance = tx_balances[idx] if idx < len(tx_balances) else prev_balance
            if amount == 0:
                prev_balance = curr_balance
                continue

            txn_type = "credit" if curr_balance > prev_balance else "debit"

            try:
                dt = datetime.strptime(f"{date_s} {time_s}", "%d/%m/%y %H:%M")
            except ValueError:
                prev_balance = curr_balance
                continue

            desc = descriptions[idx] if idx < len(descriptions) else f"Code:{code} Ch:{channel}"
            transactions.append(
                ParsedBankTransaction(
                    transaction_date=dt,
                    amount=amount,
                    transaction_type=txn_type,
                    description=desc,
                    reference=f"{code}/{channel}",
                    currency="THB",
                )
            )
            prev_balance = curr_balance

        return transactions

    def _to_float(self, value: str) -> float:
        try:
            return float(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0.0
