from pydantic import BaseModel
from typing import Optional
from datetime import date


class SpendingBreakdown(BaseModel):
    category: str
    total: float
    percentage: float
    transaction_count: int


class MonthlyTrend(BaseModel):
    month: str
    income: float
    expenses: float
    transfers_in: float = 0
    transfers_out: float = 0
    net: float


class NetWorthSnapshot(BaseModel):
    date: date
    total_investments: float
    total_cash: float
    net_worth: float


class RecurringPayment(BaseModel):
    description: str
    amount: float
    frequency: str  # monthly, weekly, etc.
    last_date: date
    bank_name: Optional[str] = None


class SpendingAnomaly(BaseModel):
    transaction_id: int
    amount: float
    description: Optional[str] = None
    category: Optional[str] = None
    date: date
    deviation_factor: float  # how many std devs from mean


class AnalyticsDashboard(BaseModel):
    net_worth: float
    total_investments: float
    total_cash: float
    monthly_spending: float
    monthly_income: float
    monthly_transfers_in: float = 0
    monthly_transfers_out: float = 0
    spending_breakdown: list[SpendingBreakdown]
    monthly_trends: list[MonthlyTrend]
    recurring_payments: list[RecurringPayment]
    anomalies: list[SpendingAnomaly]


class PortfolioHistoryPoint(BaseModel):
    date: date
    value: float
