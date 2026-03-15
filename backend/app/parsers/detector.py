"""Auto-detect the correct parser for a given statement file."""

from app.parsers.base import BaseBankParser, BaseBrokerageParser
from app.parsers.banks.kasikorn import KasikornParser, KasikornPDFParser
from app.parsers.banks.scb import SCBParser, SCBPDFParser
from app.parsers.banks.generic import GenericBankCSVParser, GenericBankPDFParser
from app.parsers.brokerages.webull import WebullParser, WebullThailandParser
from app.parsers.brokerages.dime import DimeParser
from app.parsers.brokerages.generic import GenericBrokerageParser


# Ordered by specificity — specific parsers first, generic last.
# PDF-specific parsers must come before their CSV counterparts so a PDF
# content sample match goes to the PDF parser, not the CSV one.
BANK_PARSERS: list[type[BaseBankParser]] = [
    KasikornPDFParser,  # KBank PDF e-statements
    SCBPDFParser,       # SCB PDF e-statements
    KasikornParser,     # KBank CSV
    SCBParser,          # SCB CSV
    GenericBankPDFParser,
    GenericBankCSVParser,
]

BROKERAGE_PARSERS: list[type[BaseBrokerageParser]] = [
    WebullThailandParser,
    WebullParser,
    DimeParser,
    GenericBrokerageParser,
]


def _read_sample(file_path: str) -> str:
    """Read a small sample of the file for detection."""
    try:
        if file_path.endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages[:2]:
                    text += page.extract_text() or ""
                return text[:2000]
        else:
            with open(file_path, "r", errors="ignore") as f:
                return f.read(2000)
    except Exception:
        return ""


def detect_bank_parser(file_path: str, institution_code: str = None) -> BaseBankParser:
    """Detect and return the appropriate bank parser for a file."""
    if institution_code:
        for parser_cls in BANK_PARSERS:
            if parser_cls.institution_code == institution_code:
                return parser_cls()

    sample = _read_sample(file_path)

    for parser_cls in BANK_PARSERS:
        if parser_cls.can_parse(file_path, sample):
            return parser_cls()

    raise ValueError(f"No parser found for file: {file_path}")


def detect_brokerage_parser(file_path: str, institution_code: str = None) -> BaseBrokerageParser:
    """Detect and return the appropriate brokerage parser for a file."""
    if institution_code:
        for parser_cls in BROKERAGE_PARSERS:
            if parser_cls.institution_code == institution_code:
                return parser_cls()

    sample = _read_sample(file_path)

    for parser_cls in BROKERAGE_PARSERS:
        if parser_cls.can_parse(file_path, sample):
            return parser_cls()

    raise ValueError(f"No parser found for file: {file_path}")
