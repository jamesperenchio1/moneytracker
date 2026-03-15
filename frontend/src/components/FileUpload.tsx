"use client";
import { useState, useRef } from "react";
import { Upload, FileText, CheckCircle, AlertCircle, Loader } from "lucide-react";
import { uploadStatement } from "@/lib/api";

interface Props {
  onUploadComplete?: () => void;
}

export default function FileUpload({ onUploadComplete }: Props) {
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [statementType, setStatementType] = useState("bank");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setStatus("idle");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("statement_type", statementType);

    try {
      const res = await uploadStatement(formData);
      setStatus("success");
      setMessage(
        `Uploaded ${res.data.file_name} — processing ${res.data.records_processed || "..."} records`
      );
      onUploadComplete?.();
    } catch (err: unknown) {
      setStatus("error");
      const errorMsg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail || "Upload failed"
          : "Upload failed";
      setMessage(errorMsg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button
          onClick={() => setStatementType("bank")}
          className={`px-4 py-2 rounded-lg text-sm ${
            statementType === "bank"
              ? "bg-[var(--accent)] text-white"
              : "border border-[var(--card-border)] text-[var(--muted)]"
          }`}
        >
          Bank Statement
        </button>
        <button
          onClick={() => setStatementType("brokerage")}
          className={`px-4 py-2 rounded-lg text-sm ${
            statementType === "brokerage"
              ? "bg-[var(--accent)] text-white"
              : "border border-[var(--card-border)] text-[var(--muted)]"
          }`}
        >
          Brokerage Statement
        </button>
      </div>

      <div
        onClick={() => fileRef.current?.click()}
        className="border-2 border-dashed border-[var(--card-border)] rounded-xl p-8 text-center cursor-pointer hover:border-[var(--accent)] transition-colors"
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.xlsx,.xls,.pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleUpload(file);
          }}
        />
        {uploading ? (
          <Loader className="w-8 h-8 mx-auto mb-2 animate-spin text-[var(--accent)]" />
        ) : (
          <Upload className="w-8 h-8 mx-auto mb-2 text-[var(--muted)]" />
        )}
        <p className="text-sm text-[var(--muted)]">
          {uploading
            ? "Processing..."
            : "Drop CSV, Excel, or PDF statements here"}
        </p>
        <p className="text-xs text-[var(--muted)] mt-1">
          Supports: Kasikorn, SCB, Webull, Dime, and generic formats
        </p>
      </div>

      {status !== "idle" && (
        <div
          className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
            status === "success"
              ? "bg-green-500/10 text-[var(--accent-green)]"
              : "bg-red-500/10 text-[var(--accent-red)]"
          }`}
        >
          {status === "success" ? (
            <CheckCircle className="w-4 h-4" />
          ) : (
            <AlertCircle className="w-4 h-4" />
          )}
          {message}
        </div>
      )}
    </div>
  );
}
