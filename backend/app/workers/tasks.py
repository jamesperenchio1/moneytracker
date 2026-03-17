"""Celery background tasks for data processing."""

import json
import logging
import os
from datetime import datetime, date, timedelta, timezone

from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.core.config import get_settings
from app.models.statement import Statement, StatementType, StatementStatus
from app.models.transaction import Transaction, TransactionType, Category, CategoryName
from app.models.bank import Bank, BankAccount, BankName
from app.models.brokerage import BrokerageAccount
from app.models.portfolio import Holding, PortfolioTransaction, TradeAction
from app.models.asset import Asset, HistoricalPrice
from app.parsers.detector import detect_bank_parser, detect_brokerage_parser
from app.services.categorizer import infer_category
from app.services.market_data import fetch_historical_prices_sync

logger = logging.getLogger(__name__)
settings = get_settings()

# Sync engine for Celery workers
sync_engine = create_engine(settings.database_url_sync, pool_size=5)


def get_sync_session() -> Session:
    return Session(sync_engine)


def _now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit_entry(step: str, detail: str, level: str = "info", **kwargs) -> dict:
    entry = {"step": step, "ts": _now_ts(), "level": level, "detail": detail}
    entry.update({k: v for k, v in kwargs.items() if v is not None})
    return entry


@celery_app.task(bind=True, max_retries=3)
def process_statement(self, statement_id: int):
    """Process an uploaded statement file."""
    with get_sync_session() as db:
        stmt = db.get(Statement, statement_id)
        if not stmt:
            return

        stmt.status = StatementStatus.PROCESSING
        db.commit()

        audit: list[dict] = []

        # Log file receipt
        try:
            file_size_kb = round(os.path.getsize(stmt.file_path) / 1024, 1)
        except OSError:
            file_size_kb = 0
        audit.append(_audit_entry(
            "file_received",
            f"{stmt.file_name} ({file_size_kb} KB) — type: {stmt.statement_type.value}",
        ))

        try:
            if stmt.statement_type == StatementType.BANK:
                count = _process_bank_statement(stmt, db, audit)
            elif stmt.statement_type == StatementType.CREDIT_CARD:
                count = _process_credit_card_statement(stmt, db, audit)
            elif stmt.statement_type == StatementType.BROKERAGE:
                count = _process_brokerage_statement(stmt, db, audit)
            else:
                raise ValueError(f"Unknown statement type: {stmt.statement_type}")

            audit.append(_audit_entry(
                "summary",
                f"Processing complete — {count} record(s) saved",
            ))
            stmt.status = StatementStatus.COMPLETED
            stmt.records_processed = count
            stmt.processed_at = datetime.now(timezone.utc)
            stmt.audit_log = json.dumps(audit)
            db.commit()

        except Exception as exc:
            db.rollback()
            audit.append(_audit_entry("error", str(exc)[:300], level="error"))
            stmt.status = StatementStatus.FAILED
            stmt.error_message = str(exc)[:500]
            stmt.audit_log = json.dumps(audit)
            db.commit()
            raise self.retry(exc=exc, countdown=60)


# ---------------------------------------------------------------------------
# CC-payment keywords used to flag bank-side payoff transactions
# ---------------------------------------------------------------------------
_CC_PAYMENT_KEYWORDS = [
    "credit card", "creditcard", "cc payment", "visa payment",
    "mastercard payment", "amex payment",
    "บัตรเครดิต", "ชำระบัตร", "ชำระค่าบัตร",
]


def _is_cc_payment(description: str) -> bool:
    if not description:
        return False
    desc = description.lower()
    return any(kw in desc for kw in _CC_PAYMENT_KEYWORDS)


