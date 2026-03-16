"""Webull USA PDF statement parser.

Parses monthly PDF statements from Webull Financial LLC containing:
- Securities Trading Activity (buys/sells with symbol, qty, price, fees)
- Open Positions (current holdings with quantities and prices)
- Account Activity (dividends, interest, fees)

The PDF format has multi-line entries where symbol/CUSIP are on one line
and trade data on the following line. Uses pdfplumber table extraction
where possible and falls back to text parsing.
"""

import re
from datetime import datetime

import pdfplumber

from app.parsers.base import BaseBrokerageParser, ParsedPortfolioTransaction


class WebullPDFParser(BaseBrokerageParser):
    institution_code = "webull_usa_pdf"
    institution_name = "Webull USA"

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        if not file_path.lower().endswith(".pdf"):
            return False
        content = content_sample.lower()
        return "webull" in content and (
            "securities trading" in content
            or "account activity" in content
            or "webull financial" in content
            or "statement period" in content
        )

    def parse(self, file_path: str) -> list[ParsedPortfolioTransaction]:
        transactions: list[ParsedPortfolioTransaction] = []

        with pdfplumber.open(file_path) as pdf:
            full_text = ""
            all_tables = []
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"
                tables = page.extract_tables() or []
                all_tables.extend(tables)

            # Parse Securities Trading Activity
            transactions.extend(self._parse_trading_activity(full_text))

            # Parse Open Positions as current holdings (buy at current price)
            transactions.extend(self._parse_open_positions(full_text))

            # Parse Account Activity (dividends, interest, fees)
            transactions.extend(self._parse_account_activity(full_text))

        return transactions

    def _parse_trading_activity(self, text: str) -> list[ParsedPortfolioTransaction]:
        """Parse the SECURITIES TRADING ACTIVITY section.

        Format observed in real PDFs:
        - Option: NVDA 250103C00131000 - 01/03/2025 01/06/2025 S -1.00 13.35 1,335.00 0.00 -0.10 1,334.90 N
        - Stock (multi-line):
            SMH - 92189F676
            01/06/2025 01/07/2025 S -5.00 260.70 1,303.50 0.00 -0.05 1,303.45 N N
        """
        transactions = []

        # Find the trading activity section
        trading_match = re.search(
            r"SECURITIES TRADING ACTIVITY(.*?)(?:OPEN POSITIONS|ACCOUNT ACTIVITY|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if not trading_match:
            return transactions

        section = trading_match.group(1)
        lines = section.split("\n")

        current_symbol = None
        current_name = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip header lines
            if any(h in line for h in ["Symbol", "Currency:", "Equities", "Trade Date", "Settlement"]):
                continue

            # Check if this line has trade data (starts with date pattern)
            # Format: 01/06/2025 01/07/2025 S -5.00 260.70 1,303.50 0.00 -0.05 1,303.45 N N
            trade_match = re.match(
                r"(\d{2}/\d{2}/\d{4})\s+"  # Trade Date
                r"(\d{2}/\d{2}/\d{4})\s+"  # Settlement Date
                r"([BS])\s+"  # Buy/Sell
                r"(-?[\d,]+\.?\d*)\s+"  # Quantity (can be negative)
                r"([\d,]+\.?\d*)\s+"  # Price
                r"(-?[\d,]+\.?\d*)\s+"  # Gross Amount
                r"(-?[\d,]+\.?\d*)\s+"  # Commission
                r"(-?[\d,]+\.?\d*)\s+"  # Fee/Tax
                r"(-?[\d,]+\.?\d*)",  # Net Amount
                line,
            )

            if trade_match:
                if current_symbol:
                    try:
                        trade_date = datetime.strptime(trade_match.group(1), "%m/%d/%Y")
                        side = trade_match.group(3)
                        quantity = abs(self._parse_number(trade_match.group(4)))
                        price = self._parse_number(trade_match.group(5))
                        gross = abs(self._parse_number(trade_match.group(6)))
                        commission = abs(self._parse_number(trade_match.group(7)))
                        fee_tax = abs(self._parse_number(trade_match.group(8)))
                        net_amount = abs(self._parse_number(trade_match.group(9)))

                        action = "sell" if side == "S" else "buy"
                        total_fees = commission + fee_tax
                        desc = f"{'Sell' if side == 'S' else 'Buy'} {current_symbol}"
                        if current_name:
                            desc += f" ({current_name})"

                        transactions.append(
                            ParsedPortfolioTransaction(
                                transaction_date=trade_date,
                                action=action,
                                symbol=current_symbol,
                                quantity=quantity if quantity > 0 else None,
                                price=price if price > 0 else None,
                                total_amount=net_amount if net_amount > 0 else gross,
                                fees=total_fees,
                                currency="USD",
                                description=desc,
                            )
                        )
                    except (ValueError, IndexError):
                        pass
                continue

            # Check if line has option trade data inline (symbol + option code + date on same line)
            # Format: NVDA 250103C00131000 - 01/03/2025 01/06/2025 S -1.00 13.35 ...
            option_match = re.match(
                r"([A-Z]{1,5})\s+(\d{6}[CP]\d+)\s*-?\s*"  # Symbol + Option code
                r"(\d{2}/\d{2}/\d{4})\s+"  # Trade Date
                r"(\d{2}/\d{2}/\d{4})\s+"  # Settlement Date
                r"([BS])\s+"  # Buy/Sell
                r"(-?[\d,]+\.?\d*)\s+"  # Quantity
                r"([\d,]+\.?\d*)\s+"  # Price
                r"(-?[\d,]+\.?\d*)\s+"  # Gross Amount
                r"(-?[\d,]+\.?\d*)\s+"  # Commission
                r"(-?[\d,]+\.?\d*)\s+"  # Fee/Tax
                r"(-?[\d,]+\.?\d*)",  # Net Amount
                line,
            )

            if option_match:
                try:
                    symbol = option_match.group(1)
                    option_code = option_match.group(2)
                    trade_date = datetime.strptime(option_match.group(3), "%m/%d/%Y")
                    side = option_match.group(5)
                    quantity = abs(self._parse_number(option_match.group(6)))
                    price = self._parse_number(option_match.group(7))
                    gross = abs(self._parse_number(option_match.group(8)))
                    commission = abs(self._parse_number(option_match.group(9)))
                    fee_tax = abs(self._parse_number(option_match.group(10)))
                    net_amount = abs(self._parse_number(option_match.group(11)))

                    action = "sell" if side == "S" else "buy"
                    total_fees = commission + fee_tax

                    transactions.append(
                        ParsedPortfolioTransaction(
                            transaction_date=trade_date,
                            action=action,
                            symbol=symbol,
                            quantity=quantity if quantity > 0 else None,
                            price=price if price > 0 else None,
                            total_amount=net_amount if net_amount > 0 else gross,
                            fees=total_fees,
                            currency="USD",
                            description=f"{'Sell' if side == 'S' else 'Buy'} Option {symbol} {option_code}",
                        )
                    )
                except (ValueError, IndexError):
                    pass
                continue

            # Check if this is a symbol line: "SMH - 92189F676" or "SPY - 78462F103"
            symbol_match = re.match(
                r"([A-Z]{1,5})\s*-\s*([A-Z0-9]{6,})",
                line,
            )
            if symbol_match:
                current_symbol = symbol_match.group(1)
                current_name = None
                continue

            # Check if this is a name line following the symbol (e.g. "VanEck Semiconductor ETF")
            if current_symbol and not re.match(r"\d", line) and len(line) > 3:
                # Looks like a name line
                if not any(c.isdigit() for c in line[:5]):
                    current_name = line
                    continue

        return transactions

    def _parse_open_positions(self, text: str) -> list[ParsedPortfolioTransaction]:
        """Parse OPEN POSITIONS section to create buy transactions for current holdings.

        Format:
        AVGO 11135F101 0.87 1 221.27 192.50
        INTC 458140100 22 1 19.43 427.46
        SPY 78462F103 8 1 601.82 4,814.56 N
        """
        transactions = []

        # Find the open positions section
        positions_match = re.search(
            r"OPEN POSITIONS(.*?)(?:Mutual Funds|ACCOUNT ACTIVITY|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if not positions_match:
            return transactions

        section = positions_match.group(1)

        # Extract statement period end date for transaction date
        period_match = re.search(r"Statement Period:.*?-\s*(\d{2}/\d{2}/\d{4})", text)
        period_end = datetime.strptime(period_match.group(1), "%m/%d/%Y") if period_match else datetime.now()

        # Match position lines: Symbol CUSIP Quantity Multiplier Price Amount [Callable]
        position_pattern = re.compile(
            r"([A-Z]{1,5})\s+"  # Symbol
            r"([A-Z0-9]{6,})\s+"  # CUSIP
            r"([\d.]+)\s+"  # Quantity
            r"(\d+)\s+"  # Multiplier
            r"([\d,.]+)\s+"  # Closing Price
            r"([\d,.]+)"  # Amount
        )

        for match in position_pattern.finditer(section):
            try:
                symbol = match.group(1)
                quantity = self._parse_number(match.group(3))
                price = self._parse_number(match.group(5))
                amount = self._parse_number(match.group(6))

                if quantity <= 0 or price <= 0:
                    continue

                # Skip if it looks like a header
                if symbol in ("Symbol", "Cusip"):
                    continue

                transactions.append(
                    ParsedPortfolioTransaction(
                        transaction_date=period_end,
                        action="buy",
                        symbol=symbol,
                        quantity=quantity,
                        price=price,
                        total_amount=amount,
                        fees=0,
                        currency="USD",
                        description=f"Open Position: {symbol} ({quantity} shares @ ${price:.2f})",
                    )
                )
            except (ValueError, IndexError):
                continue

        # Also parse Mutual Funds section (separate from equities)
        mf_match = re.search(
            r"Mutual Funds\s*\n(?:Symbol.*?\n)?(.*?)(?:ACCOUNT ACTIVITY|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if mf_match:
            mf_section = mf_match.group(1)
            mf_pattern = re.compile(
                r"([A-Z]{1,5})\s+"  # Symbol
                r"([A-Z0-9]{6,})\s+"  # CUSIP
                r"[\d.]+%?\s+"  # Yield
                r"([\d,.]+)\s+"  # Quantity
                r"([\d,.]+)\s+"  # Price
                r"([\d,.]+)"  # Amount
            )
            for match in mf_pattern.finditer(mf_section):
                try:
                    symbol = match.group(1)
                    quantity = self._parse_number(match.group(3))
                    price = self._parse_number(match.group(4))
                    amount = self._parse_number(match.group(5))
                    if quantity > 0 and symbol not in ("Symbol",):
                        transactions.append(
                            ParsedPortfolioTransaction(
                                transaction_date=period_end,
                                action="buy",
                                symbol=symbol,
                                quantity=quantity,
                                price=price,
                                total_amount=amount,
                                fees=0,
                                currency="USD",
                                description=f"Open Position (Fund): {symbol} ({quantity} units @ ${price:.2f})",
                            )
                        )
                except (ValueError, IndexError):
                    continue

        return transactions

    def _parse_account_activity(self, text: str) -> list[ParsedPortfolioTransaction]:
        """Parse the ACCOUNT ACTIVITY section for dividends, interest, fees.

        Format (multi-line, from page 4):
        01/02/2025 Dividend USD CASH PRCXX 60934N617 0.63 PRCXX Dividends Payment: 12/01/2024 to 12/31/2024
        01/15/2025 Interest USD BANK_SWEEP 1.76 Credit - FDIC-Insured Cash Management Interest Payment
        01/14/2025 Fee Income from FPSL USD CASH 0.04 FULLY-PAID SECURITIES LENDING
        """
        transactions = []

        activity_match = re.search(
            r"ACCOUNT ACTIVITY(.*?)(?:BANK BALANCE|ACCRUED|DISCLOSURES|IMPORTANT|NOTES|KEY DEFINITIONS|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if not activity_match:
            return transactions

        section = activity_match.group(1)
        lines = section.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match lines starting with a date
            date_match = re.match(r"(\d{2}/\d{2}/\d{4})\s+(.*)", line)
            if not date_match:
                continue

            date_str = date_match.group(1)
            rest = date_match.group(2).strip()

            # Skip JOURNAL/FUND_SWEEP entries (internal sweeps)
            if "JOURNAL" in rest or "FUND_SWEEP" in rest:
                continue

            # Skip FDIC balance entries
            if "FDIC Insured" in rest:
                continue

            # Extract the transaction type and amount
            # Look for a number (amount) in the line
            amount_matches = re.findall(r"(-?[\d,]+\.\d{2})", rest)
            if not amount_matches:
                continue

            # The first standalone number is usually the amount
            amount = self._parse_number(amount_matches[0])
            if abs(amount) < 0.001:
                continue

            try:
                txn_date = datetime.strptime(date_str, "%m/%d/%Y")
            except ValueError:
                continue

            rest_lower = rest.lower()

            # Determine action type
            if "dividend" in rest_lower:
                action = "dividend"
                # Extract symbol
                sym_match = re.search(r"\b([A-Z]{1,5})\b", rest)
                symbol = sym_match.group(1) if sym_match else None
                # Filter out non-symbol words
                if symbol in ("USD", "CASH", "IN", "OUT", "FDIC", "BANK"):
                    symbol = None
            elif "interest" in rest_lower:
                action = "dividend"
                symbol = None
            elif "fee" in rest_lower:
                action = "fee"
                symbol = None
            else:
                continue  # Skip unrecognized entries

            description = rest[:200]

            transactions.append(
                ParsedPortfolioTransaction(
                    transaction_date=txn_date,
                    action=action,
                    symbol=symbol,
                    quantity=None,
                    price=None,
                    total_amount=abs(amount),
                    fees=abs(amount) if action == "fee" else 0,
                    currency="USD",
                    description=description,
                )
            )

        return transactions

    @staticmethod
    def _parse_number(s: str) -> float:
        """Parse a number string, handling commas and negative signs."""
        try:
            return float(s.replace(",", "").replace("$", "").strip())
        except (ValueError, TypeError):
            return 0.0
