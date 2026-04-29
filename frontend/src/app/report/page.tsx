"use client";

import { Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { FraudType } from "@/types";

const FRAUD_TYPES: { value: FraudType; label: string }[] = [
  { value: "NON_DELIVERY",        label: "Non-delivery of Goods" },
  { value: "FALSE_ADVERTISING",   label: "False Advertising" },
  { value: "REFUSAL_OF_REFUND",   label: "Refusal of Refund" },
  { value: "DEFECTIVE_PRODUCTS",  label: "Defective Products" },
  { value: "PERSONAL_DATA_LEAKAGE", label: "Personal Data Leakage" },
  { value: "OTHERS",              label: "Others" },
];

function ReportForm() {
  const params = useSearchParams();
  const router = useRouter();

  const [url, setUrl] = useState(params.get("url") ?? "");
  const [fraudType, setFraudType] = useState<FraudType>("NON_DELIVERY");
  const [description, setDescription] = useState("");
  const [evidenceImageUrl, setEvidenceImageUrl] = useState("");
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = consent && url.trim() !== "" && description.trim().length >= 20 && !submitting;

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

  return (
    <section className="mx-auto max-w-xl space-y-4">
      <h1 className="text-2xl font-bold">Report Fraud</h1>
      <p className="text-sm text-slate-600">Report suspicious shops</p>

      <form onSubmit={onSubmit} className="space-y-4">
        <label className="block">
          <span className="block text-sm font-medium">URL *</span>
          <input
            type="url" required value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>

        <label className="block">
          <span className="block text-sm font-medium">Fraud Type *</span>
          <select
            value={fraudType}
            onChange={(e) => setFraudType(e.target.value as FraudType)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          >
            {FRAUD_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="block text-sm font-medium">Description *</span>
          <textarea
            required minLength={20} rows={5} value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the fraud incident in detail"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
          <span className="text-xs text-slate-500">Please enter at least 20 characters</span>
        </label>

        <label className="block">
          <span className="block text-sm font-medium">Evidence (Optional)</span>
          <input
            type="url" value={evidenceImageUrl}
            onChange={(e) => setEvidenceImageUrl(e.target.value)}
            placeholder="Image URL"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>

        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
          <p className="font-medium text-red-700">
            ⚠ False reports may result in legal liability and service restrictions.
            Please submit only fact-based reports.
          </p>
          <label className="mt-2 flex items-center gap-2">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <span>I have read and agree to the above</span>
          </label>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-2">
          <button
            type="button" onClick={() => router.back()}
            className="rounded border border-slate-300 px-4 py-2"
          >
            Cancel
          </button>
          <button
            type="submit" disabled={!canSubmit}
            className="rounded bg-slate-900 px-4 py-2 text-white disabled:bg-slate-400"
          >
            Submit Report
          </button>
        </div>
      </form>
    </section>
  );
}

export default function ReportPage() {
  return (
    <Suspense fallback={<p>Loading…</p>}>
      <ReportForm />
    </Suspense>
  );
}
