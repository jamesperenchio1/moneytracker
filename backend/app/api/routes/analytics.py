from datetime import datetime, date, timedelta, timezone
from typing import Optional, AsyncIterator
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.bank import BankAccount
from app.models.transaction import Transaction, Category, TransactionType
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


def _period_to_timedelta(period: str) -> timedelta:
    """Convert period string (1D/1W/1M/3M/6M/1Y) to timedelta."""
    mapping = {
        "1D": timedelta(days=1),
        "1W": timedelta(weeks=1),
        "1M": timedelta(days=30),
        "3M": timedelta(days=90),
        "6M": timedelta(days=180),
        "1Y": timedelta(days=365),
    }
    return mapping.get(period.upper(), timedelta(days=180))


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    months: int = Query(6, ge=1, le=24),
    period: Optional[str] = Query(None),
):
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period:
        lookback = now - _period_to_timedelta(period)
    else:
        lookback = now - timedelta(days=months * 30)

    user_accounts = select(BankAccount.id).where(BankAccount.user_id == user.id)

    # Total cash (sum of bank balances — includes negative CC balances)
    cash_result = await db.execute(
        select(func.coalesce(func.sum(BankAccount.balance), 0)).where(BankAccount.user_id == user.id)
    )
    total_cash = float(cash_result.scalar())

    # Gross bank cash (positive balances) and CC debt (negative balances)
    bank_cash_result = await db.execute(
        select(func.coalesce(func.sum(BankAccount.balance), 0)).where(
            BankAccount.user_id == user.id,
            BankAccount.balance > 0,
        )
    )
    bank_cash = float(bank_cash_result.scalar())
    cc_debt_result = await db.execute(
        select(func.coalesce(func.sum(BankAccount.balance), 0)).where(
            BankAccount.user_id == user.id,
            BankAccount.balance < 0,
        )
    )
    credit_card_debt = abs(float(cc_debt_result.scalar()))

    # Total investments (sum of holdings * current price, in USD)
    holdings_result = await db.execute(
        select(Holding)
        .join(BrokerageAccount)
        .options(selectinload(Holding.asset))
        .where(BrokerageAccount.user_id == user.id)
    )
    holdings = holdings_result.scalars().all()
    total_investments_usd = sum(
        float(h.quantity) * float(h.asset.current_price or 0) for h in holdings
    )
    # Convert USD → THB for net worth (use cached rate, fall back to 34)
    try:
        import yfinance as yf
        fx = yf.download("THBUSD=X", period="2d", progress=False, auto_adjust=True)
        thb_usd = float(fx["Close"].iloc[-1].iloc[0]) if not fx.empty else (1 / 34.0)
        usd_thb = 1 / thb_usd if thb_usd else 34.0
    except Exception:
        usd_thb = 34.0
    total_investments = total_investments_usd  # kept in USD for display
    total_investments_thb = total_investments_usd * usd_thb

    # Subquery for "transfer" category to exclude inter-account transfers from burn rate
    transfer_category_sq = select(Category.id).where(
        func.lower(Category.name).contains("transfer")
    ).scalar_subquery()

    # Monthly spending (current month debits, excluding transfers like CC payments)
    spending_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.transaction_date >= start_of_month,
                ~Transaction.category_id.in_(transfer_category_sq),
            )
        )
    )
    monthly_spending = float(spending_result.scalar())

    # Monthly income (current month credits, excluding CC payment received on CC account)
    income_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_type == TransactionType.CREDIT,
                Transaction.transaction_date >= start_of_month,
                ~Transaction.category_id.in_(transfer_category_sq),
            )
        )
    )
    monthly_income = float(income_result.scalar())

    # Spending breakdown by category (current month)
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
            )
        )
        .group_by(Category.display_name)
    )
    breakdowns = breakdown_result.all()
    spending_breakdown = []
    for cat_name, total, cnt in breakdowns:
        spending_breakdown.append(
            SpendingBreakdown(
                category=cat_name or "Uncategorized",
                total=float(total),
                percentage=(float(total) / monthly_spending * 100) if monthly_spending > 0 else 0,
                transaction_count=cnt,
            )
        )

    # Monthly trends
    trends_result = await db.execute(
        select(
            func.to_char(Transaction.transaction_date, "YYYY-MM").label("month"),
            Transaction.transaction_type,
            func.sum(Transaction.amount).label("total"),
        )
        .where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_date >= lookback,
            )
        )
        .group_by("month", Transaction.transaction_type)
        .order_by("month")
    )
    trends_raw = trends_result.all()
    month_data = {}
    for month, txn_type, total in trends_raw:
        month_data.setdefault(month, {"income": 0, "expenses": 0})
        if txn_type == TransactionType.CREDIT:
            month_data[month]["income"] = float(total)
        elif txn_type == TransactionType.DEBIT:
            month_data[month]["expenses"] = float(total)

    monthly_trends = [
        MonthlyTrend(month=m, income=d["income"], expenses=d["expenses"], net=d["income"] - d["expenses"])
        for m, d in sorted(month_data.items())
    ]

    # Recurring payments detection (transactions with similar description appearing 2+ times)
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
            last_date=r.last_date.date() if hasattr(r.last_date, "date") else r.last_date,
        )
        for r in recurring_result.all()
    ]

    # Anomaly detection (transactions > 2 std dev from mean)
    stats_result = await db.execute(
        select(
            func.avg(Transaction.amount).label("mean"),
            func.stddev(Transaction.amount).label("stddev"),
        ).where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.transaction_date >= lookback,
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
                    date=t.transaction_date.date() if hasattr(t.transaction_date, "date") else t.transaction_date,
                    deviation_factor=round((float(t.amount) - mean_val) / std_val, 2),
                )
            )

    return AnalyticsDashboard(
        net_worth=total_cash + total_investments_thb,
        total_investments=total_investments,
        total_cash=total_cash,
        bank_cash=bank_cash,
        credit_card_debt=credit_card_debt,
        monthly_spending=monthly_spending,
        monthly_income=monthly_income,
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
    period: Optional[str] = Query(None),
):
    """Reconstruct historical net worth using transaction data and historical prices."""
    from app.services.history import reconstruct_net_worth_history

    if period:
        td = _period_to_timedelta(period)
        months = max(1, int(td.days / 30)) or 1
    return await reconstruct_net_worth_history(user.id, months, db)


