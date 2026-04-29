"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { RiskLevel, UrlAnalysisResult } from "@/types";

const LEVEL_COLOR: Record<RiskLevel, string> = {
  SAFE:     "bg-risk-safe",
  WARNING:  "bg-risk-warning",
  DANGER:   "bg-risk-danger",
  CRITICAL: "bg-risk-critical",
};

function SearchResults() {
  const params = useSearchParams();
  const router = useRouter();
  const url = params.get("url") ?? "";

  const [result, setResult] = useState<UrlAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pollScore, setPollScore] = useState<number | null>(null);
  const [pollLevel, setPollLevel] = useState<RiskLevel | null>(null);

  useEffect(() => {
    if (!url) return;
    setError(null);
    api.searchUrl(url).then(setResult).catch((e) => setError(String(e)));
  }, [url]);

  useEffect(() => {
    if (!result?.job_id || result.cached) return;
    const id = setInterval(async () => {
      try {
        const job = await api.getJob(result.job_id!);
        if (job.status === "COMPLETED") {
          setPollScore(job.final_risk_score);
          setPollLevel(job.risk_level as RiskLevel | null);
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

  if (!url) return <p>No URL provided.</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (!result) return <p>Loading…</p>;

  const score = result.risk_score ?? pollScore;
  const level = result.risk_level ?? pollLevel;

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm text-slate-500">Analyzed URL</p>
        <p className="break-all font-mono text-sm">{result.url}</p>
      </div>

      {score == null ? (
        <div className="animate-pulse rounded-lg border border-slate-200 bg-white p-6">
          <p className="text-slate-600">AI analysis in progress…</p>
          <div className="mt-4 h-8 w-32 rounded bg-slate-200" />
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <p className="text-sm text-slate-500">Risk Score (0–100)</p>
          <div className="mt-2 flex items-center gap-3">
            <span className="text-4xl font-bold">{score}</span>
            {level && (
              <span className={`rounded-full px-3 py-1 text-sm font-medium text-white ${LEVEL_COLOR[level]}`}>
                {level}
              </span>
            )}
          </div>
          <p className="mt-2 text-sm text-slate-500">Reports: {result.report_count}</p>
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={() => router.push(`/report?url=${encodeURIComponent(result.url)}`)}
          className="rounded-lg border border-red-300 px-4 py-2 text-sm text-red-700 hover:bg-red-50"
        >
          Report as Fraud
        </button>
      </div>
    </section>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<p>Loading…</p>}>
      <SearchResults />
    </Suspense>
  );
}
