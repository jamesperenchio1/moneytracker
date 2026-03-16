from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.brokerage import Brokerage, BrokerageAccount
from app.models.portfolio import Holding, PortfolioTransaction, TradeAction
from app.models.asset import Asset, AssetType
from app.schemas.portfolio import (
    BrokerageAccountCreate,
    BrokerageAccountResponse,
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    DividendCreate,
    AssetInfoResponse,
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


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brokerage_account(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BrokerageAccount).where(
            BrokerageAccount.id == account_id,
            BrokerageAccount.user_id == user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)


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


def _holding_response(h: Holding) -> HoldingResponse:
    qty = float(h.quantity)
    cost = float(h.total_cost_basis)
    price = float(h.asset.current_price) if h.asset.current_price else None
    mv = qty * price if price else None
    return HoldingResponse(
        id=h.id,
        brokerage_account_id=h.brokerage_account_id,
        brokerage_name=h.brokerage_account.brokerage.name,
        asset_symbol=h.asset.symbol,
        asset_name=h.asset.name,
        asset_type=h.asset.asset_type.value,
        quantity=qty,
        avg_cost_basis=float(h.avg_cost_basis),
        total_cost_basis=cost,
        purchase_date=h.purchase_date,
        current_price=price,
        market_value=mv,
        gain_loss=(mv - cost) if mv is not None else None,
        gain_loss_pct=((mv - cost) / cost * 100) if mv is not None and cost > 0 else None,
    )


@router.post("/holdings", response_model=HoldingResponse, status_code=201)
async def create_holding(
    data: HoldingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify account belongs to user
    account = await db.get(BrokerageAccount, data.brokerage_account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")

    # Find or create asset
    symbol = data.symbol.upper().strip()
    result = await db.execute(select(Asset).where(Asset.symbol == symbol))
    asset = result.scalar_one_or_none()
    if not asset:
        try:
            asset_type = AssetType(data.asset_type)
        except ValueError:
            asset_type = AssetType.STOCK
        asset = Asset(symbol=symbol, asset_type=asset_type, currency=data.currency)
        db.add(asset)
        await db.flush()

    # Check if holding already exists for this account+asset
    result = await db.execute(
        select(Holding).where(
            Holding.brokerage_account_id == data.brokerage_account_id,
            Holding.asset_id == asset.id,
        )
    )
    holding = result.scalar_one_or_none()
    if holding:
        raise HTTPException(status_code=409, detail=f"Holding for {symbol} already exists in this account. Use PUT to update.")

    holding = Holding(
        brokerage_account_id=data.brokerage_account_id,
        asset_id=asset.id,
        quantity=data.quantity,
        avg_cost_basis=data.avg_cost_basis,
        total_cost_basis=data.quantity * data.avg_cost_basis,
        purchase_date=data.purchase_date,
    )
    db.add(holding)
    await db.flush()
    await db.refresh(holding)

    # Trigger price fetch for new asset
    from app.workers.tasks import fetch_historical_prices_for_asset
    fetch_historical_prices_for_asset.delay(asset.id, asset.symbol)

    result = await db.execute(
        select(Holding)
        .options(
            selectinload(Holding.asset),
            selectinload(Holding.brokerage_account).selectinload(BrokerageAccount.brokerage),
        )
        .where(Holding.id == holding.id)
    )
    holding = result.scalar_one()
    return _holding_response(holding)


@router.put("/holdings/{holding_id}", response_model=HoldingResponse)
async def update_holding(
    holding_id: int,
    data: HoldingUpdate,
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
        .where(Holding.id == holding_id, BrokerageAccount.user_id == user.id)
    )
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    if data.quantity is not None:
        holding.quantity = data.quantity
    if data.avg_cost_basis is not None:
        holding.avg_cost_basis = data.avg_cost_basis
    if data.purchase_date is not None:
        holding.purchase_date = data.purchase_date
    holding.total_cost_basis = float(holding.quantity) * float(holding.avg_cost_basis)

    await db.flush()
    return _holding_response(holding)


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
    holding_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Holding)
        .join(BrokerageAccount)
        .where(Holding.id == holding_id, BrokerageAccount.user_id == user.id)
    )
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    await db.delete(holding)


@router.post("/dividends", status_code=201)
async def log_dividend(
    data: DividendCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Holding)
        .join(BrokerageAccount)
        .options(selectinload(Holding.asset))
        .where(Holding.id == data.holding_id, BrokerageAccount.user_id == user.id)
    )
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    from datetime import datetime, timezone
    txn = PortfolioTransaction(
        brokerage_account_id=holding.brokerage_account_id,
        asset_id=holding.asset_id,
        action=TradeAction.DIVIDEND,
        quantity=None,
        price=data.per_share,
        total_amount=data.amount,
        currency="USD",
        fees=0,
        transaction_date=datetime.combine(data.dividend_date, datetime.min.time()).replace(tzinfo=timezone.utc),
        description=f"Dividend ${data.amount:.2f}" + (f" (${data.per_share}/share)" if data.per_share else ""),
    )
    db.add(txn)
    return {"message": "Dividend logged", "amount": data.amount}


