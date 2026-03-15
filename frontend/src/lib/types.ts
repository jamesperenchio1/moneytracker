export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
}

export interface BankAccount {
  id: number;
  bank_id: number;
  bank_name: string;
  bank_code: string;
  account_number?: string;
  account_name?: string;
  balance: number;
  currency: string;
}

export interface Transaction {
  id: number;
  bank_account_id: number;
  category_id?: number;
  category_name?: string;
  transaction_type: string;
  amount: number;
  currency: string;
  description?: string;
  sender?: string;
  receiver?: string;
  bank_name?: string;
  transaction_date: string;
}

export interface Holding {
  id: number;
  brokerage_account_id: number;
  brokerage_name: string;
  asset_symbol: string;
  asset_name?: string;
  asset_type: string;
  quantity: number;
  avg_cost_basis: number;
  total_cost_basis: number;
  current_price?: number;
  market_value?: number;
  gain_loss?: number;
  gain_loss_pct?: number;
}

export interface PortfolioSummary {
  total_value: number;
  total_cost: number;
  total_gain_loss: number;
  total_gain_loss_pct: number;
  by_platform: { platform: string; value: number; cost: number }[];
  holdings: Holding[];
}

export interface SpendingBreakdown {
  category: string;
  total: number;
  percentage: number;
  transaction_count: number;
}

export interface MonthlyTrend {
  month: string;
  income: number;
  expenses: number;
  net: number;
}

export interface Dashboard {
  net_worth: number;
  total_investments: number;
  total_cash: number;
  monthly_spending: number;
  monthly_income: number;
  spending_breakdown: SpendingBreakdown[];
  monthly_trends: MonthlyTrend[];
  recurring_payments: {
    description: string;
    amount: number;
    frequency: string;
    last_date: string;
  }[];
  anomalies: {
    transaction_id: number;
    amount: number;
    description?: string;
    category?: string;
    date: string;
    deviation_factor: number;
  }[];
}

export interface Statement {
  id: number;
  statement_type: string;
  institution_code?: string;
  file_name: string;
  file_type: string;
  status: string;
  error_message?: string;
  records_processed: number;
  uploaded_at: string;
  processed_at?: string;
}

export interface NetWorthSnapshot {
  date: string;
  total_investments: number;
  total_cash: number;
  net_worth: number;
}
