from pydantic import BaseModel
from typing import Optional
from datetime import datetime


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
