"use client";
import { useRef, useState } from "react";
import {
  Upload,
  Building2,
  CreditCard,
  TrendingUp,
  Loader,
} from "lucide-react";
import { uploadStatement } from "@/lib/api";
import AuditTrail from "./AuditTrail";

interface UploadPanelProps {
  title: string;
  subtitle: string;
  statementType: "bank" | "credit_card" | "brokerage";
  icon: React.ReactNode;
  supportedInstitutions: string[];
  onUploadComplete?: () => void;
}

function UploadPanel({
  title,
  subtitle,
  statementType,
  icon,
  supportedInstitutions,
  onUploadComplete,
}: UploadPanelProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [pendingIds, setPendingIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("statement_type", statementType);

    try {
      const res = await uploadStatement(formData);
      const stmtId: number = res.data.id;
      setPendingIds((ids) => [...ids, stmtId]);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail ?? "Upload failed"
          : "Upload failed";
      setError(msg);
    } finally {
      setUploading(false);
      // Reset file input so the same file can be re-uploaded
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div
      data-testid={`upload-panel-${statementType}`}
      className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-5 space-y-4"
    >
      {/* Panel header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-[var(--accent)]/10 text-[var(--accent)]">
          {icon}
        </div>
        <div>
          <h4 className="font-medium text-sm">{title}</h4>
          <p className="text-xs text-[var(--muted)]">{subtitle}</p>
        </div>
      </div>

      {/* Supported institutions */}
      <div className="flex flex-wrap gap-1">
        {supportedInstitutions.map((inst) => (
          <span
            key={inst}
            className="text-xs px-2 py-0.5 rounded-full border border-[var(--card-border)] text-[var(--muted)]"
          >
            {inst}
          </span>
        ))}
      </div>

      {/* Drop zone */}
      <div
        onClick={() => !uploading && fileRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-5 text-center transition-colors ${
          uploading
            ? "border-[var(--accent)] cursor-default"
            : "border-[var(--card-border)] cursor-pointer hover:border-[var(--accent)]"
        }`}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.xlsx,.xls,.pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        {uploading ? (
          <Loader className="w-6 h-6 mx-auto mb-1 animate-spin text-[var(--accent)]" />
        ) : (
          <Upload className="w-6 h-6 mx-auto mb-1 text-[var(--muted)]" />
        )}
        <p className="text-xs text-[var(--muted)]">
          {uploading ? "Uploading…" : "Drop CSV, Excel, or PDF here"}
        </p>
      </div>

      {error && (
        <p className="text-xs text-[var(--accent-red)] px-1">{error}</p>
      )}

      {/* Audit trails for each uploaded statement */}
      {pendingIds.length > 0 && (
        <div className="space-y-3">
          {pendingIds.map((id) => (
            <AuditTrail
              key={id}
              statementId={id}
              onComplete={onUploadComplete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface Props {
  onUploadComplete?: () => void;
}

export default function FileUpload({ onUploadComplete }: Props) {
  return (
    <div className="space-y-4">
      <UploadPanel
        title="Bank Statement"
        subtitle="Thai bank account transactions"
        statementType="bank"
        icon={<Building2 className="w-5 h-5" />}
        supportedInstitutions={[
          "Kasikorn (KBank)",
          "SCB",
          "Bangkok Bank",
          "Krungsri",
          "Krungthai",
          "TTB",
          "Generic CSV/PDF",
        ]}
        onUploadComplete={onUploadComplete}
      />

      <UploadPanel
        title="Credit Card Statement"
        subtitle="Monthly CC charges — auto-links to your bank payoff"
        statementType="credit_card"
        icon={<CreditCard className="w-5 h-5" />}
        supportedInstitutions={[
          "Kasikorn CC",
          "SCB CC",
          "Bangkok Bank CC",
          "Krungsri CC",
          "Generic CSV/PDF",
        ]}
        onUploadComplete={onUploadComplete}
      />

      <UploadPanel
        title="Brokerage Statement"
        subtitle="Investment account trades and holdings"
        statementType="brokerage"
        icon={<TrendingUp className="w-5 h-5" />}
        supportedInstitutions={[
          "Webull USA",
          "Webull Thailand",
          "Dime",
          "Generic CSV",
        ]}
        onUploadComplete={onUploadComplete}
      />
    </div>
  );
}
