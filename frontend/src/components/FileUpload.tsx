"use client";
import { useState, useRef, useCallback, useEffect } from "react";
import {
  Upload,
  FileText,
  CheckCircle,
  AlertCircle,
  Loader,
  X,
} from "lucide-react";
import { uploadStatement, getStatement } from "@/lib/api";
import type { UploadFileItem } from "@/lib/types";

interface Props {
  onUploadComplete?: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-gray-500/20 text-gray-400",
  uploading: "bg-blue-500/20 text-[var(--accent)]",
  processing: "bg-amber-500/20 text-[var(--accent-amber)]",
  completed: "bg-green-500/20 text-[var(--accent-green)]",
  failed: "bg-red-500/20 text-[var(--accent-red)]",
};

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued",
  uploading: "Uploading...",
  processing: "Processing...",
  completed: "Completed",
  failed: "Failed",
};

export default function FileUpload({ onUploadComplete }: Props) {
  const [files, setFiles] = useState<UploadFileItem[]>([]);
  const [statementType, setStatementType] = useState("bank");
  const [isDragging, setIsDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const items: UploadFileItem[] = Array.from(newFiles).map((file) => ({
      file,
      id: `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      status: "queued" as const,
    }));
    setFiles((prev) => [...prev, ...items]);
  }, []);

  const removeFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const startPolling = useCallback(
    (items: { fileId: string; statementId: number }[]) => {
      const remaining = new Set(items.map((i) => i.fileId));

      const poll = async () => {
        for (const item of items) {
          if (!remaining.has(item.fileId)) continue;

          try {
            const res = await getStatement(item.statementId);
            const stmt = res.data;

            if (stmt.status === "completed") {
              setFiles((prev) =>
                prev.map((f) =>
                  f.id === item.fileId
                    ? {
                        ...f,
                        status: "completed" as const,
                        recordsProcessed: stmt.records_processed,
                      }
                    : f
                )
              );
              remaining.delete(item.fileId);
            } else if (stmt.status === "failed") {
              setFiles((prev) =>
                prev.map((f) =>
                  f.id === item.fileId
                    ? {
                        ...f,
                        status: "failed" as const,
                        errorMessage: stmt.error_message || "Processing failed",
                      }
                    : f
                )
              );
              remaining.delete(item.fileId);
            }
          } catch {
            // Keep polling on transient errors
          }
        }

        if (remaining.size > 0) {
          pollingRef.current = setTimeout(poll, 2000);
        } else {
          onUploadComplete?.();
        }
      };

      pollingRef.current = setTimeout(poll, 2000);
    },
    [onUploadComplete]
  );

  const uploadAll = useCallback(async () => {
    const queuedFiles = files.filter((f) => f.status === "queued");
    const uploadedIds: { fileId: string; statementId: number }[] = [];

    for (const item of queuedFiles) {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === item.id ? { ...f, status: "uploading" as const } : f
        )
      );

      try {
        const formData = new FormData();
        formData.append("file", item.file);
        formData.append("statement_type", statementType);
        const res = await uploadStatement(formData);
        const stmtId = res.data.id;

        setFiles((prev) =>
          prev.map((f) =>
            f.id === item.id
              ? { ...f, status: "processing" as const, statementId: stmtId }
              : f
          )
        );
        uploadedIds.push({ fileId: item.id, statementId: stmtId });
      } catch {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === item.id
              ? { ...f, status: "failed" as const, errorMessage: "Upload failed" }
              : f
          )
        );
      }
    }

    if (uploadedIds.length > 0) {
      startPolling(uploadedIds);
    }
  }, [files, statementType, startPolling]);

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearTimeout(pollingRef.current);
    };
  }, []);

  const hasQueued = files.some((f) => f.status === "queued");
  const isProcessing = files.some(
    (f) => f.status === "uploading" || f.status === "processing"
  );
  const completedCount = files.filter((f) => f.status === "completed").length;
  const failedCount = files.filter((f) => f.status === "failed").length;
  const totalRecords = files.reduce(
    (sum, f) => sum + (f.recordsProcessed || 0),
    0
  );

  return (
    <div className="space-y-4">
      {/* Statement type toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setStatementType("bank")}
          className={`px-4 py-2 rounded-lg text-sm transition-colors ${
            statementType === "bank"
              ? "bg-[var(--accent)] text-white"
              : "border border-[var(--card-border)] text-[var(--muted)] hover:text-white"
          }`}
        >
          Bank Statement
        </button>
        <button
          onClick={() => setStatementType("brokerage")}
          className={`px-4 py-2 rounded-lg text-sm transition-colors ${
            statementType === "brokerage"
              ? "bg-[var(--accent)] text-white"
              : "border border-[var(--card-border)] text-[var(--muted)] hover:text-white"
          }`}
        >
          Brokerage Statement
        </button>
      </div>

      {/* Drop zone */}
      <div
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
        }}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
          isDragging
            ? "border-[var(--accent)] bg-blue-500/5 scale-[1.01]"
            : "border-[var(--card-border)] hover:border-[var(--accent)]"
        }`}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.xlsx,.xls,.pdf"
          className="hidden"
          multiple
          onChange={(e) => {
            if (e.target.files?.length) addFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <Upload
          className={`w-8 h-8 mx-auto mb-2 ${isDragging ? "text-[var(--accent)]" : "text-[var(--muted)]"}`}
        />
        <p className="text-sm text-[var(--muted)]">
          Drop CSV, Excel, or PDF statements here — or click to browse
        </p>
        <p className="text-xs text-[var(--muted)] mt-1">
          Select multiple files at once
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-3 p-3 rounded-lg border border-[var(--card-border)] bg-[var(--card)]"
            >
              <FileText className="w-4 h-4 text-[var(--muted)] shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm truncate">{item.file.name}</div>
                {item.recordsProcessed !== undefined && (
                  <div className="text-xs text-[var(--accent-green)]">
                    {item.recordsProcessed} transactions imported
                  </div>
                )}
                {item.errorMessage && (
                  <div className="text-xs text-[var(--accent-red)]">
                    {item.errorMessage}
                  </div>
                )}
              </div>
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-medium shrink-0 ${STATUS_COLORS[item.status]}`}
              >
                {item.status === "uploading" || item.status === "processing" ? (
                  <span className="flex items-center gap-1">
                    <Loader className="w-3 h-3 animate-spin" />
                    {STATUS_LABELS[item.status]}
                  </span>
                ) : item.status === "completed" ? (
                  <span className="flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" />
                    {STATUS_LABELS[item.status]}
                  </span>
                ) : item.status === "failed" ? (
                  <span className="flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {STATUS_LABELS[item.status]}
                  </span>
                ) : (
                  STATUS_LABELS[item.status]
                )}
              </span>
              {item.status === "queued" && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(item.id);
                  }}
                  className="text-[var(--muted)] hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Upload button */}
      {hasQueued && (
        <button
          onClick={uploadAll}
          disabled={isProcessing}
          className="w-full py-3 rounded-lg bg-[var(--accent)] text-white font-medium text-sm hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          Upload {files.filter((f) => f.status === "queued").length} file(s)
        </button>
      )}

      {/* Summary */}
      {files.length > 0 &&
        !hasQueued &&
        !isProcessing &&
        (completedCount > 0 || failedCount > 0) && (
          <div className="flex items-center gap-3 p-4 rounded-lg bg-[var(--card)] border border-[var(--card-border)]">
            <CheckCircle className="w-5 h-5 text-[var(--accent-green)]" />
            <div className="flex-1">
              <div className="text-sm font-medium">Upload Complete</div>
              <div className="text-xs text-[var(--muted)]">
                {completedCount} file(s) processed, {totalRecords} transactions
                imported
                {failedCount > 0 && `, ${failedCount} failed`}
              </div>
            </div>
            <button
              onClick={() => setFiles([])}
              className="text-xs text-[var(--muted)] hover:text-white px-3 py-1 rounded border border-[var(--card-border)]"
            >
              Clear
            </button>
          </div>
        )}
    </div>
  );
}
