"""Webull brokerage statement parser.

Supports CSV exports from Webull (both US and Thailand versions).
"""

import pandas as pd
from datetime import datetime

from app.parsers.base import BaseBrokerageParser, ParsedPortfolioTransaction


class WebullParser(BaseBrokerageParser):
    institution_code = "webull_usa"
    institution_name = "Webull USA"

    ACTION_MAP = {
        "buy": "buy",
        "sell": "sell",
        "dividend": "dividend",
        "deposit": "deposit",
        "withdrawal": "withdrawal",
        "commission": "fee",
        "fee": "fee",
        "transfer in": "transfer_in",
        "transfer out": "transfer_out",
    }

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        # PDFs are handled by WebullPDFParser — this parser only handles CSVs
        if file_path.lower().endswith(".pdf"):
            return False
        content = content_sample.lower()
        if "webull" in content:
            return True
        if file_path.lower().endswith(".csv"):
            try:
                df = pd.read_csv(file_path, nrows=2)
                cols = {c.strip().lower() for c in df.columns}
                return "ticker" in cols or "symbol" in cols
            except Exception:
                pass
        return False

    def parse(self, file_path: str) -> list[ParsedPortfolioTransaction]:
        df = pd.read_csv(file_path)
        df.columns = [c.strip().lower() for c in df.columns]

        transactions = []
        for _, row in df.iterrows():
            try:
                dt = pd.to_datetime(row.get("date", row.get("trade date", row.get("transaction date", ""))))
                if pd.isna(dt):
                    continue

                action_raw = str(row.get("action", row.get("type", row.get("side", "")))).strip().lower()
                action = self.ACTION_MAP.get(action_raw, action_raw)

                symbol = str(row.get("symbol", row.get("ticker", ""))).strip().upper()
                quantity = self._to_float(row.get("quantity", row.get("qty", row.get("shares", 0))))
                price = self._to_float(row.get("price", row.get("avg price", 0)))
                total = self._to_float(row.get("total", row.get("amount", row.get("net amount", 0))))
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
                        currency="USD",
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


class WebullThailandParser(WebullParser):
    institution_code = "webull_th"
    institution_name = "Webull Thailand"

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        content = content_sample.lower()
        return "webull" in content and ("thailand" in content or "th" in content or "thb" in content)
