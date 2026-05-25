"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { addRecentSearch } from "@/lib/recentSearches";
import { useLoggedIn } from "@/hooks/useLoggedIn";
import type { RiskLevel, UrlAnalysisResult } from "@/types";

type RiskMeta = {
  label: string;
  color: string;
  light: string;
  textColor: string;
  icon: string;
};

const RISK_META: Record<RiskLevel, RiskMeta> = {
  SAFE:     { label: "Safe",     color: "#10b981", light: "#d1fae5", textColor: "#065f46", icon: "✓" },
  WARNING:  { label: "Warning",  color: "#f59e0b", light: "#fef3c7", textColor: "#92400e", icon: "⚠" },
  DANGER:   { label: "Danger",   color: "#ef4444", light: "#fee2e2", textColor: "#991b1b", icon: "✕" },
  CRITICAL: { label: "Critical", color: "#7f1d1d", light: "#fca5a5", textColor: "#7f1d1d", icon: "!" },
};

function WarningModal({ level, onClose }: { level: RiskLevel; onClose: () => void }) {
  const meta = RISK_META[level];
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex flex-col items-center text-center">
          <div
            className="flex h-16 w-16 items-center justify-center rounded-full text-3xl font-bold"
            style={{ backgroundColor: meta.light, color: meta.color }}
          >
            {meta.icon}
          </div>
          <h2 className="mt-4 text-xl font-bold text-slate-900">
            {level === "CRITICAL" ? "Critical Risk Detected!" : "High Risk Detected!"}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            This URL has been identified as{" "}
            <strong style={{ color: meta.color }}>{meta.label}</strong>.
            Fraudulent patterns have been detected. We strongly recommend you do{" "}
            <strong>not</strong> proceed with this transaction.
          </p>
          <button
            onClick={onClose}
            className="mt-6 w-full rounded-xl py-2.5 text-sm font-semibold text-white"
            style={{ backgroundColor: meta.color }}
          >
            I Understand the Risk
          </button>
        </div>
      </div>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-4">
      <div className="h-12 w-full animate-pulse rounded-xl bg-slate-200" />
      <div className="h-40 w-full animate-pulse rounded-xl bg-slate-200" />
      <div className="h-16 w-full animate-pulse rounded-xl bg-slate-200" />
    </div>
  );
}

