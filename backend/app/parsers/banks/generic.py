"""Generic bank statement parser.

Handles CSV/Excel files that don't match any specific bank parser.
Attempts to auto-detect column mappings.
"""

import pandas as pd
import pdfplumber
from datetime import datetime
from typing import Optional

from app.parsers.base import BaseBankParser, ParsedBankTransaction


class GenericBankCSVParser(BaseBankParser):
    institution_code = "generic"
    institution_name = "Generic Bank"

    DATE_COLUMNS = ["date", "transaction date", "transaction_date", "datetime", "txn_date", "posting date"]
    AMOUNT_COLUMNS = ["amount", "total", "value"]
    DEBIT_COLUMNS = ["withdrawal", "debit", "amount_debit", "out"]
    CREDIT_COLUMNS = ["deposit", "credit", "amount_credit", "in"]
    DESC_COLUMNS = ["description", "details", "memo", "narrative", "particulars", "remark"]

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        return file_path.lower().endswith((".csv", ".xlsx", ".xls"))

    def parse(self, file_path: str) -> list[ParsedBankTransaction]:
        if file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        df.columns = [str(c).strip().lower() for c in df.columns]
        cols = set(df.columns)

        date_col = self._find_column(cols, self.DATE_COLUMNS)
        desc_col = self._find_column(cols, self.DESC_COLUMNS)
        debit_col = self._find_column(cols, self.DEBIT_COLUMNS)
        credit_col = self._find_column(cols, self.CREDIT_COLUMNS)
        amount_col = self._find_column(cols, self.AMOUNT_COLUMNS) if not debit_col else None

        if not date_col:
            raise ValueError("Cannot detect date column in file")

        transactions = []
        for _, row in df.iterrows():
            try:
                dt = pd.to_datetime(row[date_col])
                if pd.isna(dt):
                    continue

                amount, txn_type = 0.0, "debit"

                if debit_col and credit_col:
                    debit = self._to_float(row.get(debit_col, 0))
                    credit = self._to_float(row.get(credit_col, 0))
                    if debit > 0:
                        amount, txn_type = debit, "debit"
                    elif credit > 0:
                        amount, txn_type = credit, "credit"
                    else:
                        continue
                elif amount_col:
                    val = self._to_float(row.get(amount_col, 0))
                    if val == 0:
                        continue
                    amount = abs(val)
                    txn_type = "credit" if val > 0 else "debit"
                else:
                    continue

                transactions.append(
                    ParsedBankTransaction(
                        transaction_date=dt.to_pydatetime(),
                        amount=amount,
                        transaction_type=txn_type,
                        description=str(row[desc_col]).strip() if desc_col and pd.notna(row.get(desc_col)) else None,
                    )
                )
            except Exception:
                continue

        return transactions

    def _find_column(self, cols: set, candidates: list[str]) -> Optional[str]:
        for c in candidates:
            if c in cols:
                return c
        return None

    def _to_float(self, value) -> float:
        if pd.isna(value):
            return 0
        try:
            return float(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0


class GenericBankPDFParser(BaseBankParser):
    institution_code = "generic_pdf"
    institution_name = "Generic Bank (PDF)"

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        return file_path.lower().endswith(".pdf")

    def parse(self, file_path: str) -> list[ParsedBankTransaction]:
        transactions = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 2:
                        continue

                    # Use first row as headers
                    headers = [str(h).strip().lower() if h else "" for h in table[0]]
                    for row in table[1:]:
                        try:
                            row_dict = dict(zip(headers, row))
                            txn = self._parse_row(row_dict, headers)
                            if txn:
                                transactions.append(txn)
                        except Exception:
                            continue

        return transactions

    def _parse_row(self, row: dict, headers: list[str]) -> Optional[ParsedBankTransaction]:
        # Find date
        date_val = None
        for key in ("date", "transaction date", "txn date"):
            if key in row and row[key]:
                try:
                    date_val = pd.to_datetime(row[key])
                    break
                except Exception:
                    continue

        if not date_val:
            return None

        # Find amount
        amount = 0.0
        txn_type = "debit"

        for key in ("withdrawal", "debit"):
            if key in row and row[key]:
                val = self._to_float(row[key])
                if val > 0:
                    amount, txn_type = val, "debit"
                    break

        if amount == 0:
            for key in ("deposit", "credit"):
                if key in row and row[key]:
                    val = self._to_float(row[key])
                    if val > 0:
                        amount, txn_type = val, "credit"
                        break

        if amount == 0:
            for key in ("amount", "total"):
                if key in row and row[key]:
                    val = self._to_float(row[key])
                    if val != 0:
                        amount = abs(val)
                        txn_type = "credit" if val > 0 else "debit"
                        break

        if amount == 0:
            return None

        desc = row.get("description") or row.get("details") or row.get("memo") or ""

        return ParsedBankTransaction(
            transaction_date=date_val.to_pydatetime(),
            amount=amount,
            transaction_type=txn_type,
            description=str(desc).strip(),
        )

    def _to_float(self, value) -> float:
        if not value:
            return 0
        try:
            return float(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0
