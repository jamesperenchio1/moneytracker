"use client";
import { useState, useEffect, useCallback } from "react";
import {
  User as UserIcon,
  Building2,
  TrendingUp,
  FileText,
  Shield,
  Check,
  X,
  Plus,
  Trash2,
  AlertCircle,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  FolderOpen,
  RefreshCw,
  Zap,
  Eye,
  EyeOff,
} from "lucide-react";
import type {
  User,
  BankAccount,
  BrokerageAccount,
  Statement,
  Bank,
  BrokerageInfo,
} from "@/lib/types";
import {
  updateProfile,
  getBankAccounts,
  getBrokerageAccounts,
  getBanks,
  getBrokerages,
  getStatements,
  createBankAccount,
  createBrokerageAccount,
  deleteBankAccount,
  deleteBrokerageAccount,
  importFolder,
  syncBinance,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

type SettingsSection =
  | "profile"
  | "bank-accounts"
  | "brokerage-accounts"
  | "binance"
  | "watch-folder"
  | "upload-history"
  | "about";

interface Props {
  user: User;
  onUserUpdate?: (user: User) => void;
}

function SectionNav({
  active,
  onChange,
}: {
  active: SettingsSection;
  onChange: (s: SettingsSection) => void;
}) {
  const items: { id: SettingsSection; label: string; icon: React.ReactNode }[] =
    [
      { id: "profile", label: "Profile", icon: <UserIcon className="w-4 h-4" /> },
      {
        id: "bank-accounts",
        label: "Bank Accounts",
        icon: <Building2 className="w-4 h-4" />,
      },
      {
        id: "brokerage-accounts",
        label: "Brokerage Accounts",
        icon: <TrendingUp className="w-4 h-4" />,
      },
      {
        id: "binance",
        label: "Binance",
        icon: <Zap className="w-4 h-4" />,
      },
      {
        id: "watch-folder",
        label: "Watch Folder",
        icon: <FolderOpen className="w-4 h-4" />,
      },
      {
        id: "upload-history",
        label: "Upload History",
        icon: <FileText className="w-4 h-4" />,
      },
      { id: "about", label: "About", icon: <Shield className="w-4 h-4" /> },
    ];

  return (
    <div className="flex flex-wrap gap-1">
      {items.map(({ id, label, icon }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
            active === id
              ? "bg-[var(--accent)]/15 text-[var(--accent)] font-medium"
              : "text-[var(--muted)] hover:text-white hover:bg-white/5"
          }`}
        >
          {icon}
          {label}
        </button>
      ))}
    </div>
  );
}

function ProfileSection({
  user,
  onUserUpdate,
}: {
  user: User;
  onUserUpdate?: (u: User) => void;
}) {
  const [fullName, setFullName] = useState(user.full_name);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const handleSaveProfile = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const res = await updateProfile({ full_name: fullName });
      onUserUpdate?.(res.data);
      setMessage({ type: "success", text: "Profile updated successfully" });
    } catch {
      setMessage({ type: "error", text: "Failed to update profile" });
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setMessage({ type: "error", text: "Passwords do not match" });
      return;
    }
    if (newPassword.length < 4) {
      setMessage({
        type: "error",
        text: "Password must be at least 4 characters",
      });
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      await updateProfile({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage({ type: "success", text: "Password changed successfully" });
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : null;
      setMessage({ type: "error", text: detail || "Failed to change password" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {message && (
        <div
          className={`rounded-lg px-4 py-2 text-sm flex items-center gap-2 ${
            message.type === "success"
              ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
              : "bg-red-500/10 border border-red-500/20 text-red-400"
          }`}
        >
          {message.type === "success" ? (
            <Check className="w-4 h-4" />
          ) : (
            <AlertCircle className="w-4 h-4" />
          )}
          {message.text}
        </div>
      )}

      {/* Profile info */}
      <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
        <h3 className="font-medium mb-4">Profile Information</h3>
        <div className="space-y-4 max-w-md">
          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">
              Email
            </label>
            <input
              type="email"
              value={user.email}
              disabled
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-[var(--card-border)] text-sm text-[var(--muted)] cursor-not-allowed"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">
              Full Name
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">
              Member Since
            </label>
            <input
              type="text"
              value={
                user.created_at
                  ? new Date(user.created_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })
                  : "N/A"
              }
              disabled
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-[var(--card-border)] text-sm text-[var(--muted)] cursor-not-allowed"
            />
          </div>
          <button
            onClick={handleSaveProfile}
            disabled={saving || fullName === user.full_name}
            className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>

      {/* Change password */}
      <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
        <h3 className="font-medium mb-4">Change Password</h3>
        <div className="space-y-4 max-w-md">
          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">
              Current Password
            </label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">
              New Password
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">
              Confirm New Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]"
            />
          </div>
          <button
            onClick={handleChangePassword}
            disabled={saving || !currentPassword || !newPassword}
            className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {saving ? "Changing..." : "Change Password"}
          </button>
        </div>
      </div>
    </div>
  );
}

function BankAccountsSection() {
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [banks, setBanks] = useState<Bank[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newBankId, setNewBankId] = useState<number>(0);
  const [newAccountName, setNewAccountName] = useState("");
  const [newAccountNumber, setNewAccountNumber] = useState("");
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [accRes, bankRes] = await Promise.all([
        getBankAccounts(),
        getBanks(),
      ]);
      setAccounts(accRes.data);
      setBanks(bankRes.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleAdd = async () => {
    if (!newBankId) return;
    setSaving(true);
    try {
      await createBankAccount({
        bank_id: newBankId,
        account_name: newAccountName || undefined,
        account_number: newAccountNumber || undefined,
      });
      setShowAdd(false);
      setNewBankId(0);
      setNewAccountName("");
      setNewAccountNumber("");
      await loadData();
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this bank account? This cannot be undone.")) return;
    try {
      await deleteBankAccount(id);
      await loadData();
    } catch {
      // ignore
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-[var(--muted)]">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">
          Bank Accounts{" "}
          <span className="text-xs text-[var(--muted)]">
            ({accounts.length})
          </span>
        </h3>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[var(--accent)]/10 text-[var(--accent)] text-xs font-medium hover:bg-[var(--accent)]/20 transition-colors"
        >
          <Plus className="w-3 h-3" />
          Add Account
        </button>
      </div>

      {showAdd && (
        <div className="rounded-xl border border-[var(--accent)]/30 bg-[var(--card)] p-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-[var(--muted)] mb-1">
                Bank
              </label>
              <select
                value={newBankId}
                onChange={(e) => setNewBankId(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]"
              >
                <option value={0}>Select bank...</option>
                {banks.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-[var(--muted)] mb-1">
                Account Name
              </label>
              <input
                type="text"
                value={newAccountName}
                onChange={(e) => setNewAccountName(e.target.value)}
                placeholder="e.g. Main Savings"
                className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]"
              />
            </div>
            <div>
              <label className="block text-xs text-[var(--muted)] mb-1">
                Account Number
              </label>
              <input
                type="text"
                value={newAccountNumber}
                onChange={(e) => setNewAccountNumber(e.target.value)}
                placeholder="Optional"
                className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleAdd}
              disabled={saving || !newBankId}
              className="px-3 py-1.5 rounded-lg bg-[var(--accent)] text-white text-xs font-medium hover:opacity-90 disabled:opacity-50"
            >
              {saving ? "Adding..." : "Add"}
            </button>
            <button
              onClick={() => setShowAdd(false)}
              className="px-3 py-1.5 rounded-lg text-xs text-[var(--muted)] hover:text-white"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {accounts.length === 0 ? (
        <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-8 text-center text-[var(--muted)] text-sm">
          No bank accounts connected. Add one to start tracking transactions.
        </div>
      ) : (
        <div className="space-y-2">
          {accounts.map((acc) => (
            <div
              key={acc.id}
              className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-4 flex items-center justify-between"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-green-500/15 flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <div className="font-medium text-sm">
                    {acc.bank_name}
                    {acc.account_name && (
                      <span className="text-[var(--muted)] ml-2">
                        - {acc.account_name}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[var(--muted)] mt-0.5">
                    {acc.account_number && <span>#{acc.account_number}</span>}
                    <span>{acc.currency}</span>
                    <span>
                      Balance: {formatCurrency(acc.balance, acc.currency)}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleDelete(acc.id)}
                className="text-[var(--muted)] hover:text-red-400 transition-colors p-1"
                title="Delete account"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function BrokerageAccountsSection() {
  const [accounts, setAccounts] = useState<BrokerageAccount[]>([]);
  const [brokerages, setBrokerages] = useState<BrokerageInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newBrokerageId, setNewBrokerageId] = useState<number>(0);
  const [newAccountName, setNewAccountName] = useState("");
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [accRes, brkRes] = await Promise.all([
        getBrokerageAccounts(),
        getBrokerages(),
      ]);
      setAccounts(accRes.data);
      setBrokerages(brkRes.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleAdd = async () => {
    if (!newBrokerageId) return;
    setSaving(true);
    try {
      await createBrokerageAccount({
        brokerage_id: newBrokerageId,
        account_name: newAccountName || undefined,
      });
      setShowAdd(false);
      setNewBrokerageId(0);
      setNewAccountName("");
      await loadData();
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (
      !confirm(
        "Delete this brokerage account? This will remove all associated holdings and transactions. This cannot be undone."
      )
    )
      return;
    try {
      await deleteBrokerageAccount(id);
      await loadData();
    } catch {
      // ignore
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-[var(--muted)]">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">
          Brokerage Accounts{" "}
          <span className="text-xs text-[var(--muted)]">
            ({accounts.length})
          </span>
        </h3>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[var(--accent)]/10 text-[var(--accent)] text-xs font-medium hover:bg-[var(--accent)]/20 transition-colors"
        >
          <Plus className="w-3 h-3" />
          Add Account
        </button>
      </div>

      {showAdd && (
        <div className="rounded-xl border border-[var(--accent)]/30 bg-[var(--card)] p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-[var(--muted)] mb-1">
                Brokerage
              </label>
              <select
                value={newBrokerageId}
                onChange={(e) => setNewBrokerageId(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]"
              >
                <option value={0}>Select brokerage...</option>
                {brokerages.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-[var(--muted)] mb-1">
                Account Name
              </label>
              <input
                type="text"
                value={newAccountName}
                onChange={(e) => setNewAccountName(e.target.value)}
                placeholder="e.g. Webull USA - Main"
                className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm focus:outline-none focus:border-[var(--accent)]"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleAdd}
              disabled={saving || !newBrokerageId}
              className="px-3 py-1.5 rounded-lg bg-[var(--accent)] text-white text-xs font-medium hover:opacity-90 disabled:opacity-50"
            >
              {saving ? "Adding..." : "Add"}
            </button>
            <button
              onClick={() => setShowAdd(false)}
              className="px-3 py-1.5 rounded-lg text-xs text-[var(--muted)] hover:text-white"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {accounts.length === 0 ? (
        <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-8 text-center text-[var(--muted)] text-sm">
          No brokerage accounts connected. Add one to start tracking
          investments.
        </div>
      ) : (
        <div className="space-y-2">
          {accounts.map((acc) => (
            <div
              key={acc.id}
              className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-4 flex items-center justify-between"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-purple-500/15 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <div className="font-medium text-sm">
                    {acc.brokerage_name}
                    {acc.account_name && (
                      <span className="text-[var(--muted)] ml-2">
                        - {acc.account_name}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[var(--muted)] mt-0.5">
                    {acc.account_identifier && (
                      <span>ID: {acc.account_identifier}</span>
                    )}
                    <span>{acc.currency}</span>
                    <span>
                      Cash: {formatCurrency(acc.cash_balance, acc.currency)}
                    </span>
                    <span>
                      Added:{" "}
                      {new Date(acc.created_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleDelete(acc.id)}
                className="text-[var(--muted)] hover:text-red-400 transition-colors p-1"
                title="Delete account"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function UploadHistorySection() {
  const [statements, setStatements] = useState<Statement[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "bank" | "brokerage">("all");

  useEffect(() => {
    getStatements()
      .then((res) => setStatements(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-[var(--muted)]">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading...
      </div>
    );
  }

  const filtered =
    filter === "all"
      ? statements
      : statements.filter((s) => s.statement_type === filter);

  const statusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case "failed":
        return <XCircle className="w-4 h-4 text-red-400" />;
      case "processing":
        return <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-[var(--muted)]" />;
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-emerald-400 bg-emerald-500/10";
      case "failed":
        return "text-red-400 bg-red-500/10";
      case "processing":
        return "text-amber-400 bg-amber-500/10";
      default:
        return "text-[var(--muted)] bg-white/5";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">
          Upload History{" "}
          <span className="text-xs text-[var(--muted)]">
            ({filtered.length} of {statements.length})
          </span>
        </h3>
        <div className="flex gap-1">
          {(["all", "bank", "brokerage"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-lg text-xs transition-colors ${
                filter === f
                  ? "bg-[var(--accent)]/15 text-[var(--accent)] font-medium"
                  : "text-[var(--muted)] hover:text-white"
              }`}
            >
              {f === "all" ? "All" : f === "bank" ? "Banking" : "Brokerage"}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-8 text-center text-[var(--muted)] text-sm">
          No uploads found.
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((stmt) => (
            <div
              key={stmt.id}
              className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  {statusIcon(stmt.status)}
                  <div>
                    <div className="font-medium text-sm flex items-center gap-2">
                      {stmt.file_name}
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${statusColor(stmt.status)}`}
                      >
                        {stmt.status.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--muted)] mt-1">
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-white/5 text-[10px]">
                        {stmt.statement_type === "bank"
                          ? "Banking"
                          : "Brokerage"}
                      </span>
                      {stmt.institution_code && (
                        <span>
                          Parser: {stmt.institution_code}
                        </span>
                      )}
                      <span>Format: {stmt.file_type.toUpperCase()}</span>
                      <span>
                        Records: {stmt.records_processed}
                      </span>
                      <span>
                        Uploaded:{" "}
                        {new Date(stmt.uploaded_at).toLocaleString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                      {stmt.processed_at && (
                        <span>
                          Processed:{" "}
                          {new Date(stmt.processed_at).toLocaleString("en-US", {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      )}
                    </div>
                    {stmt.error_message && (
                      <div className="mt-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                        <span className="font-medium">Error:</span>{" "}
                        {stmt.error_message}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function WatchFolderSection() {
  const DEFAULT_FOLDER = "/Users/jamesperenchio/Downloads/deposit/Unlocked PDFs";
  const [folderPath, setFolderPath] = useState(DEFAULT_FOLDER);
  const [stmtType, setStmtType] = useState<"bank" | "brokerage">("bank");
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<{
    queued: number;
    skipped: number;
    files: string[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleImport = async () => {
    setImporting(true);
    setResult(null);
    setError(null);
    try {
      const res = await importFolder(folderPath, stmtType);
      setResult(res.data);
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : null;
      setError(detail || "Import failed");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
        <h3 className="font-medium mb-1">Watch Folder</h3>
        <p className="text-sm text-[var(--muted)] mb-4">
          Import all PDFs and CSV files from a local folder. Already-imported
          files are skipped automatically.
        </p>

        <div className="space-y-4 max-w-xl">
          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">
              Folder Path
            </label>
            <input
              type="text"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm font-mono focus:outline-none focus:border-[var(--accent)]"
              placeholder="/path/to/folder"
            />
          </div>

          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">
              Statement Type
            </label>
            <div className="flex gap-2">
              {(["bank", "brokerage"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setStmtType(t)}
                  className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                    stmtType === t
                      ? "bg-[var(--accent)]/15 text-[var(--accent)] font-medium"
                      : "text-[var(--muted)] hover:text-white bg-white/5"
                  }`}
                >
                  {t === "bank" ? "Banking" : "Brokerage"}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleImport}
            disabled={importing || !folderPath}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            <RefreshCw className={`w-4 h-4 ${importing ? "animate-spin" : ""}`} />
            {importing ? "Importing..." : "Import New Files"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg px-4 py-3 bg-red-500/10 border border-red-500/20 text-sm text-red-400 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {result && (
        <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-5 space-y-3">
          <div className="flex items-center gap-3 text-sm">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {result.queued} queued
            </span>
            <span className="text-[var(--muted)]">
              {result.skipped} already imported
            </span>
          </div>
          {result.files.length > 0 && (
            <ul className="space-y-1">
              {result.files.map((f) => (
                <li
                  key={f}
                  className="text-xs text-[var(--muted)] flex items-center gap-2"
                >
                  <FileText className="w-3 h-3 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function AboutSection() {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
        <h3 className="font-medium mb-4">About MoneyTracker</h3>
        <p className="text-sm text-[var(--muted)] leading-relaxed">
          MoneyTracker is a personal finance application designed for tracking
          investments, banking transactions, and spending patterns. Built for
          users in Thailand, it supports Thai banks and international brokerages.
        </p>
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-[var(--muted)]">Version:</span>{" "}
            <span className="font-medium">1.0.0</span>
          </div>
          <div>
            <span className="text-[var(--muted)]">Stack:</span>{" "}
            <span className="font-medium">Next.js + FastAPI</span>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
        <h3 className="font-medium mb-4">Supported Institutions</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm">
          <div>
            <h4 className="font-medium text-emerald-400 mb-2 flex items-center gap-2">
              <Building2 className="w-4 h-4" /> Banks (Thailand)
            </h4>
            <ul className="space-y-1.5 text-[var(--muted)]">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
                Kasikorn Bank (KBank) - CSV & PDF
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                SCB (Siam Commercial) - PDF
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                Bangkok Bank - CSV
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                Krungsri - CSV
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                Krungthai - CSV
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-orange-400" />
                TTB - CSV
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Payslips (Income) - PDF
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-gray-400" />
                Generic CSV / Excel / PDF
              </li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-purple-400 mb-2 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" /> Brokerages
            </h4>
            <ul className="space-y-1.5 text-[var(--muted)]">
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                Webull USA - CSV & PDF Statements
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                Webull Thailand - CSV
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                Dime - CSV
              </li>
              <li className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-gray-400" />
                Generic CSV / Excel
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
        <h3 className="font-medium mb-4">Data & Privacy</h3>
        <ul className="space-y-2 text-sm text-[var(--muted)]">
          <li className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            All data is stored locally on your server
          </li>
          <li className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            No data is shared with third parties
          </li>
          <li className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            Market prices fetched from Yahoo Finance (public API)
          </li>
          <li className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            Passwords are hashed with bcrypt
          </li>
        </ul>
      </div>
    </div>
  );
}

function BinanceSection({ user, onUserUpdate }: { user: User; onUserUpdate?: (u: User) => void }) {
  const [apiKey, setApiKey] = useState(user.binance_api_key ?? "");
  const [apiSecret, setApiSecret] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSaveKeys = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const res = await updateProfile({
        binance_api_key: apiKey,
        binance_api_secret: apiSecret || undefined,
      });
      onUserUpdate?.(res.data);
      setApiSecret("");
      setMessage({ type: "success", text: "Binance keys saved successfully" });
    } catch {
      setMessage({ type: "error", text: "Failed to save keys" });
    } finally {
      setSaving(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setMessage(null);
    try {
      const res = await syncBinance();
      setMessage({ type: "success", text: `Synced ${res.data.synced} assets: ${res.data.assets.join(", ")}` });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Sync failed";
      setMessage({ type: "error", text: detail });
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-6">
      {message && (
        <div className={`rounded-lg px-4 py-2 text-sm flex items-center gap-2 ${
          message.type === "success"
            ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
            : "bg-red-500/10 border border-red-500/20 text-red-400"
        }`}>
          {message.type === "success" ? <Check className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          {message.text}
        </div>
      )}

      <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
        <h3 className="font-medium mb-1 flex items-center gap-2">
          <Zap className="w-4 h-4 text-yellow-400" /> Binance Integration
        </h3>
        <p className="text-sm text-[var(--muted)] mb-4">
          Connect your Binance account to automatically sync spot, earn, and staking balances as holdings.
          Use a <strong className="text-white">read-only</strong> API key — no trading permissions needed.
        </p>

        <div className="space-y-4 max-w-md">
          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">API Key</label>
            <input
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter your Binance API key"
              className="w-full px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm font-mono focus:outline-none focus:border-[var(--accent)]"
            />
          </div>

          <div>
            <label className="block text-xs text-[var(--muted)] mb-1">
              Secret Key {user.binance_api_key && <span className="text-emerald-400">(already set — leave blank to keep)</span>}
            </label>
            <div className="relative">
              <input
                type={showSecret ? "text" : "password"}
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                placeholder={user.binance_api_key ? "Leave blank to keep existing" : "Enter your Binance secret key"}
                className="w-full px-3 py-2 pr-10 rounded-lg bg-[var(--background)] border border-[var(--card-border)] text-sm font-mono focus:outline-none focus:border-[var(--accent)]"
              />
              <button
                type="button"
                onClick={() => setShowSecret(!showSecret)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted)] hover:text-white"
              >
                {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="flex gap-2 flex-wrap">
            <button
              onClick={handleSaveKeys}
              disabled={saving || !apiKey}
              className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {saving ? "Saving..." : "Save Keys"}
            </button>

            {user.binance_api_key && (
              <button
                onClick={handleSync}
                disabled={syncing}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-yellow-500/15 text-yellow-400 text-sm font-medium hover:bg-yellow-500/25 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
                {syncing ? "Syncing..." : "Sync Now"}
              </button>
            )}
          </div>

          {user.binance_last_synced && (
            <p className="text-xs text-[var(--muted)]">
              Last synced: {new Date(user.binance_last_synced).toLocaleString("en-US", {
                month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit"
              })}
            </p>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-amber-300">
        <strong className="font-medium">Security note:</strong> Only grant Read permissions on your API key.
        Never enable trading, withdrawal, or transfer permissions. Your keys are stored on your local server only.
      </div>
    </div>
  );
}

export default function SettingsPage({ user, onUserUpdate }: Props) {
  const [section, setSection] = useState<SettingsSection>("profile");

  return (
    <div className="space-y-6">
      <SectionNav active={section} onChange={setSection} />

      {section === "profile" && (
        <ProfileSection user={user} onUserUpdate={onUserUpdate} />
      )}
      {section === "bank-accounts" && <BankAccountsSection />}
      {section === "brokerage-accounts" && <BrokerageAccountsSection />}
      {section === "binance" && <BinanceSection user={user} onUserUpdate={onUserUpdate} />}
      {section === "watch-folder" && <WatchFolderSection />}
      {section === "upload-history" && <UploadHistorySection />}
      {section === "about" && <AboutSection />}
    </div>
  );
}
