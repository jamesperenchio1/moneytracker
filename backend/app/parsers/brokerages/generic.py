"""Generic brokerage statement parser for unrecognized formats."""

import pandas as pd
from datetime import datetime
from typing import Optional

from app.parsers.base import BaseBrokerageParser, ParsedPortfolioTransaction


class GenericBrokerageParser(BaseBrokerageParser):
    institution_code = "generic_brokerage"
    institution_name = "Generic Brokerage"

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        return file_path.lower().endswith((".csv", ".xlsx", ".xls"))

    def parse(self, file_path: str) -> list[ParsedPortfolioTransaction]:
        if file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        df.columns = [str(c).strip().lower() for c in df.columns]
        cols = set(df.columns)

        date_col = self._find_col(cols, ["date", "trade date", "transaction date", "txn_date"])
        action_col = self._find_col(cols, ["action", "type", "side", "transaction type"])
        symbol_col = self._find_col(cols, ["symbol", "ticker", "security", "instrument"])
        qty_col = self._find_col(cols, ["quantity", "qty", "shares", "units"])
        price_col = self._find_col(cols, ["price", "avg price", "fill price"])
        amount_col = self._find_col(cols, ["amount", "total", "net amount", "value"])
        fee_col = self._find_col(cols, ["fees", "commission", "fee"])

        if not date_col:
            raise ValueError("Cannot detect date column")

        transactions = []
        for _, row in df.iterrows():
            try:
                dt = pd.to_datetime(row[date_col])
                if pd.isna(dt):
                    continue

                action = str(row[action_col]).strip().lower() if action_col else "buy"
                symbol = str(row[symbol_col]).strip().upper() if symbol_col and pd.notna(row.get(symbol_col)) else None
                qty = self._to_float(row.get(qty_col, 0)) if qty_col else 0
                price = self._to_float(row.get(price_col, 0)) if price_col else 0
                amount = self._to_float(row.get(amount_col, 0)) if amount_col else 0
                fees = self._to_float(row.get(fee_col, 0)) if fee_col else 0

                if amount == 0 and qty > 0 and price > 0:
                    amount = qty * price

                transactions.append(
                    ParsedPortfolioTransaction(
                        transaction_date=dt.to_pydatetime(),
                        action=action,
                        symbol=symbol if symbol and symbol != "NAN" else None,
                        quantity=qty if qty > 0 else None,
                        price=price if price > 0 else None,
                        total_amount=abs(amount),
                        fees=fees,
                    )
                )
            except Exception:
                continue

        return transactions

    def _find_col(self, cols: set, candidates: list[str]) -> Optional[str]:
        for c in candidates:
            if c in cols:
                return c
        return None

    def _to_float(self, value) -> float:
        if pd.isna(value):
            return 0
        try:
            return float(str(value).replace(",", "").replace("$", "").strip())
        except (ValueError, TypeError):
            return 0
