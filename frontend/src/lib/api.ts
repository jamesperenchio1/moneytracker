import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// Attach token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Auth
export const login = (email: string, password: string) =>
  api.post("/auth/login", { email, password });

export const register = (email: string, password: string, full_name: string) =>
  api.post("/auth/register", { email, password, full_name });

export const getMe = () => api.get("/auth/me");

export const updateProfile = (data: {
  full_name?: string;
  current_password?: string;
  new_password?: string;
}) => api.patch("/auth/me", data);

// Banks
export const getBanks = () => api.get("/banks");
export const getBankAccounts = () => api.get("/banks/accounts");
export const createBankAccount = (data: {
  bank_id: number;
  account_number?: string;
  account_name?: string;
}) => api.post("/banks/accounts", data);
export const deleteBankAccount = (id: number) =>
  api.delete(`/banks/accounts/${id}`);

// Transactions
export const getTransactions = (params?: Record<string, string | number>) =>
  api.get("/transactions", { params });
export const getCategories = () => api.get("/transactions/categories");
export const updateTransaction = (id: number, data: { category_id: number }) =>
  api.patch(`/transactions/${id}`, data);
export const suggestCategory = (description: string) =>
  api.post("/transactions/suggest-category", { description });
export const recategorizeTransactions = () =>
  api.post("/transactions/recategorize");

// Portfolio
export const getBrokerages = () => api.get("/portfolio/brokerages");
export const getBrokerageAccounts = () => api.get("/portfolio/accounts");
export const createBrokerageAccount = (data: {
  brokerage_id: number;
  account_name?: string;
}) => api.post("/portfolio/accounts", data);
export const deleteBrokerageAccount = (id: number) =>
  api.delete(`/portfolio/accounts/${id}`);
export const getHoldings = () => api.get("/portfolio/holdings");
export const getPortfolioSummary = () => api.get("/portfolio/summary");
export const getPortfolioTransactions = () => api.get("/portfolio/transactions");
export const createHolding = (data: {
  brokerage_account_id: number;
  symbol: string;
  quantity: number;
  avg_cost_basis: number;
  asset_type?: string;
  purchase_date?: string;
}) => api.post("/portfolio/holdings", data);
export const updateHolding = (id: number, data: { quantity?: number; avg_cost_basis?: number; purchase_date?: string }) =>
  api.put(`/portfolio/holdings/${id}`, data);
export const deleteHolding = (id: number) => api.delete(`/portfolio/holdings/${id}`);
export const logDividend = (data: { holding_id: number; amount: number; dividend_date: string; per_share?: number }) =>
  api.post("/portfolio/dividends", data);
export const getAssetInfo = (symbol: string) => api.get(`/portfolio/asset-info/${symbol}`);
export const syncBinance = () => api.post("/portfolio/binance/sync");

// Statements
export const uploadStatement = (formData: FormData) =>
  api.post("/statements/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
export const getStatements = () => api.get("/statements");
export const getStatement = (id: number) => api.get(`/statements/${id}`);
export const importFolder = (folder_path: string, statement_type = "bank") =>
  api.post("/statements/import-folder", { folder_path, statement_type });

// Analytics
export const getDashboard = (period?: string) =>
  api.get("/analytics/dashboard", { params: period ? { period } : {} });
export const getNetWorthHistory = (period?: string) =>
  api.get("/analytics/net-worth-history", { params: period ? { period } : {} });
export const getPortfolioHistory = (period?: string) =>
  api.get("/analytics/portfolio-history", { params: period ? { period } : {} });

export default api;
