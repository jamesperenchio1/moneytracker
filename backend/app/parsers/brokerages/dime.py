"""Dime brokerage statement parser."""

import pandas as pd
from datetime import datetime

from app.parsers.base import BaseBrokerageParser, ParsedPortfolioTransaction


class DimeParser(BaseBrokerageParser):
    institution_code = "dime"
    institution_name = "Dime"

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        content = content_sample.lower()
        return "dime" in content

    def parse(self, file_path: str) -> list[ParsedPortfolioTransaction]:
        if file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        df.columns = [c.strip().lower() for c in df.columns]

        transactions = []
        for _, row in df.iterrows():
            try:
                dt = pd.to_datetime(
                    row.get("date", row.get("trade date", row.get("transaction date", "")))
                )
                if pd.isna(dt):
                    continue

                action_raw = str(row.get("type", row.get("action", row.get("side", "")))).strip().lower()
                action_map = {
                    "buy": "buy", "purchase": "buy",
                    "sell": "sell", "sale": "sell",
                    "dividend": "dividend", "div": "dividend",
                    "deposit": "deposit", "withdrawal": "withdrawal",
                    "fee": "fee", "commission": "fee",
                }
                action = action_map.get(action_raw, action_raw)

                symbol = str(row.get("symbol", row.get("ticker", row.get("security", "")))).strip().upper()
                quantity = self._to_float(row.get("quantity", row.get("shares", row.get("units", 0))))
                price = self._to_float(row.get("price", 0))
                total = self._to_float(row.get("amount", row.get("total", row.get("net_amount", 0))))
                fees = self._to_float(row.get("fees", row.get("commission", 0)))

                if total == 0 and quantity > 0 and price > 0:
                    total = quantity * price

                transactions.append(
                    ParsedPortfolioTransaction(
                        transaction_date=dt.to_pydatetime(),
                        action=action,
                        symbol=symbol if symbol and symbol != "NAN" else None,
                        quantity=quantity if quantity > 0 else None,
                        price=price if price > 0 else None,
                        total_amount=abs(total),
                        fees=fees,
                        description=str(row.get("description", "")).strip(),
                    )
                )
            except Exception:
                continue

        return transactions

    def _to_float(self, value) -> float:
        if pd.isna(value):
            return 0
        try:
            return float(str(value).replace(",", "").replace("$", "").strip())
        except (ValueError, TypeError):
            return 0
