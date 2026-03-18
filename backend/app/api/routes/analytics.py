from datetime import datetime, date, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.bank import BankAccount
from app.models.transaction import Transaction, Category, TransactionType, CategoryName
from app.models.brokerage import BrokerageAccount
from app.models.portfolio import Holding
from app.models.asset import Asset, HistoricalPrice
from app.schemas.analytics import (
    AnalyticsDashboard,
    SpendingBreakdown,
    MonthlyTrend,
    NetWorthSnapshot,
    RecurringPayment,
    SpendingAnomaly,
    PortfolioHistoryPoint,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Category names that represent money movement but are NOT real income / expenses.
_TRANSFER_NAMES = [
    CategoryName.TRANSFERS,
    CategoryName.TRANSFER_IN,
    CategoryName.TRANSFER_OUT,
]


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    months: int = Query(6, ge=1, le=24),
):
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    lookback = now - timedelta(days=months * 30)

    user_accounts = select(BankAccount.id).where(BankAccount.user_id == user.id)

    # IDs of transfer categories — used to exclude them from income/expenses
    transfer_ids_result = await db.execute(
        select(Category.id).where(Category.name.in_(_TRANSFER_NAMES))
    )
    transfer_ids = [r for r, in transfer_ids_result.all()]

    # ------------------------------------------------------------------ #
    # Total cash (sum of bank account balances)
    # ------------------------------------------------------------------ #
    cash_result = await db.execute(
        select(func.coalesce(func.sum(BankAccount.balance), 0)).where(
            BankAccount.user_id == user.id
        )
    )
    total_cash = float(cash_result.scalar())

    # ------------------------------------------------------------------ #
    # Total investments (holdings * current price)
    # ------------------------------------------------------------------ #
    holdings_result = await db.execute(
        select(Holding)
        .join(BrokerageAccount)
        .options(selectinload(Holding.asset))
        .where(BrokerageAccount.user_id == user.id)
    )
    holdings = holdings_result.scalars().all()
    total_investments = sum(
        float(h.quantity) * float(h.asset.current_price or 0) for h in holdings
    )

    # ------------------------------------------------------------------ #
    # Monthly spending — real expenses only (exclude transfers & CC payments
    # since CC charges are already counted in the CC statement)
    # ------------------------------------------------------------------ #
    spending_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.transaction_date >= start_of_month,
                # Exclude transfers out — they are not true spending
                Transaction.category_id.notin_(transfer_ids) if transfer_ids
                else True,
            )
        )
    )
    monthly_spending = float(spending_result.scalar())

    # ------------------------------------------------------------------ #
    # Monthly income — genuine income only (salary, dividends, etc.)
    # Excludes transfer-in so money sent by a friend doesn't inflate income.
    # ------------------------------------------------------------------ #
    income_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_type == TransactionType.CREDIT,
                Transaction.transaction_date >= start_of_month,
                Transaction.category_id.notin_(transfer_ids) if transfer_ids
                else True,
            )
        )
    )
    monthly_income = float(income_result.scalar())

    # ------------------------------------------------------------------ #
    # Monthly transfers in/out (this month)
    # ------------------------------------------------------------------ #
    transfers_in_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_type == TransactionType.CREDIT,
                Transaction.transaction_date >= start_of_month,
                Transaction.category_id.in_(transfer_ids) if transfer_ids
                else False,
            )
        )
    )
    monthly_transfers_in = float(transfers_in_result.scalar())

    transfers_out_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.transaction_date >= start_of_month,
                Transaction.category_id.in_(transfer_ids) if transfer_ids
                else False,
            )
        )
    )
    monthly_transfers_out = float(transfers_out_result.scalar())

    # ------------------------------------------------------------------ #
    # Spending breakdown by category (current month, real expenses only)
    # ------------------------------------------------------------------ #
    breakdown_result = await db.execute(
        select(
            Category.display_name,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("cnt"),
        )
        .join(Category, Transaction.category_id == Category.id, isouter=True)
        .where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.transaction_date >= start_of_month,
                Transaction.category_id.notin_(transfer_ids) if transfer_ids
                else True,
            )
        )
        .group_by(Category.display_name)
    )
    breakdowns = breakdown_result.all()
    spending_breakdown = [
        SpendingBreakdown(
            category=cat_name or "Uncategorized",
            total=float(total),
            percentage=(float(total) / monthly_spending * 100)
            if monthly_spending > 0
            else 0,
            transaction_count=cnt,
        )
        for cat_name, total, cnt in breakdowns
    ]

    # ------------------------------------------------------------------ #
    # Monthly trends — one row per month, columns split by flow type
    # ------------------------------------------------------------------ #
    # Using CASE WHEN so we get a single pass with four sums per month.
    is_transfer = (
        Transaction.category_id.in_(transfer_ids) if transfer_ids else False
    )
    is_not_transfer = (
        Transaction.category_id.notin_(transfer_ids) if transfer_ids else True
    )

    trends_result = await db.execute(
        select(
            func.to_char(Transaction.transaction_date, "YYYY-MM").label("month"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.transaction_type == TransactionType.CREDIT,
                                is_not_transfer,
                            ),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("income"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.transaction_type == TransactionType.DEBIT,
                                is_not_transfer,
                            ),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("expenses"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.transaction_type == TransactionType.CREDIT,
                                is_transfer,
                            ),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("transfers_in"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.transaction_type == TransactionType.DEBIT,
                                is_transfer,
                            ),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("transfers_out"),
        )
        .where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_date >= lookback,
            )
        )
        .group_by("month")
        .order_by("month")
    )

    monthly_trends = [
        MonthlyTrend(
            month=row.month,
            income=float(row.income),
            expenses=float(row.expenses),
            transfers_in=float(row.transfers_in),
            transfers_out=float(row.transfers_out),
            net=float(row.income) - float(row.expenses),
        )
        for row in trends_result.all()
    ]

    # ------------------------------------------------------------------ #
    # Recurring payments (debits, exclude transfers, ≥2 occurrences)
    # ------------------------------------------------------------------ #
    recurring_result = await db.execute(
        select(
            Transaction.description,
            func.avg(Transaction.amount).label("avg_amount"),
            func.count(Transaction.id).label("cnt"),
            func.max(Transaction.transaction_date).label("last_date"),
        )
        .join(BankAccount, Transaction.bank_account_id == BankAccount.id)
        .where(
            and_(
                BankAccount.user_id == user.id,
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.description.isnot(None),
                Transaction.transaction_date >= lookback,
                Transaction.category_id.notin_(transfer_ids) if transfer_ids
                else True,
            )
        )
        .group_by(Transaction.description)
        .having(func.count(Transaction.id) >= 2)
        .order_by(func.avg(Transaction.amount).desc())
        .limit(20)
    )
    recurring = [
        RecurringPayment(
            description=r.description or "Unknown",
            amount=float(r.avg_amount),
            frequency="monthly",
            last_date=r.last_date.date()
            if hasattr(r.last_date, "date")
            else r.last_date,
        )
        for r in recurring_result.all()
    ]

    # ------------------------------------------------------------------ #
    # Spending anomalies (expenses > 2 std devs from mean, no transfers)
    # ------------------------------------------------------------------ #
    stats_result = await db.execute(
        select(
            func.avg(Transaction.amount).label("mean"),
            func.stddev(Transaction.amount).label("stddev"),
        ).where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.transaction_date >= lookback,
                Transaction.category_id.notin_(transfer_ids) if transfer_ids
                else True,
            )
        )
    )
    stats = stats_result.one_or_none()
    anomalies = []
    if stats and stats.mean and stats.stddev and float(stats.stddev) > 0:
        mean_val = float(stats.mean)
        std_val = float(stats.stddev)
        threshold = mean_val + 2 * std_val

        anomaly_result = await db.execute(
            select(Transaction)
            .options(selectinload(Transaction.category))
            .where(
                and_(
                    Transaction.bank_account_id.in_(user_accounts),
                    Transaction.transaction_type == TransactionType.DEBIT,
                    Transaction.amount > threshold,
                    Transaction.transaction_date >= lookback,
                    Transaction.category_id.notin_(transfer_ids) if transfer_ids
                    else True,
                )
            )
            .order_by(Transaction.amount.desc())
            .limit(10)
        )
        for t in anomaly_result.scalars().all():
            anomalies.append(
                SpendingAnomaly(
                    transaction_id=t.id,
                    amount=float(t.amount),
                    description=t.description,
                    category=t.category.display_name if t.category else None,
                    date=t.transaction_date.date()
                    if hasattr(t.transaction_date, "date")
                    else t.transaction_date,
                    deviation_factor=round(
                        (float(t.amount) - mean_val) / std_val, 2
                    ),
                )
            )

    return AnalyticsDashboard(
        net_worth=total_cash + total_investments,
        total_investments=total_investments,
        total_cash=total_cash,
        monthly_spending=monthly_spending,
        monthly_income=monthly_income,
        monthly_transfers_in=monthly_transfers_in,
        monthly_transfers_out=monthly_transfers_out,
        spending_breakdown=spending_breakdown,
        monthly_trends=monthly_trends,
        recurring_payments=recurring,
        anomalies=anomalies,
    )


@router.get("/net-worth-history", response_model=list[NetWorthSnapshot])
async def get_net_worth_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    months: int = Query(12, ge=1, le=60),
):
    """Reconstruct historical net worth using transaction data and historical prices."""
    from app.services.history import reconstruct_net_worth_history

    return await reconstruct_net_worth_history(user.id, months, db)


@router.get("/portfolio-history", response_model=list[PortfolioHistoryPoint])
async def get_portfolio_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    months: int = Query(12, ge=1, le=60),
):
    """Reconstruct historical portfolio value using holdings and historical prices."""
    from app.services.history import reconstruct_portfolio_history

    return await reconstruct_portfolio_history(user.id, months, db)