@router.get("/portfolio-history", response_model=list[PortfolioHistoryPoint])
async def get_portfolio_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    months: int = Query(12, ge=1, le=60),
    period: Optional[str] = Query(None),
):
    """Reconstruct historical portfolio value using holdings and historical prices."""
    from app.services.history import reconstruct_portfolio_history

    if period:
        td = _period_to_timedelta(period)
        months = max(1, int(td.days / 30)) or 1
    return await reconstruct_portfolio_history(user.id, months, db)


@router.get("/ai-insights")
async def get_ai_insights(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    months: int = Query(3, ge=1, le=12),
):
    """Stream AI-powered spending analysis using Claude."""
    import os
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")

    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=months * 30)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    user_accounts = select(BankAccount.id).where(BankAccount.user_id == user.id)

    # Gather spending data
    # 1. Monthly spending by category (last N months)
    cat_result = await db.execute(
        select(
            func.to_char(Transaction.transaction_date, "YYYY-MM").label("month"),
            Category.display_name,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("cnt"),
        )
        .join(Category, Transaction.category_id == Category.id, isouter=True)
        .join(BankAccount, Transaction.bank_account_id == BankAccount.id)
        .where(
            and_(
                BankAccount.user_id == user.id,
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.transaction_date >= lookback,
            )
        )
        .group_by("month", Category.display_name)
        .order_by("month", func.sum(Transaction.amount).desc())
    )
    cat_rows = cat_result.all()

    # 2. Top recurring descriptions
    recurring_result = await db.execute(
        select(
            Transaction.description,
            func.avg(Transaction.amount).label("avg_amount"),
            func.count(Transaction.id).label("cnt"),
            Category.display_name.label("category"),
        )
        .join(Category, Transaction.category_id == Category.id, isouter=True)
        .join(BankAccount, Transaction.bank_account_id == BankAccount.id)
        .where(
            and_(
                BankAccount.user_id == user.id,
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.transaction_date >= lookback,
                Transaction.description.isnot(None),
            )
        )
        .group_by(Transaction.description, Category.display_name)
        .having(func.count(Transaction.id) >= 2)
        .order_by(func.avg(Transaction.amount).desc())
        .limit(30)
    )
    recurring_rows = recurring_result.all()

    # 3. Bank balances
    accounts_result = await db.execute(
        select(BankAccount).where(BankAccount.user_id == user.id)
    )
    accounts = accounts_result.scalars().all()

    # 4. Holdings
    holdings_result = await db.execute(
        select(Holding)
        .join(BrokerageAccount)
        .options(selectinload(Holding.asset))
        .where(BrokerageAccount.user_id == user.id)
    )
    holdings = holdings_result.scalars().all()

    # 5. Current month spending vs last month
    prev_month_start = (start_of_month - timedelta(days=1)).replace(day=1)
    curr_spend_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.transaction_date >= start_of_month,
            )
        )
    )
    prev_spend_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.bank_account_id.in_(user_accounts),
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.transaction_date >= prev_month_start,
                Transaction.transaction_date < start_of_month,
            )
        )
    )
    curr_month_spend = float(curr_spend_result.scalar())
    prev_month_spend = float(prev_spend_result.scalar())

    # Build the context for Claude
    # Category breakdown by month
    month_cat_data: dict = {}
    for month, cat_name, total, cnt in cat_rows:
        month_cat_data.setdefault(month, []).append({
            "category": cat_name or "Uncategorized",
            "amount": round(float(total), 2),
            "transactions": cnt,
        })

    recurring_list = [
        {
            "description": r.description,
            "avg_amount_thb": round(float(r.avg_amount), 2),
            "occurrences": r.cnt,
            "category": r.category or "Uncategorized",
        }
        for r in recurring_rows
    ]

    account_balances = [
        {"name": a.account_name, "balance_thb": round(float(a.balance), 2)}
        for a in accounts
    ]

    holdings_list = [
        {
            "symbol": h.asset.symbol if h.asset else "?",
            "quantity": float(h.quantity),
            "avg_cost": round(float(h.avg_cost_basis), 4),
            "current_price": round(float(h.asset.current_price or 0), 4) if h.asset else 0,
        }
        for h in holdings
    ]

    context_data = {
        "analysis_period_months": months,
        "bank_accounts": account_balances,
        "current_month_spending_thb": round(curr_month_spend, 2),
        "previous_month_spending_thb": round(prev_month_spend, 2),
        "monthly_spending_by_category": month_cat_data,
        "recurring_transactions": recurring_list,
        "investments": holdings_list,
    }

    prompt = f"""You are a personal finance advisor analyzing a user's financial data from a MoneyTracker app.
The user lives in Thailand and transactions are in Thai Baht (THB) unless noted.
Exchange rate reference: ~33-35 THB per USD.

Here is their financial data for the past {months} months:
{json.dumps(context_data, indent=2)}

Please provide a comprehensive analysis covering:

1. **Spending Patterns** — What are the main spending categories? Any notable trends month-over-month?

2. **Subscriptions & Recurring Charges** — Identify likely subscriptions or recurring payments. Flag any that seem high or unused.

3. **Savings Opportunities** — Where could they cut back? What specific changes would have the biggest impact?

4. **Income vs Expenses** — Comment on the balance between income and spending. Are they living within their means?

5. **Investment Health** — Review their investment portfolio. Any concentration risks or suggestions?

6. **Action Items** — Give 3-5 concrete, prioritized actions they should take this month.

Be specific with numbers (in THB). Keep it practical and actionable. Use markdown formatting with headers and bullet points."""

    async def stream_response() -> AsyncIterator[bytes]:
        client = anthropic.Anthropic(api_key=api_key)
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                # Send as SSE
                yield f"data: {json.dumps({'text': text})}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
