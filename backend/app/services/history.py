"""Reconstruct historical portfolio value and net worth.

Supports backwards tracking: if a user uploads statements months later,
this service will reconstruct historical values using transaction dates
and historical asset prices.
"""

from datetime import date, timedelta, datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.bank import BankAccount
from app.models.transaction import Transaction, TransactionType
from app.models.brokerage import BrokerageAccount
from app.models.portfolio import Holding, PortfolioTransaction, TradeAction
from app.models.asset import Asset, HistoricalPrice
from app.schemas.analytics import NetWorthSnapshot, PortfolioHistoryPoint


async def reconstruct_portfolio_history(
    user_id: int, months: int, db: AsyncSession
) -> list[PortfolioHistoryPoint]:
    """Reconstruct daily portfolio value over time.

    Algorithm:
    1. Get all portfolio transactions ordered by date
    2. For each day in range, compute holdings at that point
    3. Multiply holdings * historical price for that day
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    # Get all user's portfolio transactions
    user_brokerage_ids = select(BrokerageAccount.id).where(BrokerageAccount.user_id == user_id)
    txn_result = await db.execute(
        select(PortfolioTransaction)
        .where(
            and_(
                PortfolioTransaction.brokerage_account_id.in_(user_brokerage_ids),
                PortfolioTransaction.asset_id.isnot(None),
            )
        )
        .order_by(PortfolioTransaction.transaction_date)
    )
    transactions = txn_result.scalars().all()

    if not transactions:
        return []

    # Build holdings timeline: asset_id -> quantity at each transaction point
    holdings_timeline = {}  # {asset_id: [(date, cumulative_qty), ...]}

    asset_quantities = {}  # current running quantity per asset
    for txn in transactions:
        aid = txn.asset_id
        qty = float(txn.quantity or 0)

        if txn.action in (TradeAction.BUY, TradeAction.TRANSFER_IN):
            asset_quantities[aid] = asset_quantities.get(aid, 0) + qty
        elif txn.action in (TradeAction.SELL, TradeAction.TRANSFER_OUT):
            asset_quantities[aid] = asset_quantities.get(aid, 0) - qty

        txn_date = txn.transaction_date.date() if isinstance(txn.transaction_date, datetime) else txn.transaction_date
        holdings_timeline.setdefault(aid, [])
        holdings_timeline[aid].append((txn_date, asset_quantities[aid]))

    # Get all unique asset ids
    asset_ids = list(holdings_timeline.keys())

    # Fetch historical prices for all assets in range
    prices_result = await db.execute(
        select(HistoricalPrice)
        .where(
            and_(
                HistoricalPrice.asset_id.in_(asset_ids),
                HistoricalPrice.price_date >= start_date,
                HistoricalPrice.price_date <= end_date,
            )
        )
        .order_by(HistoricalPrice.price_date)
    )
    prices = prices_result.scalars().all()

    # Build price lookup: {(asset_id, date): close_price}
    price_map = {}
    for p in prices:
        price_map[(p.asset_id, p.price_date)] = float(p.close_price)

    # Generate daily portfolio values
    history = []
    current_date = start_date
    while current_date <= end_date:
        total_value = 0.0

        for aid in asset_ids:
            # Find holdings quantity at this date
            qty = 0
            for txn_date, cumulative_qty in holdings_timeline.get(aid, []):
                if txn_date <= current_date:
                    qty = cumulative_qty
                else:
                    break

            if qty > 0:
                # Find closest price
                price = price_map.get((aid, current_date))
                if not price:
                    # Look back up to 5 days for last known price
                    for lookback in range(1, 6):
                        price = price_map.get((aid, current_date - timedelta(days=lookback)))
                        if price:
                            break
                if price:
                    total_value += qty * price

        if total_value > 0:
            history.append(PortfolioHistoryPoint(date=current_date, value=round(total_value, 2)))

        current_date += timedelta(days=1)

    return history


async def reconstruct_net_worth_history(
    user_id: int, months: int, db: AsyncSession
) -> list[NetWorthSnapshot]:
    """Reconstruct historical net worth (cash + investments) over time."""
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    # Get portfolio history
    portfolio_history = await reconstruct_portfolio_history(user_id, months, db)
    portfolio_map = {p.date: p.value for p in portfolio_history}

    # Reconstruct cash balance history from transactions
    user_bank_ids = select(BankAccount.id).where(BankAccount.user_id == user_id)

    # Get current total cash
    cash_result = await db.execute(
        select(func.coalesce(func.sum(BankAccount.balance), 0)).where(BankAccount.user_id == user_id)
    )
    current_cash = float(cash_result.scalar())

    # Get all transactions in reverse to walk back balances
    txn_result = await db.execute(
        select(Transaction)
        .where(
            and_(
                Transaction.bank_account_id.in_(user_bank_ids),
                Transaction.transaction_date >= start_date,
            )
        )
        .order_by(Transaction.transaction_date.desc())
    )
    transactions = txn_result.scalars().all()

    # Build daily cash balance by walking backward
    cash_by_date = {}
    running_cash = current_cash
    cash_by_date[end_date] = running_cash

    for txn in transactions:
        txn_date = txn.transaction_date.date() if isinstance(txn.transaction_date, datetime) else txn.transaction_date
        amount = float(txn.amount)
        # Reverse the transaction to get earlier balance
        if txn.transaction_type == TransactionType.CREDIT:
            running_cash -= amount
        elif txn.transaction_type == TransactionType.DEBIT:
            running_cash += amount
        cash_by_date[txn_date] = running_cash

    # Generate monthly snapshots
    snapshots = []
    current_date = start_date
    last_cash = running_cash  # earliest known cash

    while current_date <= end_date:
        # Use closest known cash balance
        cash = cash_by_date.get(current_date, last_cash)
        last_cash = cash

        investments = portfolio_map.get(current_date, 0)

        # Only add month-end snapshots
        next_day = current_date + timedelta(days=1)
        if next_day.month != current_date.month or current_date == end_date:
            snapshots.append(
                NetWorthSnapshot(
                    date=current_date,
                    total_investments=round(investments, 2),
                    total_cash=round(cash, 2),
                    net_worth=round(cash + investments, 2),
                )
            )

        current_date += timedelta(days=1)

    return snapshots
