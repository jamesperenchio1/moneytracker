"""Celery background tasks for data processing."""

import logging
from datetime import datetime, date, timedelta, timezone

from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.core.config import get_settings
from app.models.statement import Statement, StatementType, StatementStatus
from app.models.transaction import Transaction, TransactionType, Category
from app.models.bank import BankAccount
from app.models.brokerage import BrokerageAccount
from app.models.portfolio import Holding, PortfolioTransaction, TradeAction
from app.models.asset import Asset, HistoricalPrice
from app.parsers.detector import detect_bank_parser, detect_brokerage_parser
from app.services.categorizer import infer_category
from app.services.market_data import fetch_historical_prices_sync

logger = logging.getLogger(__name__)
settings = get_settings()

# Sync engine for Celery workers
sync_engine = create_engine(settings.DATABASE_URL_SYNC, pool_size=5)


def get_sync_session() -> Session:
    return Session(sync_engine)


@celery_app.task(bind=True, max_retries=3)
def process_statement(self, statement_id: int):
    """Process an uploaded statement file."""
    with get_sync_session() as db:
        stmt = db.get(Statement, statement_id)
        if not stmt:
            return

        stmt.status = StatementStatus.PROCESSING
        db.commit()

        try:
            if stmt.statement_type == StatementType.BANK:
                count = _process_bank_statement(stmt, db)
            elif stmt.statement_type == StatementType.BROKERAGE:
                count = _process_brokerage_statement(stmt, db)
            else:
                raise ValueError(f"Unknown statement type: {stmt.statement_type}")

            stmt.status = StatementStatus.COMPLETED
            stmt.records_processed = count
            stmt.processed_at = datetime.now(timezone.utc)
            db.commit()

        except Exception as exc:
            db.rollback()
            stmt.status = StatementStatus.FAILED
            stmt.error_message = str(exc)[:500]
            db.commit()
            raise self.retry(exc=exc, countdown=60)


def _process_bank_statement(stmt: Statement, db: Session) -> int:
    """Parse bank statement and insert transactions."""
    parser = detect_bank_parser(stmt.file_path, stmt.institution_code)
    parsed_txns = parser.parse(stmt.file_path)

    # Load category map for auto-categorization
    categories = {c.name.value: c for c in db.execute(select(Category)).scalars().all()}

    # Get or validate bank account
    account = db.execute(
        select(BankAccount).where(BankAccount.user_id == stmt.user_id)
    ).scalars().first()

    if not account:
        raise ValueError("No bank account found for user. Create one first.")

    count = 0
    for ptxn in parsed_txns:
        # Auto-categorize
        cat_name = infer_category(ptxn.description)
        category = categories.get(cat_name.value) if cat_name else None

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

        # Update account balance
        if ptxn.transaction_type == "credit":
            account.balance = float(account.balance or 0) + ptxn.amount
        elif ptxn.transaction_type == "debit":
            account.balance = float(account.balance or 0) - ptxn.amount

    db.commit()
    return count


def _process_brokerage_statement(stmt: Statement, db: Session) -> int:
    """Parse brokerage statement, insert transactions, and update holdings."""
    parser = detect_brokerage_parser(stmt.file_path, stmt.institution_code)
    parsed_txns = parser.parse(stmt.file_path)

    # Get brokerage account
    account = db.execute(
        select(BrokerageAccount).where(BrokerageAccount.user_id == stmt.user_id)
    ).scalars().first()

    if not account:
        raise ValueError("No brokerage account found for user. Create one first.")

    count = 0
    symbols_to_fetch = set()

    for ptxn in parsed_txns:
        # Get or create asset
        asset = None
        if ptxn.symbol:
            asset = db.execute(
                select(Asset).where(Asset.symbol == ptxn.symbol.upper())
            ).scalars().first()

            if not asset:
                asset = Asset(symbol=ptxn.symbol.upper(), name=ptxn.symbol.upper())
                db.add(asset)
                db.flush()

            symbols_to_fetch.add((asset.id, ptxn.symbol.upper()))

        # Create portfolio transaction
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

        # Update holdings
        if asset and ptxn.action in ("buy", "sell", "transfer_in", "transfer_out"):
            _update_holding(account.id, asset.id, ptxn, db)

    db.commit()

    # Trigger historical price fetching for new symbols
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
        # Reduce cost basis proportionally
        if current_qty > 0:
            cost_reduction = (qty / current_qty) * current_cost
            holding.total_cost_basis = current_cost - cost_reduction
        holding.quantity = new_qty
        holding.avg_cost_basis = float(holding.total_cost_basis) / new_qty if new_qty > 0 else 0


@celery_app.task
def update_all_asset_prices():
    """Update current prices for all tracked assets."""
    import yfinance as yf

    with get_sync_session() as db:
        assets = db.execute(select(Asset)).scalars().all()
        for asset in assets:
            try:
                ticker = yf.Ticker(asset.symbol)
                info = ticker.info
                price = info.get("currentPrice") or info.get("regularMarketPrice")
                if price:
                    asset.current_price = price
                    asset.last_price_update = datetime.now(timezone.utc)
            except Exception as e:
                logger.warning(f"Failed to update price for {asset.symbol}: {e}")
        db.commit()


@celery_app.task
def fetch_historical_prices_for_asset(asset_id: int, symbol: str):
    """Fetch historical prices for a specific asset."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    start_date = date.today() - timedelta(days=365 * 2)  # 2 years of history
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
            # Check if we have recent data
            latest = db.execute(
                select(HistoricalPrice.price_date)
                .where(HistoricalPrice.asset_id == asset.id)
                .order_by(HistoricalPrice.price_date.desc())
                .limit(1)
            ).scalar_one_or_none()

            if not latest or (date.today() - latest).days > 1:
                fetch_historical_prices_for_asset.delay(asset.id, asset.symbol)
