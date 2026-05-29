"use client";

import { Suspense, useLayoutEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { FraudType } from "@/types";

const FRAUD_TYPES: { value: FraudType; label: string }[] = [
  { value: "NON_DELIVERY",          label: "Non-delivery of Goods" },
  { value: "FALSE_ADVERTISING",     label: "False Advertising" },
  { value: "REFUSAL_OF_REFUND",     label: "Refusal of Refund" },
  { value: "DEFECTIVE_PRODUCTS",    label: "Defective Products" },
  { value: "PERSONAL_DATA_LEAKAGE", label: "Personal Data Leakage" },
  { value: "OTHERS",                label: "Others" },
];

function ReportForm() {
  const params = useSearchParams();
  const router = useRouter();
  const queryString = params.toString();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [url, setUrl] = useState(params.get("url") ?? "");
  const [fraudType, setFraudType] = useState<FraudType>("NON_DELIVERY");
  const [description, setDescription] = useState("");
  const [evidenceImageUrl, setEvidenceImageUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authReady, setAuthReady] = useState(false);

  useLayoutEffect(() => {
    if (!getToken()) {
      const next = queryString ? `/report?${queryString}` : "/report";
      router.replace(`/login?next=${encodeURIComponent(next)}`);
      return;
    }
    setAuthReady(true);
  }, [queryString, router]);

  const descOk = description.trim().length >= 20;
  const canSubmit = authReady && consent && url.trim() !== "" && descOk && !submitting && !uploading;

  async function uploadFile(file: File) {
    setUploading(true);
    setUploadError(null);
    try {
      const { url: uploadedUrl } = await api.uploadEvidence(file);
      setEvidenceImageUrl(uploadedUrl);
    } catch (e) {
      setUploadError(String(e));
    } finally {
      setUploading(false);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.createReport({
        url,
        fraud_type: fraudType,
        description,
        evidence_image_url: evidenceImageUrl || undefined,
        legal_consent: consent,
      });
      router.push("/my-page");
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      await uploadFile(file);
    } else {
      // Fallback: accept pasted URL text
      const text = e.dataTransfer.getData("text/plain");
      if (text) setEvidenceImageUrl(text);
    }
  }

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) await uploadFile(file);
  }

  if (!authReady) {
    return (
      <section className="mx-auto max-w-xl py-12">
        <div className="h-10 w-56 animate-pulse rounded-lg bg-slate-200" />
        <div className="mt-6 h-32 animate-pulse rounded-xl bg-slate-100" />
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Report Fraud</h1>
        <p className="mt-1 text-sm text-slate-500">Report suspicious shops</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-5">
        {/* URL */}
        <div>
          <label className="block text-sm font-medium text-slate-700">
            URL <span className="text-red-500">*</span>
          </label>
          <input
            type="url"
            required
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example-shop.com/product/123"
            className="mt-1.5 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>

        {/* Fraud Type */}
        <div>
          <label className="block text-sm font-medium text-slate-700">
            Fraud Type <span className="text-red-500">*</span>
          </label>
          <select
            value={fraudType}
            onChange={(e) => setFraudType(e.target.value as FraudType)}
            className="mt-1.5 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            {FRAUD_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-slate-700">
            Description <span className="text-red-500">*</span>
          </label>
          <textarea
            required
            minLength={20}
            rows={5}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the fraud incident in detail"
            className="mt-1.5 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
          <div className="mt-1 flex items-center justify-between">
            <span className="text-xs text-slate-400">Please enter at least 20 characters</span>
            <span className={`text-xs ${descOk ? "text-green-600" : "text-slate-400"}`}>
              {description.trim().length}/20
            </span>
          </div>
        </div>

        {/* Evidence upload — uploads to Supabase Storage */}
        <div>
          <label className="block text-sm font-medium text-slate-700">
            Evidence <span className="text-xs font-normal text-slate-400">(Optional)</span>
          </label>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`mt-1.5 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 transition-colors ${
              dragging
                ? "border-blue-400 bg-blue-50"
                : "border-slate-300 bg-slate-50 hover:bg-slate-100"
            }`}
          >
            {uploading ? (
              <p className="text-sm text-slate-500">Uploading…</p>
            ) : evidenceImageUrl ? (
              <>
                <svg className="h-6 w-6 text-green-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <p className="mt-1 text-sm text-green-700">Image uploaded</p>
                <p className="mt-0.5 max-w-full truncate text-xs text-slate-400">{evidenceImageUrl}</p>
              </>
            ) : (
              <>
                <svg className="h-8 w-8 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
                <p className="mt-2 text-sm text-slate-500">Click or drag to upload image</p>
                <p className="text-xs text-slate-400">PNG, JPG, GIF, WebP (max 5 MB)</p>
              </>
            )}
          </div>
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            className="hidden"
            onChange={onFileChange}
          />
          {uploadError && (
            <p className="mt-1 text-xs text-red-600">{uploadError}</p>
          )}
          {/* Manual URL fallback */}
          <input
            type="url"
            value={evidenceImageUrl}
            onChange={(e) => setEvidenceImageUrl(e.target.value)}
            placeholder="Or paste image URL here"
            className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>

        {/* Legal warning */}
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex gap-2">
            <svg className="mt-0.5 h-4 w-4 shrink-0 text-red-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <p className="text-sm font-medium text-red-700">
              False reports may result in legal liability and service restrictions.
              Please submit only fact-based reports.
            </p>
          </div>
          <label className="mt-3 flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="h-4 w-4 accent-blue-600"
            />
            <span className="text-sm text-slate-700">I have read and agree to the above</span>
          </label>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-1">
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded-xl border border-slate-300 px-5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {submitting ? "Submitting…" : "Submit Report"}
          </button>
        </div>
      </form>
    </section>
  );
}

export default function ReportPage() {
  return (
    <Suspense fallback={<div className="h-96 animate-pulse rounded-xl bg-slate-200" />}>
      <ReportForm />
    </Suspense>
  );
}