def _get_or_create_bank_account(stmt: Statement, parser_institution_code: str, db: Session) -> BankAccount:
    """Resolve the correct BankAccount for this statement, auto-creating if needed."""
    _INSTITUTION_TO_BANK = {
        "kasikorn": BankName.KASIKORN,
        "kasikorn_pdf": BankName.KASIKORN,
        "scb": BankName.SCB,
        "scb_pdf": BankName.SCB,
        "generic": BankName.OTHER,
        "generic_pdf": BankName.OTHER,
    }

    code = stmt.institution_code or parser_institution_code
    bank_name = _INSTITUTION_TO_BANK.get(code, BankName.OTHER)

    bank = db.execute(select(Bank).where(Bank.code == bank_name)).scalars().first()

    query = select(BankAccount).where(BankAccount.user_id == stmt.user_id)
    if bank:
        query = query.where(BankAccount.bank_id == bank.id)
    account = db.execute(query).scalars().first()

    if not account:
        account = BankAccount(
            user_id=stmt.user_id,
            bank_id=bank.id if bank else None,
            account_name=bank.name if bank else "Unknown Bank",
            currency="THB",
            balance=0,
        )
        db.add(account)
        db.flush()
        logger.info(f"Auto-created BankAccount for user {stmt.user_id}, bank={bank_name.value}")

    return account


def _process_bank_statement(stmt: Statement, db: Session, audit: list[dict]) -> int:
    """Parse bank statement and insert transactions."""
    parser = detect_bank_parser(stmt.file_path, stmt.institution_code)

    audit.append(_audit_entry(
        "parser_detected",
        f"Using {parser.__class__.__name__}",
        parser_name=parser.__class__.__name__,
        expected=(
            "CSV/Excel with columns: date, description, debit, credit, balance"
            if "pdf" not in parser.__class__.__name__.lower()
            else "PDF bank statement — transaction history table"
        ),
    ))

    parsed_txns = parser.parse(stmt.file_path)
    audit.append(_audit_entry(
        "parse_complete",
        f"Extracted {len(parsed_txns)} row(s) from file",
    ))

    categories = {c.name.value: c for c in db.execute(select(Category)).scalars().all()}
    account = _get_or_create_bank_account(stmt, parser.institution_code, db)

    audit.append(_audit_entry(
        "account_resolved",
        f"Bank account: {account.account_name or 'account #' + str(account.id)} (id={account.id})",
    ))

    count = 0
    cc_payoff_total = 0.0

    for i, ptxn in enumerate(parsed_txns, 1):
        cat_name = infer_category(ptxn.description)
        category = categories.get(cat_name.value) if cat_name else None

        is_cc = _is_cc_payment(ptxn.description or "")
        if is_cc:
            cc_payoff_total += ptxn.amount
            audit.append(_audit_entry(
                "cc_payment_detected",
                (
                    f"Row {i}: CC payoff debit of ฿{ptxn.amount:,.2f} "
                    f"on {ptxn.transaction_date.date()} — "
                    f'"{ptxn.description}" — this matches your monthly credit card payment'
                ),
                level="warn",
                index=i,
                date=str(ptxn.transaction_date.date()),
                amount=ptxn.amount,
                txn_type=ptxn.transaction_type,
                description=ptxn.description,
                category=cat_name.value if cat_name else None,
            ))
        else:
            audit.append(_audit_entry(
                "row",
                f"Row {i}: {ptxn.transaction_type} ฿{ptxn.amount:,.2f} — {ptxn.description or '(no description)'}",
                index=i,
                date=str(ptxn.transaction_date.date()),
                amount=ptxn.amount,
                txn_type=ptxn.transaction_type,
                description=ptxn.description,
                category=cat_name.value if cat_name else None,
            ))

        txn = Transaction(
            bank_account_id=account.id,
            statement_id=stmt.id,
            transaction_type=TransactionType(ptxn.transaction_type),
            amount=ptxn.amount,
            currency=ptxn.currency,
            description=ptxn.description,
            sender=ptxn.sender,
            receiver=ptxn.receiver,
            reference=ptxn.reference,
            category_id=category.id if category else None,
            transaction_date=ptxn.transaction_date,
        )
        db.add(txn)
        count += 1

        if ptxn.transaction_type == "credit":
            account.balance = float(account.balance or 0) + ptxn.amount
        elif ptxn.transaction_type == "debit":
            account.balance = float(account.balance or 0) - ptxn.amount

    if cc_payoff_total > 0:
        audit.append(_audit_entry(
            "cc_payment_summary",
            f"Total CC payoff found in this bank statement: ฿{cc_payoff_total:,.2f} — "
            "upload your credit card statement to see the individual charges that make up this total",
            level="warn",
        ))

    db.commit()
    return count


