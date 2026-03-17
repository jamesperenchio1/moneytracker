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

// Banks
export const getBanks = () => api.get("/banks/");
export const getBankAccounts = () => api.get("/banks/accounts");
export const createBankAccount = (data: {
  bank_id: number;
  account_number?: string;
  account_name?: string;
}) => api.post("/banks/accounts", data);

// Transactions
export const getTransactions = (params?: Record<string, string | number>) =>
  api.get("/transactions/", { params });
export const getCategories = () => api.get("/transactions/categories");

// Portfolio
export const getBrokerages = () => api.get("/portfolio/brokerages");
export const getBrokerageAccounts = () => api.get("/portfolio/accounts");
export const createBrokerageAccount = (data: {
  brokerage_id: number;
  account_name?: string;
}) => api.post("/portfolio/accounts", data);
export const getHoldings = () => api.get("/portfolio/holdings");
export const getPortfolioSummary = () => api.get("/portfolio/summary");
export const getPortfolioTransactions = () => api.get("/portfolio/transactions");

// Statements
export const uploadStatement = (formData: FormData) =>
  api.post("/statements/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
export const getStatements = () => api.get("/statements/");
export const getStatement = (id: number) => api.get(`/statements/${id}`);

// Analytics
export const getDashboard = (months?: number) =>
  api.get("/analytics/dashboard", { params: { months } });
export const getNetWorthHistory = (months?: number) =>
  api.get("/analytics/net-worth-history", { params: { months } });
export const getPortfolioHistory = (months?: number) =>
  api.get("/analytics/portfolio-history", { params: { months } });

export default api;