@router.get("/asset-info/{symbol}", response_model=AssetInfoResponse)
async def get_asset_info(symbol: str):
    """Fetch live stock info: insider transactions, dividend dates, analyst ratings."""
    import yfinance as yf
    import pandas as pd

    symbol = symbol.upper()
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
    except Exception:
        info = {}

    # Insider transactions
    insider_list = []
    try:
        insider_df = ticker.insider_transactions
        if insider_df is not None and not insider_df.empty:
            for _, row in insider_df.head(10).iterrows():
                insider_list.append({
                    "name": str(row.get("Insider", "")),
                    "title": str(row.get("Title", "")),
                    "transaction": str(row.get("Transaction", "")),
                    "shares": int(row.get("Shares", 0)) if pd.notna(row.get("Shares")) else 0,
                    "value": float(row.get("Value", 0)) if pd.notna(row.get("Value")) else None,
                    "date": str(row.get("Start Date", "")),
                })
    except Exception:
        pass

    # Analyst recommendations
    buy, hold, sell = 0, 0, 0
    try:
        rec = ticker.recommendations
        if rec is not None and not rec.empty:
            latest = rec.tail(1).iloc[0]
            buy = int(latest.get("strongBuy", 0) + latest.get("buy", 0))
            hold = int(latest.get("hold", 0))
            sell = int(latest.get("sell", 0) + latest.get("strongSell", 0))
    except Exception:
        pass

    # Calendar (earnings / dividend dates)
    ex_div_date = None
    next_earnings = None
    try:
        cal = ticker.calendar
        if cal:
            if "Ex-Dividend Date" in cal:
                ex_div_date = str(cal["Ex-Dividend Date"])
            if "Earnings Date" in cal and len(cal["Earnings Date"]) > 0:
                next_earnings = str(cal["Earnings Date"][0])
    except Exception:
        pass

    return AssetInfoResponse(
        symbol=symbol,
        name=info.get("longName") or info.get("shortName"),
        current_price=info.get("currentPrice") or info.get("regularMarketPrice"),
        market_cap=info.get("marketCap"),
        week_52_high=info.get("fiftyTwoWeekHigh"),
        week_52_low=info.get("fiftyTwoWeekLow"),
        dividend_yield=info.get("dividendYield"),
        ex_dividend_date=ex_div_date,
        next_earnings_date=next_earnings,
        analyst_buy=buy,
        analyst_hold=hold,
        analyst_sell=sell,
        insider_transactions=insider_list,
    )


@router.post("/binance/sync")
async def sync_binance(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync Binance spot + earn + staking balances as crypto holdings."""
    from datetime import datetime, timezone
    from app.services.binance_service import aggregate_balances
    from app.models.brokerage import BrokerageName

    if not user.binance_api_key or not user.binance_api_secret:
        raise HTTPException(status_code=400, detail="Binance API keys not configured. Go to Settings to add them.")

    # Fetch balances from Binance
    try:
        balances = aggregate_balances(user.binance_api_key, user.binance_api_secret)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Binance API error: {str(e)}")

    # Find or create "Binance Global" brokerage
    brokerage_result = await db.execute(select(Brokerage).where(Brokerage.name == "Binance Global"))
    brokerage = brokerage_result.scalar_one_or_none()
    if not brokerage:
        brokerage = Brokerage(
            name="Binance Global",
            code=BrokerageName.OTHER,
            country="Global",
            api_supported=True,
        )
        db.add(brokerage)
        await db.flush()

    # Find or create brokerage account for this user
    account_result = await db.execute(
        select(BrokerageAccount).where(
            BrokerageAccount.user_id == user.id,
            BrokerageAccount.brokerage_id == brokerage.id,
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        account = BrokerageAccount(
            user_id=user.id,
            brokerage_id=brokerage.id,
            account_name="Binance Wallet",
            currency="USD",
        )
        db.add(account)
        await db.flush()

    synced = 0
    for symbol, quantity in balances.items():
        # Find or create Asset
        asset_result = await db.execute(select(Asset).where(Asset.symbol == symbol))
        asset = asset_result.scalar_one_or_none()
        if not asset:
            asset = Asset(symbol=symbol, asset_type=AssetType.CRYPTO, currency="USD")
            db.add(asset)
            await db.flush()

        # Upsert Holding
        holding_result = await db.execute(
            select(Holding).where(
                Holding.brokerage_account_id == account.id,
                Holding.asset_id == asset.id,
            )
        )
        holding = holding_result.scalar_one_or_none()
        if holding:
            holding.quantity = quantity
            # Keep existing cost basis — user must set manually
        else:
            holding = Holding(
                brokerage_account_id=account.id,
                asset_id=asset.id,
                quantity=quantity,
                avg_cost_basis=0,
                total_cost_basis=0,
            )
            db.add(holding)
            # Trigger price fetch for new crypto asset
            try:
                from app.workers.tasks import fetch_historical_prices_for_asset
                fetch_historical_prices_for_asset.delay(asset.id, asset.symbol)
            except Exception:
                pass
        synced += 1

    # Update last synced time
    user.binance_last_synced = datetime.now(timezone.utc)
    await db.flush()

    return {"synced": synced, "assets": list(balances.keys())}