def _process_credit_card_statement(stmt: Statement, db: Session, audit: list[dict]) -> int:
    """Parse a credit card statement — reuses bank parsers, tags CC payoff debit."""
    parser = detect_bank_parser(stmt.file_path, stmt.institution_code)

    audit.append(_audit_entry(
        "parser_detected",
        f"Using {parser.__class__.__name__} (credit-card mode)",
        parser_name=parser.__class__.__name__,
        expected=(
            "Credit card statement CSV/Excel: date, description, amount columns. "
            "Charges are debits; payments/credits reduce the balance."
        ),
    ))

    parsed_txns = parser.parse(stmt.file_path)
    audit.append(_audit_entry(
        "parse_complete",
        f"Extracted {len(parsed_txns)} row(s) from credit card statement",
    ))

    categories = {c.name.value: c for c in db.execute(select(Category)).scalars().all()}

    # CC gets its own bank account entry labelled "Credit Card"
    account = _get_or_create_cc_account(stmt, parser.institution_code, db)
    audit.append(_audit_entry(
        "account_resolved",
        f"Credit card account: {account.account_name or 'cc account #' + str(account.id)} (id={account.id})",
    ))

    count = 0
    total_charges = 0.0
    total_payments = 0.0

    for i, ptxn in enumerate(parsed_txns, 1):
        cat_name = infer_category(ptxn.description)
        # Payments back to the card (credits) are flagged as CC payment category
        if ptxn.transaction_type == "credit":
            cat_name = CategoryName.CREDIT_CARD_PAYMENT
        category = categories.get(cat_name.value) if cat_name else None

        if ptxn.transaction_type == "credit":
            total_payments += ptxn.amount
            audit.append(_audit_entry(
                "cc_payment_received",
                f"Row {i}: Payment received ฿{ptxn.amount:,.2f} on {ptxn.transaction_date.date()} — "
                f'"{ptxn.description or "(payment)"}"',
                level="warn",
                index=i,
                date=str(ptxn.transaction_date.date()),
                amount=ptxn.amount,
                txn_type=ptxn.transaction_type,
                description=ptxn.description,
                category=cat_name.value if cat_name else None,
            ))
        else:
            total_charges += ptxn.amount
            audit.append(_audit_entry(
                "row",
                f"Row {i}: Charge ฿{ptxn.amount:,.2f} — {ptxn.description or '(no description)'}",
                index=i,
                date=str(ptxn.transaction_date.date()),
                amount=ptxn.amount,
                txn_type=ptxn.transaction_type,
                description=ptxn.description,
                category=cat_name.value if cat_name else None,
            ))

        txn = Transaction(
            bank_account_id=account.id,
            statement_id=stmt.id,
            transaction_type=TransactionType(ptxn.transaction_type),
            amount=ptxn.amount,
            currency=ptxn.currency,
            description=ptxn.description,
            sender=ptxn.sender,
            receiver=ptxn.receiver,
            reference=ptxn.reference,
            category_id=category.id if category else None,
            transaction_date=ptxn.transaction_date,
        )
        db.add(txn)
        count += 1

        if ptxn.transaction_type == "credit":
            account.balance = float(account.balance or 0) - ptxn.amount  # payment reduces CC balance
        elif ptxn.transaction_type == "debit":
            account.balance = float(account.balance or 0) + ptxn.amount  # charge increases CC balance

    # Summary for CC statement
    net_balance = total_charges - total_payments
    audit.append(_audit_entry(
        "cc_statement_summary",
        f"Total charges: ฿{total_charges:,.2f} | Payments received: ฿{total_payments:,.2f} | "
        f"Net balance change: ฿{net_balance:,.2f} — "
        "Cross-check: the payment received here should match the debit in your bank statement",
        level="warn" if total_payments == 0 else "info",
    ))

    db.commit()
    return count


