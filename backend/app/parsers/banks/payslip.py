"""Payslip PDF parser.

Parses payslip PDFs (e.g., Chromalloy Thailand) to extract salary as income transactions.
Handles various payslip formats with Thai and English text.
"""

import re
from datetime import datetime
from typing import Optional

import pdfplumber

from app.parsers.base import BaseBankParser, ParsedBankTransaction, ParsedStatement


class PayslipParser(BaseBankParser):
    institution_code = "payslip"
    institution_name = "Payslip"

    @classmethod
    def can_parse(cls, file_path: str, content_sample: str = "") -> bool:
        if not file_path.lower().endswith(".pdf"):
            return False
        content = content_sample.lower()
        # Must have payslip-related keywords
        payslip_keywords = ["payslip", "pay slip", "net pay", "สลิปเงินเดือน", "เงินเดือน"]
        structure_keywords = ["earnings", "deductions", "gross pay", "total earnings", "total deductions"]

        has_payslip = any(kw in content for kw in payslip_keywords)
        has_structure = any(kw in content for kw in structure_keywords)

        return has_payslip or (has_structure and ("salary" in content or "basic" in content))

    def parse(self, file_path: str) -> ParsedStatement:
        transactions = []

        with pdfplumber.open(file_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"

        if not full_text.strip():
            return ParsedStatement(transactions=transactions)

        # Extract key fields
        net_pay = self._extract_net_pay(full_text)
        if net_pay is None or net_pay <= 0:
            return ParsedStatement(transactions=transactions)

        payment_date = self._extract_payment_date(full_text)
        employer = self._extract_employer(full_text)
        pay_period = self._extract_pay_period(full_text)
        base_salary = self._extract_amount(full_text, r"(?:monthly\s+basic\s+salary|base\s+salary|basic\s+salary|เงินเดือน)\s*[:：]?\s*([\d,]+(?:\.\d{2})?)")
        housing = self._extract_amount(full_text, r"(?:housing\s+allowance|ค่าที่พัก)\s*[:：]?\s*([\d,]+(?:\.\d{2})?)")
        total_earnings = self._extract_amount(full_text, r"(?:total\s+earnings|รวมรายได้)\s*[:：]?\s*([\d,]+(?:\.\d{2})?)")
        total_deductions = self._extract_amount(full_text, r"(?:total\s+deductions|รวมหัก)\s*[:：]?\s*([\d,]+(?:\.\d{2})?)")

        # Build description
        desc_parts = [f"Salary"]
        if employer:
            desc_parts[0] = f"Salary - {employer}"
        detail_parts = []
        if base_salary:
            detail_parts.append(f"Base: {base_salary:,.0f}")
        if housing:
            detail_parts.append(f"Housing: {housing:,.0f}")
        if total_earnings:
            detail_parts.append(f"Gross: {total_earnings:,.0f}")
        if total_deductions:
            detail_parts.append(f"Deductions: {total_deductions:,.0f}")
        detail_parts.append(f"Net: {net_pay:,.2f}")

        if detail_parts:
            desc_parts.append(f"({', '.join(detail_parts)})")
        if pay_period:
            desc_parts.append(f"[{pay_period}]")

        description = " ".join(desc_parts)

        transactions.append(
            ParsedBankTransaction(
                transaction_date=payment_date or datetime.now(),
                amount=net_pay,
                transaction_type="credit",
                description=description,
                sender=employer or "Employer",
                receiver=None,
                reference=f"payslip-{payment_date.strftime('%Y%m%d') if payment_date else 'unknown'}",
                currency="THB",
            )
        )

        return ParsedStatement(transactions=transactions)

    def _extract_net_pay(self, text: str) -> Optional[float]:
        """Extract net pay amount from payslip text."""
        patterns = [
            r"net\s+pay\s*[:：]?\s*[฿B]?\s*([\d,]+\.\d{2})",
            r"net\s+pay\s+([\d,]+\.\d{2})",
            r"เงินสุทธิ\s*[:：]?\s*[฿B]?\s*([\d,]+\.\d{2})",
            r"รับเงินสุทธิ\s*[:：]?\s*[฿B]?\s*([\d,]+\.\d{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        return None

    def _extract_payment_date(self, text: str) -> Optional[datetime]:
        """Extract payment date from payslip."""
        patterns = [
            # DD/MM/YYYY format (common in Thai payslips)
            (r"(?:payment\s+date|pay\s+date|วันจ่ายเงิน)\s*[:：]?\s*(\d{2}/\d{2}/\d{4})", "%d/%m/%Y"),
            # YYYY-MM-DD format
            (r"(?:payment\s+date|pay\s+date)\s*[:：]?\s*(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
            # From filename pattern like 20260127
            (r"_(\d{8})_", None),
        ]
        for pattern, fmt in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    if fmt:
                        return datetime.strptime(date_str, fmt)
                    else:
                        return datetime.strptime(date_str, "%Y%m%d")
                except ValueError:
                    continue

        # Try to extract from pay period end date
        period_match = re.search(r"(\d{2}/\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{2}/\d{4})", text)
        if period_match:
            try:
                return datetime.strptime(period_match.group(2), "%d/%m/%Y")
            except ValueError:
                pass

        return None

    def _extract_employer(self, text: str) -> Optional[str]:
        """Extract employer name from payslip."""
        # Look for company name patterns
        patterns = [
            r"(?:company|employer|บริษัท)\s*[:：]?\s*(.+?)(?:\n|$)",
            # Match "Company Ltd" or "Company Co., Ltd" patterns in first few lines
            r"^(.+?(?:Ltd\.?|Co\.,?\s*Ltd\.?|PLC|Inc\.?|Corp\.?))\s*$",
        ]
        lines = text.split("\n")
        for pattern in patterns:
            for line in lines[:10]:  # Check first 10 lines
                match = re.search(pattern, line.strip(), re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    if len(name) > 3 and len(name) < 100:
                        return name
        return None

    def _extract_pay_period(self, text: str) -> Optional[str]:
        """Extract pay period string."""
        patterns = [
            r"(?:pay\s+period|period|งวด)\s*[:：]?\s*(.+?)(?:\n|$)",
            r"(\d{2}/\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{2}/\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.lastindex == 2:
                    return f"{match.group(1)} - {match.group(2)}"
                result = match.group(1).strip()
                if len(result) > 3:
                    return result
        return None

    def _extract_amount(self, text: str, pattern: str) -> Optional[float]:
        """Extract a specific amount using a regex pattern."""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except (ValueError, IndexError):
                pass
        return None
