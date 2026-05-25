"use client";

import type { Report } from "@/types";
import { FRAUD_LABEL, RISK_BADGE, statusBadge } from "@/lib/reportLabels";

type Props = {
  report: Report;
  onClose: () => void;
  showReporterId?: boolean;
};

export function ReportDetailModal({ report, onClose, showReporterId }: Props) {
  const badge = statusBadge(report.status);
  const risk =
    report.risk_level && RISK_BADGE[report.risk_level]
      ? RISK_BADGE[report.risk_level]
      : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-detail-title"
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id="report-detail-title" className="text-lg font-bold text-slate-900">
            Report Details
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${badge.bg} ${badge.text}`}>
            {badge.label}
          </span>
          {risk ? (
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${risk.bg} ${risk.text}`}>
              {risk.label}
              {report.risk_score != null && ` · ${report.risk_score}/100`}
            </span>
          ) : (
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600">
              Not analyzed yet
            </span>
          )}
        </div>

        <dl className="mt-5 space-y-4 text-sm">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">URL</dt>
            <dd className="mt-1 break-all">
              {report.url ? (
                <a
                  href={report.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-blue-600 hover:underline"
                >
                  {report.url}
                </a>
              ) : (
                <span className="text-slate-400">—</span>
              )}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Risk Score</dt>
            <dd className="mt-1 text-slate-800">
              {report.risk_score != null ? (
                <span className="text-2xl font-bold">{report.risk_score}</span>
              ) : (
                <span className="text-slate-500">No score available — run URL analysis from search.</span>
              )}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Fraud Type</dt>
            <dd className="mt-1 text-slate-800">{FRAUD_LABEL[report.fraud_type] ?? report.fraud_type}</dd>
          </div>

          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Description</dt>
            <dd className="mt-1 whitespace-pre-wrap text-slate-700">{report.description}</dd>
          </div>

          {report.evidence_image_url && (
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Evidence</dt>
              <dd className="mt-1">
                <a
                  href={report.evidence_image_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  View evidence image
                </a>
              </dd>
            </div>
          )}

          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Submitted</dt>
            <dd className="mt-1 text-slate-700">
              {new Date(report.created_at).toLocaleString("en-US", {
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </dd>
          </div>

          {showReporterId && (
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Reporter ID</dt>
              <dd className="mt-1 font-mono text-xs text-slate-600">{report.user_id}</dd>
            </div>
          )}

          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Report ID</dt>
            <dd className="mt-1 font-mono text-xs text-slate-500">{report.id}</dd>
          </div>
        </dl>

        {report.url && (
          <a
            href={`/search?url=${encodeURIComponent(report.url)}`}
            className="mt-6 block w-full rounded-xl border border-blue-200 bg-blue-50 py-2.5 text-center text-sm font-semibold text-blue-700 hover:bg-blue-100"
          >
            Analyze this URL
          </a>
        )}
      </div>
    </div>
  );
}