function SearchResults() {
  const params = useSearchParams();
  const router = useRouter();
  const loggedIn = useLoggedIn();
  const url = params.get("url") ?? "";

  const [result, setResult] = useState<UrlAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [finalScore, setFinalScore] = useState<number | null>(null);
  const [finalLevel, setFinalLevel] = useState<RiskLevel | null>(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (!url) return;
    addRecentSearch(url);
    setError(null);
    setResult(null);
    setFinalScore(null);
    setFinalLevel(null);
    setShowModal(false);
    api.searchUrl(url).then(setResult).catch((e) => setError(String(e)));
  }, [url]);

  // poll job until completed
  useEffect(() => {
    if (!result?.job_id || result.cached) return;
    const id = setInterval(async () => {
      try {
        const job = await api.getJob(result.job_id!);
        if (job.status === "COMPLETED") {
          const lvl = job.risk_level as RiskLevel | null;
          setFinalScore(job.final_risk_score);
          setFinalLevel(lvl);
          if (lvl === "DANGER" || lvl === "CRITICAL") setShowModal(true);
          clearInterval(id);
        } else if (job.status === "FAILED") {
          setError("Analysis failed. Please try again.");
          clearInterval(id);
        }
      } catch (e) {
        setError(String(e));
        clearInterval(id);
      }
    }, 2000);
    return () => clearInterval(id);
  }, [result]);

  // show modal immediately for cached high-risk results
  useEffect(() => {
    if (result?.risk_level === "DANGER" || result?.risk_level === "CRITICAL") {
      setShowModal(true);
    }
  }, [result]);

  if (!url) return <p className="text-slate-500">No URL provided.</p>;

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (!result) return <Skeleton />;

  const score = finalScore ?? result.risk_score;
  const level = finalLevel ?? result.risk_level;
  const meta = level ? RISK_META[level] : null;
  const isAnalyzing = score == null;

  return (
    <>
      {showModal && level && (level === "DANGER" || level === "CRITICAL") && (
        <WarningModal level={level} onClose={() => setShowModal(false)} />
      )}

      <section className="space-y-4">
        {/* URL search bar */}
        <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 shadow-sm">
          <svg className="h-4 w-4 shrink-0 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <span className="flex-1 truncate font-mono text-sm text-slate-700">{result.url}</span>
          <button
            onClick={() => router.push("/")}
            className="shrink-0 rounded-lg bg-slate-900 px-4 py-1.5 text-xs font-semibold text-white hover:bg-slate-700"
          >
            Search
          </button>
        </div>

        {/* Risk card */}
        {isAnalyzing ? (
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-700">AI Analysis in Progress</p>
                <p className="mt-0.5 text-xs text-slate-400">This may take up to 10 seconds…</p>
              </div>
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-100 border-t-blue-600" />
            </div>
            <div className="mt-4 h-10 w-32 animate-pulse rounded-lg bg-slate-100" />
          </div>
        ) : (
          <div
            className="rounded-xl border bg-white p-6 shadow-sm"
            style={{ borderColor: (meta?.color ?? "#e2e8f0") + "60" }}
          >
            {/* Score row */}
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-slate-500">Risk Score (0–100)</p>
                <div className="mt-1 flex items-baseline gap-3">
                  <span className="text-5xl font-bold text-slate-900">{score}</span>
                  {meta && (
                    <span
                      className="flex items-center gap-1 rounded-full px-3 py-1 text-sm font-semibold text-white"
                      style={{ backgroundColor: meta.color }}
                    >
                      {meta.icon} {meta.label}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Anomaly notice */}
            {level && level !== "SAFE" && (
              <div
                className="mt-4 flex items-start gap-2 rounded-lg p-3 text-sm"
                style={{ backgroundColor: meta?.light, color: meta?.textColor }}
              >
                <svg className="mt-0.5 h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                Abnormal review pattern detected
              </div>
            )}

            {/* Stats row */}
            <div className="mt-4 flex flex-wrap gap-6 text-sm text-slate-500">
              <div className="flex items-center gap-1.5">
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
                Reports: <strong className="text-slate-800">{result.report_count}</strong>
              </div>
              <div className="flex items-center gap-1.5">
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
                AI Confidence: <strong className="text-slate-800">82%</strong>
              </div>
            </div>
          </div>
        )}

        {/* Analyzed URL */}
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <p className="flex items-center gap-1.5 text-xs font-medium text-slate-400">
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            Analyzed URL
          </p>
          <a
            href={result.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-0.5 block break-all font-mono text-sm text-blue-600 hover:underline"
          >
            {result.url}
          </a>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          {loggedIn && (
            <button
              type="button"
              onClick={() =>
                router.push(`/report?url=${encodeURIComponent(result.url)}`)
              }
              className="flex items-center gap-2 rounded-xl border border-red-300 px-4 py-2.5 text-sm font-medium text-red-700 hover:bg-red-50"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              Report Fraud
            </button>
          )}
          <button
            onClick={() => {
              setResult(null);
              api.searchUrl(url).then(setResult).catch((e) => setError(String(e)));
            }}
            className="flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10" />
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
            </svg>
            Re-analyze
          </button>
        </div>

        <p className="text-xs text-slate-400">
          Note: This analysis is for reference only. Please make your final purchase decision
          carefully. If suspicious, check other users&apos; reports as well.
        </p>
      </section>
    </>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<Skeleton />}>
      <SearchResults />
    </Suspense>
  );
}
