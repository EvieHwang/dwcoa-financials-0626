import { useState } from "react";
import type { UploadSummary } from "@/lib/types";
import { Upload as UploadIcon, FileText, CheckCircle2 } from "@/icons";
import { Button, Card, CardBody, CardHead } from "@/primitives";

// CSV import (admin). POST /api/transactions/upload (multipart `file`); renders a
// result summary; server `detail` errors surface as an alert. Fetch/handler
// behavior reused unchanged (visual-redesign-009 US-5).
export default function ImportScreen({
  onUploaded,
  onToast,
}: {
  onUploaded?: () => void;
  onToast?: (msg: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [summary, setSummary] = useState<UploadSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    if (!file) return;
    setError(null);
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/transactions/upload", {
      method: "POST",
      credentials: "include",
      body: form,
    });
    if (!res.ok) {
      setSummary(null);
      let message = "Upload failed.";
      try {
        const data = await res.json();
        if (typeof data?.detail === "string") message = data.detail;
        else if (data?.detail?.errors) message = data.detail.errors.join(" ");
      } catch {
        /* keep the generic message */
      }
      setError(message);
      return;
    }
    const body = (await res.json()) as UploadSummary;
    setSummary(body);
    onUploaded?.();
    onToast?.("Import complete");
  }

  return (
    <section aria-label="Import transactions" className="space-y-[18px]">
      <Card>
        <CardHead title="Import transactions" subtitle="Upload the full bank export as CSV" />
        <CardBody className="space-y-4">
          <label className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-card border-2 border-dashed border-border-2 bg-surface-2 px-6 py-10 text-center">
            <input
              type="file"
              accept=".csv,text/csv"
              aria-label="Upload transactions CSV"
              className="sr-only"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <span className="flex h-12 w-12 items-center justify-center rounded-ctrl bg-brand-soft text-brand">
              <UploadIcon size={22} />
            </span>
            <span className="text-[13.5px] font-semibold text-ink">
              Drop your file here or click to browse
            </span>
            <span className="text-[12.5px] text-ink-3">
              {file ? file.name : "Accepts a .csv bank export"}
            </span>
          </label>
          <div className="flex justify-end">
            <Button variant="primary" onClick={handleUpload} disabled={!file}>
              <UploadIcon size={15} /> Upload
            </Button>
          </div>

          {error && (
            <p role="alert" className="text-[13px] font-medium text-neg">
              {error}
            </p>
          )}

          {summary && (
            <div
              data-testid="upload-summary"
              role="status"
              aria-live="polite"
              className="rounded-card border border-border bg-surface-2 p-5"
            >
              <div className="flex items-center gap-2 text-[14px] font-bold text-pos">
                <CheckCircle2 size={17} /> Import complete — {summary.total} rows read
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3 text-center">
                <SummaryStat label="Added" value={summary.added} />
                <SummaryStat label="Duplicates skipped" value={summary.skipped_duplicate} />
                <SummaryStat label="Unknown account" value={summary.unknown_account_count} />
              </div>
              {summary.unknown_accounts.length > 0 && (
                <p className="mt-4 flex items-start gap-2 text-[12.5px] text-ink-2">
                  <FileText size={15} className="mt-0.5 shrink-0" />
                  Unknown accounts: {summary.unknown_accounts.join(", ")}.
                </p>
              )}
            </div>
          )}
        </CardBody>
      </Card>
    </section>
  );
}

function SummaryStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-ctrl bg-surface px-3 py-3">
      <div className="tnum text-[22px] font-bold text-ink">{value}</div>
      <div className="text-[11.5px] text-ink-3">{label}</div>
    </div>
  );
}
