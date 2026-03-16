from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class BrokerageAccountCreate(BaseModel):
    brokerage_id: int
    account_identifier: Optional[str] = None
    account_name: Optional[str] = None
    currency: str = "USD"


class BrokerageAccountResponse(BaseModel):
    id: int
    brokerage_id: int
    brokerage_name: Optional[str] = None
    brokerage_code: Optional[str] = None
    account_identifier: Optional[str] = None
    account_name: Optional[str] = None
    cash_balance: float
    currency: str
    created_at: datetime

    model_config = {"from_attributes": True}


class HoldingResponse(BaseModel):
    id: int
    brokerage_account_id: int
    brokerage_name: Optional[str] = None
    asset_symbol: str
    asset_name: Optional[str] = None
    asset_type: str
    quantity: float
    avg_cost_basis: float
    total_cost_basis: float
    purchase_date: Optional[date] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    gain_loss: Optional[float] = None
    gain_loss_pct: Optional[float] = None

    model_config = {"from_attributes": True}


class PortfolioTransactionCreate(BaseModel):
    brokerage_account_id: int
    asset_symbol: Optional[str] = None
    action: str
    quantity: Optional[float] = None
    price: Optional[float] = None
    total_amount: float
    currency: str = "USD"
    fees: float = 0
    transaction_date: datetime
    description: Optional[str] = None


class PortfolioTransactionResponse(BaseModel):
    id: int
    brokerage_account_id: int
    asset_symbol: Optional[str] = None
    action: str
    quantity: Optional[float] = None
    price: Optional[float] = None
    total_amount: float
    currency: str
    fees: float
    transaction_date: datetime
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    total_value: float
    total_cost: float
    total_gain_loss: float
    total_gain_loss_pct: float
    by_platform: list[dict]
    holdings: list[HoldingResponse]


class HoldingCreate(BaseModel):
    brokerage_account_id: int
    symbol: str
    quantity: float
    avg_cost_basis: float
    asset_type: str = "stock"
    currency: str = "USD"
    purchase_date: Optional[date] = None


class HoldingUpdate(BaseModel):
    quantity: Optional[float] = None
    avg_cost_basis: Optional[float] = None
    purchase_date: Optional[date] = None


class DividendCreate(BaseModel):
    holding_id: int
    amount: float
    dividend_date: date
    per_share: Optional[float] = None


class AssetInfoResponse(BaseModel):
    symbol: str
    name: Optional[str] = None
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    dividend_yield: Optional[float] = None
    ex_dividend_date: Optional[str] = None
    next_earnings_date: Optional[str] = None
    analyst_buy: int = 0
    analyst_hold: int = 0
    analyst_sell: int = 0
    insider_transactions: list[dict] = []


class AssetResponse(BaseModel):
    id: int
    symbol: str
    name: Optional[str] = None
    asset_type: str
    exchange: Optional[str] = None
    currency: str
    current_price: Optional[float] = None
    last_price_update: Optional[datetime] = None

    model_config = {"from_attributes": True}
