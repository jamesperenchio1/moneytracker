"use client";
import { useState, useEffect, useCallback, useMemo } from "react";
import {
  Wallet,
  TrendingUp,
  Building2,
  CreditCard,
  Upload,
  BarChart3,
  LogOut,
  RefreshCw,
  X,
  Settings,
  Brain,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import {
  getDashboard,
  getPortfolioSummary,
  getTransactions,
  getPortfolioHistory,
  getNetWorthHistory,
  getBrokerageAccounts,
  recategorizeTransactions,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import type {
  Dashboard,
  PortfolioSummary,
  Transaction,
  NetWorthSnapshot,
  BrokerageAccount,
} from "@/lib/types";
import StatCard from "@/components/StatCard";
import SpendingChart from "@/components/SpendingChart";
import IncomeExpenseChart from "@/components/IncomeExpenseChart";
import NetWorthChart from "@/components/NetWorthChart";
import CategoryTreemap from "@/components/CategoryTreemap";
import PortfolioChart from "@/components/PortfolioChart";
import HoldingsTable from "@/components/HoldingsTable";
import TransactionList from "@/components/TransactionList";
import FileUpload from "@/components/FileUpload";
import PlatformBreakdown from "@/components/PlatformBreakdown";
import SettingsPage from "@/components/SettingsPage";
import TimePeriodSelector, { type Period } from "@/components/TimePeriodSelector";
import AiInsights from "@/components/AiInsights";

type Tab = "overview" | "investments" | "banking" | "upload" | "settings" | "ai";

export default function Home() {
  const { user, loading, login, register, logout } = useAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [portfolioHistory, setPortfolioHistory] = useState<
    { date: string; value: number }[]
  >([]);
  const [netWorthHistory, setNetWorthHistory] = useState<NetWorthSnapshot[]>(
    []
  );
  const [brokerageAccounts, setBrokerageAccounts] = useState<BrokerageAccount[]>([]);
  const [period, setPeriod] = useState<Period>("6M");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [recategorizing, setRecategorizing] = useState(false);
  const [recategorizeResult, setRecategorizeResult] = useState<string | null>(
    null
  );

  // Auth form state
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [authError, setAuthError] = useState("");

  const loadData = useCallback(async (p?: Period) => {
    const activePeriod = p ?? period;
    try {
      const [dashRes, portRes, txnRes, histRes, nwRes, baRes] =
        await Promise.allSettled([
          getDashboard(activePeriod),
          getPortfolioSummary(),
          getTransactions({ page_size: 200 }),
          getPortfolioHistory(activePeriod),
          getNetWorthHistory(activePeriod),
          getBrokerageAccounts(),
        ]);

      if (dashRes.status === "fulfilled") setDashboard(dashRes.value.data);
      if (portRes.status === "fulfilled") setPortfolio(portRes.value.data);
      if (txnRes.status === "fulfilled")
        setTransactions(txnRes.value.data.transactions);
      if (histRes.status === "fulfilled")
        setPortfolioHistory(histRes.value.data);
      if (nwRes.status === "fulfilled") setNetWorthHistory(nwRes.value.data);
      if (baRes.status === "fulfilled") setBrokerageAccounts(baRes.value.data);
    } catch {
      // Individual failures are handled by Promise.allSettled
    }
  }, []);

  useEffect(() => {
    if (user) loadData(period);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, period]);

  // Reset category filter on tab change
  useEffect(() => {
    setSelectedCategory(null);
  }, [tab]);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    try {
      if (authMode === "login") {
        await login(email, password);
      } else {
        await register(email, password, fullName);
      }
    } catch (err: unknown) {
      const errorDetail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : null;
      setAuthError(errorDetail || "Authentication failed");
    }
  };

  const handleCategoryClick = useCallback((categoryName: string) => {
    setSelectedCategory((prev) =>
      prev === categoryName ? null : categoryName
    );
  }, []);

  const handleRecategorize = async () => {
    setRecategorizing(true);
    setRecategorizeResult(null);
    try {
      const res = await recategorizeTransactions();
      setRecategorizeResult(res.data.message);
      // Reload data to reflect changes
      await loadData();
    } catch {
      setRecategorizeResult("Failed to recategorize transactions");
    } finally {
      setRecategorizing(false);
    }
  };

  const handleTransactionUpdate = useCallback(
    (updated: Transaction) => {
      setTransactions((prev) =>
        prev.map((t) => (t.id === updated.id ? updated : t))
      );
      // Reload dashboard to update category breakdown
      getDashboard(period).then((res) => setDashboard(res.data)).catch(() => {});
    },
    []
  );

  // Filter transactions by selected category
  const filteredTransactions = useMemo(() => {
    if (!selectedCategory) return transactions;
    return transactions.filter(
      (t) => t.category_name === selectedCategory
    );
  }, [transactions, selectedCategory]);

  // Count uncategorized
  const uncategorizedCount = useMemo(
    () => transactions.filter((t) => !t.category_name).length,
    [transactions]
  );

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-[var(--muted)]">Loading...</div>
      </div>
    );
  }

  // Auth screen
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2">MoneyTracker</h1>
            <p className="text-[var(--muted)]">
              Smart finance tracking for Thailand
            </p>
          </div>

          <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
            <div className="flex gap-2 mb-6">
              <button
                onClick={() => setAuthMode("login")}
                className={`flex-1 py-2 rounded-lg text-sm ${
                  authMode === "login"
                    ? "bg-[var(--accent)] text-white"
                    : "text-[var(--muted)]"
                }`}
              >
                Login
              </button>
              <button
                onClick={() => setAuthMode("register")}
                className={`flex-1 py-2 rounded-lg text-sm ${
                  authMode === "register"
                    ? "bg-[var(--accent)] text-white"
                    : "text-[var(--muted)]"
                }`}
              >
                Register
              </button>
            </div>

            <form onSubmit={handleAuth} className="space-y-4">
              {authMode === "register" && (
                <input
                  type="text"
                  placeholder="Full Name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]"
                  required
                />
              )}
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]"
                required
              />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]"
                required
              />
              {authError && (
                <p className="text-sm text-[var(--accent-red)]">{authError}</p>
              )}
              <button
                type="submit"
                className="w-full py-3 rounded-lg bg-[var(--accent)] text-white font-medium text-sm hover:opacity-90"
              >
                {authMode === "login" ? "Sign In" : "Create Account"}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // Main dashboard
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-[var(--card-border)] px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold">MoneyTracker</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-[var(--muted)]">
              {user.full_name}
            </span>
            <button
              onClick={logout}
              className="text-[var(--muted)] hover:text-white"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="border-b border-[var(--card-border)] px-6">
        <div className="max-w-7xl mx-auto flex gap-1">
          {[
            { id: "overview" as Tab, label: "Overview", icon: BarChart3 },
            {
              id: "investments" as Tab,
              label: "Investments",
              icon: TrendingUp,
            },
            { id: "banking" as Tab, label: "Banking", icon: Building2 },
            { id: "upload" as Tab, label: "Upload", icon: Upload },
            { id: "settings" as Tab, label: "Settings", icon: Settings },
            { id: "ai" as Tab, label: "AI Insights", icon: Brain },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm border-b-2 transition-colors ${
                tab === id
                  ? "border-[var(--accent)] text-white"
                  : "border-transparent text-[var(--muted)] hover:text-white"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-7xl mx-auto p-6">
        {tab === "overview" && (
          <div className="space-y-6">
            {/* Stat cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                title="Net Worth"
                value={formatCurrency(dashboard?.net_worth ?? 0, "THB")}
                icon={<Wallet className="w-5 h-5" />}
                gradient="var(--gradient-blue)"
                accentColor="#3b82f6"
                subtitle="Investments converted to THB"
              />
              <StatCard
                title="Total Investments"
                value={formatCurrency(dashboard?.total_investments ?? 0)}
                icon={<TrendingUp className="w-5 h-5" />}
                gradient="var(--gradient-purple)"
                accentColor="#8b5cf6"
                onClick={() => setTab("investments")}
              />
              <StatCard
                title="Bank Cash"
                value={formatCurrency(dashboard?.bank_cash ?? dashboard?.total_cash ?? 0, "THB")}
                icon={<Building2 className="w-5 h-5" />}
                gradient="var(--gradient-green)"
                accentColor="#22c55e"
                subtitle={dashboard?.credit_card_debt ? `CC Debt: ${formatCurrency(dashboard.credit_card_debt, "THB")}` : undefined}
                onClick={() => setTab("banking")}
              />
              <StatCard
                title="Monthly Spending"
                value={formatCurrency(dashboard?.monthly_spending ?? 0, "THB")}
                icon={<CreditCard className="w-5 h-5" />}
                subtitle={`Income: ${formatCurrency(dashboard?.monthly_income ?? 0, "THB")}`}
                gradient="var(--gradient-amber)"
                accentColor="#f59e0b"
                onClick={() => setTab("banking")}
              />
            </div>

            {/* Net Worth History */}
            <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-medium">Net Worth History</h3>
                <TimePeriodSelector value={period} onChange={(p) => setPeriod(p)} />
              </div>
              <NetWorthChart data={netWorthHistory} />
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
                <h3 className="font-medium mb-4">
                  Spending Breakdown
                  <span className="text-xs text-[var(--muted)] ml-2">
                    (click to filter)
                  </span>
                </h3>
                <SpendingChart
                  data={dashboard?.spending_breakdown ?? []}
                  currency="THB"
                  onCategoryClick={handleCategoryClick}
                  selectedCategory={selectedCategory}
                />
              </div>
              <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
                <h3 className="font-medium mb-4">Income vs Expenses</h3>
                <IncomeExpenseChart
                  data={dashboard?.monthly_trends ?? []}
                  currency="THB"
                />
              </div>
            </div>

            {/* Category Treemap */}
            <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
              <h3 className="font-medium mb-4">
                Spending by Category
                <span className="text-xs text-[var(--muted)] ml-2">
                  (click to filter)
                </span>
              </h3>
              <CategoryTreemap
                data={dashboard?.spending_breakdown ?? []}
                currency="THB"
                onCategoryClick={handleCategoryClick}
                selectedCategory={selectedCategory}
              />
            </div>

            {/* Recurring payments & anomalies */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
                <h3 className="font-medium mb-4">Recurring Payments</h3>
                {dashboard?.recurring_payments?.length ? (
                  <div className="space-y-2">
                    {dashboard.recurring_payments.map((rp, i) => (
                      <div
                        key={i}
                        className="flex justify-between text-sm py-2 border-b border-[var(--card-border)] last:border-0"
                      >
                        <span>{rp.description}</span>
                        <span className="text-[var(--accent-red)]">
                          {formatCurrency(rp.amount, "THB")}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[var(--muted)] text-sm">
                    No recurring payments detected yet
                  </p>
                )}
              </div>
              <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
                <h3 className="font-medium mb-4">Spending Anomalies</h3>
                {dashboard?.anomalies?.length ? (
                  <div className="space-y-2">
                    {dashboard.anomalies.map((a, i) => (
                      <div
                        key={i}
                        className="flex justify-between text-sm py-2 border-b border-[var(--card-border)] last:border-0"
                      >
                        <div>
                          <div>{a.description || "Large transaction"}</div>
                          <div className="text-xs text-[var(--muted)]">
                            {a.deviation_factor}x above average
                          </div>
                        </div>
                        <span className="text-[var(--accent-red)]">
                          {formatCurrency(a.amount, "THB")}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[var(--muted)] text-sm">
                    No anomalies detected
                  </p>
                )}
              </div>
            </div>

            {/* Category filter chip */}
            {selectedCategory && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-[var(--muted)]">
                  Filtered by:
                </span>
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-[var(--accent)]/20 text-[var(--accent)] text-sm font-medium">
                  {selectedCategory}
                  <button
                    onClick={() => setSelectedCategory(null)}
                    className="hover:text-white ml-1"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              </div>
            )}

            {/* Recent transactions */}
            <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
              <h3 className="font-medium mb-4">
                {selectedCategory
                  ? `${selectedCategory} Transactions`
                  : "Recent Transactions"}
                <span className="text-xs text-[var(--muted)] ml-2">
                  ({filteredTransactions.length}
                  {selectedCategory ? " filtered" : ""})
                </span>
              </h3>
              <TransactionList
                transactions={
                  selectedCategory
                    ? filteredTransactions
                    : transactions.slice(0, 20)
                }
                onTransactionUpdate={handleTransactionUpdate}
              />
            </div>
          </div>
        )}

        {tab === "investments" && (
          <div className="space-y-6">
            {/* Portfolio summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <StatCard
                title="Portfolio Value"
                value={formatCurrency(portfolio?.total_value ?? 0)}
                trend={portfolio?.total_gain_loss_pct ?? 0}
                gradient="var(--gradient-purple)"
                accentColor="#8b5cf6"
              />
              <StatCard
                title="Total Cost"
                value={formatCurrency(portfolio?.total_cost ?? 0)}
                gradient="var(--gradient-cyan)"
                accentColor="#06b6d4"
              />
              <StatCard
                title="Total Gain/Loss"
                value={formatCurrency(portfolio?.total_gain_loss ?? 0)}
                trend={portfolio?.total_gain_loss_pct ?? 0}
                gradient="var(--gradient-green)"
                accentColor="#22c55e"
              />
            </div>

            {/* Platform breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
                <h3 className="font-medium mb-4">Platform Breakdown</h3>
                <PlatformBreakdown
                  platforms={portfolio?.by_platform ?? []}
                  totalValue={portfolio?.total_value ?? 0}
                />
              </div>
              <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium">Portfolio Performance</h3>
                  <TimePeriodSelector value={period} onChange={(p) => setPeriod(p)} />
                </div>
                <PortfolioChart data={portfolioHistory} />
              </div>
            </div>

            {/* Holdings table */}
            <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
              <h3 className="font-medium mb-4">Holdings</h3>
              <HoldingsTable
                holdings={portfolio?.holdings ?? []}
                accounts={brokerageAccounts}
                onRefresh={loadData}
              />
            </div>
          </div>
        )}

        {tab === "banking" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <StatCard
                title="Bank Cash"
                value={formatCurrency(dashboard?.bank_cash ?? dashboard?.total_cash ?? 0, "THB")}
                icon={<Building2 className="w-5 h-5" />}
                gradient="var(--gradient-green)"
                accentColor="#22c55e"
                subtitle={dashboard?.credit_card_debt ? `CC Debt: ${formatCurrency(dashboard.credit_card_debt, "THB")} · Net: ${formatCurrency(dashboard.total_cash, "THB")}` : undefined}
              />
              <StatCard
                title="Monthly Burn Rate"
                value={formatCurrency(
                  dashboard?.monthly_spending ?? 0,
                  "THB"
                )}
                subtitle={`Income: ${formatCurrency(dashboard?.monthly_income ?? 0, "THB")} · Net: ${formatCurrency((dashboard?.monthly_income ?? 0) - (dashboard?.monthly_spending ?? 0), "THB")}`}
                gradient="var(--gradient-pink)"
                accentColor="#ec4899"
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
                <h3 className="font-medium mb-4">
                  Spending by Category
                  <span className="text-xs text-[var(--muted)] ml-2">
                    (click to filter)
                  </span>
                </h3>
                <SpendingChart
                  data={dashboard?.spending_breakdown ?? []}
                  currency="THB"
                  onCategoryClick={handleCategoryClick}
                  selectedCategory={selectedCategory}
                />
              </div>
              <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
                <h3 className="font-medium mb-4">Income vs Expenses</h3>
                <IncomeExpenseChart
                  data={dashboard?.monthly_trends ?? []}
                  currency="THB"
                />
              </div>
            </div>

            {/* Category Treemap for banking tab */}
            <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
              <h3 className="font-medium mb-4">
                Category Breakdown
                <span className="text-xs text-[var(--muted)] ml-2">
                  (click to filter)
                </span>
              </h3>
              <CategoryTreemap
                data={dashboard?.spending_breakdown ?? []}
                currency="THB"
                onCategoryClick={handleCategoryClick}
                selectedCategory={selectedCategory}
              />
            </div>

            {/* Category filter + recategorize controls */}
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-2">
                {selectedCategory && (
                  <>
                    <span className="text-sm text-[var(--muted)]">
                      Filtered by:
                    </span>
                    <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-[var(--accent)]/20 text-[var(--accent)] text-sm font-medium">
                      {selectedCategory}
                      <button
                        onClick={() => setSelectedCategory(null)}
                        className="hover:text-white ml-1"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  </>
                )}
              </div>
              <div className="flex items-center gap-3">
                {uncategorizedCount > 0 && (
                  <span className="text-xs text-[var(--muted)]">
                    {uncategorizedCount} uncategorized
                  </span>
                )}
                <button
                  onClick={handleRecategorize}
                  disabled={recategorizing}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--accent)]/10 text-[var(--accent)] text-xs font-medium hover:bg-[var(--accent)]/20 transition-colors disabled:opacity-50"
                >
                  <RefreshCw
                    className={`w-3 h-3 ${recategorizing ? "animate-spin" : ""}`}
                  />
                  Re-categorize Uncategorized
                </button>
              </div>
            </div>

            {recategorizeResult && (
              <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-2 text-sm text-emerald-400">
                {recategorizeResult}
              </div>
            )}

            <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
              <h3 className="font-medium mb-4">
                {selectedCategory
                  ? `${selectedCategory} Transactions`
                  : "All Transactions"}
                <span className="text-xs text-[var(--muted)] ml-2">
                  ({filteredTransactions.length}
                  {selectedCategory ? " filtered" : ""})
                </span>
              </h3>
              <TransactionList
                transactions={filteredTransactions}
                onTransactionUpdate={handleTransactionUpdate}
              />
            </div>
          </div>
        )}

        {tab === "upload" && (
          <div className="max-w-2xl mx-auto space-y-6">
            <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
              <h3 className="font-medium mb-4">Upload Statements</h3>
              <p className="text-sm text-[var(--muted)] mb-4">
                Upload bank or brokerage statements. Supported formats: CSV,
                Excel (.xlsx), PDF. The system will auto-detect the institution
                and parse transactions.
              </p>
              <FileUpload onUploadComplete={loadData} />
            </div>

            <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
              <h3 className="font-medium mb-4">Supported Institutions</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <h4 className="font-medium text-[var(--accent)] mb-2">
                    Banks (Thailand)
                  </h4>
                  <ul className="space-y-1 text-[var(--muted)]">
                    <li>Kasikorn Bank (KBank)</li>
                    <li>SCB (Siam Commercial)</li>
                    <li>Bangkok Bank</li>
                    <li>Krungsri</li>
                    <li>Krungthai</li>
                    <li>TTB</li>
                    <li>Payslips (income)</li>
                    <li>Generic CSV/Excel/PDF</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-[var(--accent)] mb-2">
                    Brokerages
                  </h4>
                  <ul className="space-y-1 text-[var(--muted)]">
                    <li>Webull USA (CSV & PDF)</li>
                    <li>Webull Thailand</li>
                    <li>Dime</li>
                    <li>Generic CSV/Excel</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === "settings" && (
          <div className="max-w-4xl mx-auto">
            <SettingsPage user={user} onUserUpdate={(u) => window.location.reload()} />
          </div>
        )}

        {tab === "ai" && (
          <div className="max-w-4xl mx-auto">
            <AiInsights />
          </div>
        )}
      </main>
    </div>
  );
}
