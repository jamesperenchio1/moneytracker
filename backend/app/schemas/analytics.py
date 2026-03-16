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
    bank_cash: float = 0.0          # gross bank account balances (positive only)
    credit_card_debt: float = 0.0   # total CC outstanding (positive number = what you owe)
    monthly_spending: float
    monthly_income: float
    spending_breakdown: list[SpendingBreakdown]
    monthly_trends: list[MonthlyTrend]
    recurring_payments: list[RecurringPayment]
    anomalies: list[SpendingAnomaly]


class PortfolioHistoryPoint(BaseModel):
    date: date
    value: float