def _get_or_create_cc_account(stmt: Statement, parser_institution_code: str, db: Session) -> BankAccount:
    """Find or create a dedicated credit-card BankAccount for this user."""
    _INSTITUTION_TO_BANK = {
        "kasikorn": BankName.KASIKORN,
        "kasikorn_pdf": BankName.KASIKORN,
        "scb": BankName.SCB,
        "scb_pdf": BankName.SCB,
        "generic": BankName.OTHER,
        "generic_pdf": BankName.OTHER,
    }

    code = stmt.institution_code or parser_institution_code
    bank_name = _INSTITUTION_TO_BANK.get(code, BankName.OTHER)
    bank = db.execute(select(Bank).where(Bank.code == bank_name)).scalars().first()

    # Look for an account whose name contains "credit card" or "cc" for this user+bank
    query = (
        select(BankAccount)
        .where(BankAccount.user_id == stmt.user_id)
    )
    if bank:
        query = query.where(BankAccount.bank_id == bank.id)
    accounts = db.execute(query).scalars().all()

    for acc in accounts:
        name = (acc.account_name or "").lower()
        if "credit" in name or " cc" in name:
            return acc

    # Auto-create a credit card account
    cc_name = f"{bank.name if bank else 'Unknown'} Credit Card"
    account = BankAccount(
        user_id=stmt.user_id,
        bank_id=bank.id if bank else None,
        account_name=cc_name,
        currency="THB",
        balance=0,
    )
    db.add(account)
    db.flush()
    logger.info(f"Auto-created CC BankAccount '{cc_name}' for user {stmt.user_id}")
    return account


def _process_brokerage_statement(stmt: Statement, db: Session, audit: list[dict]) -> int:
    """Parse brokerage statement, insert transactions, and update holdings."""
    parser = detect_brokerage_parser(stmt.file_path, stmt.institution_code)

    audit.append(_audit_entry(
        "parser_detected",
        f"Using {parser.__class__.__name__}",
        parser_name=parser.__class__.__name__,
        expected=(
            "Brokerage CSV/Excel: date, action (buy/sell/dividend/…), symbol, quantity, price, total, fees"
        ),
    ))

    parsed_txns = parser.parse(stmt.file_path)
    audit.append(_audit_entry(
        "parse_complete",
        f"Extracted {len(parsed_txns)} row(s) from brokerage statement",
    ))

    account = db.execute(
        select(BrokerageAccount).where(BrokerageAccount.user_id == stmt.user_id)
    ).scalars().first()

    if not account:
        raise ValueError("No brokerage account found for user. Create one first.")

    audit.append(_audit_entry(
        "account_resolved",
        f"Brokerage account: {account.account_name or 'account #' + str(account.id)} (id={account.id})",
    ))

    count = 0
    symbols_to_fetch = set()

    for i, ptxn in enumerate(parsed_txns, 1):
        asset = None
        if ptxn.symbol:
            asset = db.execute(
                select(Asset).where(Asset.symbol == ptxn.symbol.upper())
            ).scalars().first()

            if not asset:
                asset = Asset(symbol=ptxn.symbol.upper(), name=ptxn.symbol.upper())
                db.add(asset)
                db.flush()
                audit.append(_audit_entry(
                    "new_asset",
                    f"New asset created: {ptxn.symbol.upper()} — historical prices will be fetched",
                    level="warn",
                    symbol=ptxn.symbol.upper(),
                ))

            symbols_to_fetch.add((asset.id, ptxn.symbol.upper()))

        audit.append(_audit_entry(
            "row",
            (
                f"Row {i}: {ptxn.action.upper()} "
                + (f"{ptxn.symbol} " if ptxn.symbol else "")
                + (f"qty={ptxn.quantity} @ ${ptxn.price}" if ptxn.quantity and ptxn.price else "")
                + f" total=${ptxn.total_amount}"
                + (f" fees=${ptxn.fees}" if ptxn.fees else "")
            ),
            index=i,
            date=str(ptxn.transaction_date.date()),
            amount=ptxn.total_amount,
            action=ptxn.action,
            symbol=ptxn.symbol,
            quantity=ptxn.quantity,
            price=ptxn.price,
        ))

        portfolio_txn = PortfolioTransaction(
            brokerage_account_id=account.id,
            asset_id=asset.id if asset else None,
            statement_id=stmt.id,
            action=TradeAction(ptxn.action),
            quantity=ptxn.quantity,
            price=ptxn.price,
            total_amount=ptxn.total_amount,
            currency=ptxn.currency,
            fees=ptxn.fees,
            transaction_date=ptxn.transaction_date,
            description=ptxn.description,
        )
        db.add(portfolio_txn)
        count += 1

        if asset and ptxn.action in ("buy", "sell", "transfer_in", "transfer_out"):
            _update_holding(account.id, asset.id, ptxn, db)

    db.commit()

    for asset_id, symbol in symbols_to_fetch:
        fetch_historical_prices_for_asset.delay(asset_id, symbol)

    return count


