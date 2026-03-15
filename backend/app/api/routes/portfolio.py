from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.brokerage import Brokerage, BrokerageAccount
from app.models.portfolio import Holding, PortfolioTransaction
from app.models.asset import Asset
from app.schemas.portfolio import (
    BrokerageAccountCreate,
    BrokerageAccountResponse,
    HoldingResponse,
    PortfolioSummary,
    PortfolioTransactionCreate,
    PortfolioTransactionResponse,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/brokerages")
async def list_brokerages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brokerage).order_by(Brokerage.name))
    return result.scalars().all()


@router.post("/accounts", response_model=BrokerageAccountResponse, status_code=201)
async def create_brokerage_account(
    data: BrokerageAccountCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    brokerage = await db.get(Brokerage, data.brokerage_id)
    if not brokerage:
        raise HTTPException(status_code=404, detail="Brokerage not found")

    account = BrokerageAccount(
        user_id=user.id,
        brokerage_id=data.brokerage_id,
        account_identifier=data.account_identifier,
        account_name=data.account_name,
        currency=data.currency,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)

    return BrokerageAccountResponse(
        id=account.id,
        brokerage_id=account.brokerage_id,
        brokerage_name=brokerage.name,
        brokerage_code=brokerage.code.value,
        account_identifier=account.account_identifier,
        account_name=account.account_name,
        cash_balance=float(account.cash_balance),
        currency=account.currency,
        created_at=account.created_at,
    )


@router.get("/accounts", response_model=list[BrokerageAccountResponse])
async def list_brokerage_accounts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BrokerageAccount)
        .options(selectinload(BrokerageAccount.brokerage))
        .where(BrokerageAccount.user_id == user.id)
    )
    accounts = result.scalars().all()
    return [
        BrokerageAccountResponse(
            id=a.id,
            brokerage_id=a.brokerage_id,
            brokerage_name=a.brokerage.name,
            brokerage_code=a.brokerage.code.value,
            account_identifier=a.account_identifier,
            account_name=a.account_name,
            cash_balance=float(a.cash_balance),
            currency=a.currency,
            created_at=a.created_at,
        )
        for a in accounts
    ]


@router.get("/holdings", response_model=list[HoldingResponse])
async def list_holdings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Holding)
        .join(BrokerageAccount)
        .options(
            selectinload(Holding.asset),
            selectinload(Holding.brokerage_account).selectinload(BrokerageAccount.brokerage),
        )
        .where(BrokerageAccount.user_id == user.id)
        .order_by(Holding.updated_at.desc())
    )
    holdings = result.scalars().all()

    return [
        HoldingResponse(
            id=h.id,
            brokerage_account_id=h.brokerage_account_id,
            brokerage_name=h.brokerage_account.brokerage.name,
            asset_symbol=h.asset.symbol,
            asset_name=h.asset.name,
            asset_type=h.asset.asset_type.value,
            quantity=float(h.quantity),
            avg_cost_basis=float(h.avg_cost_basis),
            total_cost_basis=float(h.total_cost_basis),
            current_price=float(h.asset.current_price) if h.asset.current_price else None,
            market_value=float(h.quantity) * float(h.asset.current_price) if h.asset.current_price else None,
            gain_loss=(float(h.quantity) * float(h.asset.current_price) - float(h.total_cost_basis))
            if h.asset.current_price
            else None,
            gain_loss_pct=(
                (float(h.quantity) * float(h.asset.current_price) - float(h.total_cost_basis))
                / float(h.total_cost_basis)
                * 100
                if h.asset.current_price and float(h.total_cost_basis) > 0
                else None
            ),
        )
        for h in holdings
    ]


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Holding)
        .join(BrokerageAccount)
        .options(
            selectinload(Holding.asset),
            selectinload(Holding.brokerage_account).selectinload(BrokerageAccount.brokerage),
        )
        .where(BrokerageAccount.user_id == user.id)
    )
    holdings = result.scalars().all()

    total_value = 0.0
    total_cost = 0.0
    platform_map = {}

    holding_responses = []
    for h in holdings:
        qty = float(h.quantity)
        cost = float(h.total_cost_basis)
        price = float(h.asset.current_price) if h.asset.current_price else 0
        mv = qty * price

        total_value += mv
        total_cost += cost

        platform = h.brokerage_account.brokerage.name
        platform_map.setdefault(platform, {"platform": platform, "value": 0, "cost": 0})
        platform_map[platform]["value"] += mv
        platform_map[platform]["cost"] += cost

        holding_responses.append(
            HoldingResponse(
                id=h.id,
                brokerage_account_id=h.brokerage_account_id,
                brokerage_name=platform,
                asset_symbol=h.asset.symbol,
                asset_name=h.asset.name,
                asset_type=h.asset.asset_type.value,
                quantity=qty,
                avg_cost_basis=float(h.avg_cost_basis),
                total_cost_basis=cost,
                current_price=price if price else None,
                market_value=mv if price else None,
                gain_loss=(mv - cost) if price else None,
                gain_loss_pct=((mv - cost) / cost * 100) if price and cost > 0 else None,
            )
        )

    return PortfolioSummary(
        total_value=total_value,
        total_cost=total_cost,
        total_gain_loss=total_value - total_cost,
        total_gain_loss_pct=((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0,
        by_platform=list(platform_map.values()),
        holdings=holding_responses,
    )


@router.get("/transactions", response_model=list[PortfolioTransactionResponse])
async def list_portfolio_transactions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    brokerage_account_id: int = None,
):
    query = (
        select(PortfolioTransaction)
        .join(BrokerageAccount)
        .options(selectinload(PortfolioTransaction.asset))
        .where(BrokerageAccount.user_id == user.id)
        .order_by(PortfolioTransaction.transaction_date.desc())
    )
    if brokerage_account_id:
        query = query.where(PortfolioTransaction.brokerage_account_id == brokerage_account_id)

    result = await db.execute(query)
    txns = result.scalars().all()

    return [
        PortfolioTransactionResponse(
            id=t.id,
            brokerage_account_id=t.brokerage_account_id,
            asset_symbol=t.asset.symbol if t.asset else None,
            action=t.action.value,
            quantity=float(t.quantity) if t.quantity else None,
            price=float(t.price) if t.price else None,
            total_amount=float(t.total_amount),
            currency=t.currency,
            fees=float(t.fees),
            transaction_date=t.transaction_date,
            description=t.description,
        )
        for t in txns
    ]
