"""Kasikorn Bank (KBank) statement parser.

Supports CSV exports from KBank e-statement / K PLUS.
Expected columns: Date, Time, Description, Withdrawal, Deposit, Balance, Channel
"""

import pandas as pd
from datetime import datetime

from app.parsers.base import BaseBankParser, ParsedBankTransaction


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