def _update_holding(account_id: int, asset_id: int, ptxn, db: Session):
    """Update or create holding based on a transaction."""
    holding = db.execute(
        select(Holding).where(
            and_(Holding.brokerage_account_id == account_id, Holding.asset_id == asset_id)
        )
    ).scalars().first()

    qty = ptxn.quantity or 0
    price = ptxn.price or 0

    if not holding:
        holding = Holding(
            brokerage_account_id=account_id,
            asset_id=asset_id,
            quantity=0,
            avg_cost_basis=0,
            total_cost_basis=0,
        )
        db.add(holding)

    current_qty = float(holding.quantity)
    current_cost = float(holding.total_cost_basis)

    if ptxn.action in ("buy", "transfer_in"):
        new_qty = current_qty + qty
        new_cost = current_cost + (qty * price)
        holding.quantity = new_qty
        holding.total_cost_basis = new_cost
        holding.avg_cost_basis = new_cost / new_qty if new_qty > 0 else 0
    elif ptxn.action in ("sell", "transfer_out"):
        new_qty = max(current_qty - qty, 0)
        if current_qty > 0:
            cost_reduction = (qty / current_qty) * current_cost
            holding.total_cost_basis = current_cost - cost_reduction
        holding.quantity = new_qty
        holding.avg_cost_basis = float(holding.total_cost_basis) / new_qty if new_qty > 0 else 0


@celery_app.task
def update_all_asset_prices():
    """Update current prices for all tracked assets using batch download."""
    from app.services.market_data import get_current_prices_batch

    with get_sync_session() as db:
        assets = db.execute(select(Asset)).scalars().all()
        if not assets:
            return

        symbols = [a.symbol for a in assets]
        prices = get_current_prices_batch(symbols)

        for asset in assets:
            price = prices.get(asset.symbol)
            if price:
                asset.current_price = price
                asset.last_price_update = datetime.now(timezone.utc)
                logger.info(f"Updated {asset.symbol}: ${price:.2f}")

        db.commit()
        logger.info(f"Prices updated for {len(prices)}/{len(symbols)} assets")


@celery_app.task
def fetch_historical_prices_for_asset(asset_id: int, symbol: str):
    """Fetch historical prices for a specific asset."""
    start_date = date.today() - timedelta(days=365 * 2)
    prices = fetch_historical_prices_sync(symbol, start_date)

    if not prices:
        return

    with get_sync_session() as db:
        for price in prices:
            existing = db.execute(
                select(HistoricalPrice).where(
                    and_(
                        HistoricalPrice.asset_id == asset_id,
                        HistoricalPrice.price_date == price["price_date"],
                    )
                )
            ).scalars().first()

            if not existing:
                hp = HistoricalPrice(asset_id=asset_id, **price)
                db.add(hp)

        db.commit()


@celery_app.task
def fetch_missing_historical_prices():
    """Find assets missing historical data and fetch it."""
    with get_sync_session() as db:
        assets = db.execute(select(Asset)).scalars().all()
        for asset in assets:
            latest = db.execute(
                select(HistoricalPrice.price_date)
                .where(HistoricalPrice.asset_id == asset.id)
                .order_by(HistoricalPrice.price_date.desc())
                .limit(1)
            ).scalar_one_or_none()

            if not latest or (date.today() - latest).days > 1:
                fetch_historical_prices_for_asset.delay(asset.id, asset.symbol)
