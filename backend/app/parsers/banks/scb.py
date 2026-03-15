"""SCB (Siam Commercial Bank) statement parser.

Supports CSV exports from SCB Easy app.
"""

import pandas as pd
from datetime import datetime

from app.parsers.base import BaseBankParser, ParsedBankTransaction


class SCBParser(BaseBankParser):
    institution_code = "scb"
    institution_name = "Siam Commercial Bank"

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
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
        # Try separate debit/credit columns
        for debit_col in ("withdrawal", "debit", "amount_debit"):
            if debit_col in row.index:
                val = self._to_float(row[debit_col])
                if val > 0:
                    credit_col_match = None
                    for credit_col in ("deposit", "credit", "amount_credit"):
                        if credit_col in row.index:
                            credit_col_match = credit_col
                            break
                    return val, "debit"

        for credit_col in ("deposit", "credit", "amount_credit"):
            if credit_col in row.index:
                val = self._to_float(row[credit_col])
                if val > 0:
                    return val, "credit"

        # Single amount column
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
