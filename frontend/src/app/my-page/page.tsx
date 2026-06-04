"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ReportDetailModal } from "@/components/reports/ReportDetailModal";
import { api } from "@/lib/api";
import { FRAUD_LABEL, statusBadge } from "@/lib/reportLabels";
import type { Report, ReportStatus, User } from "@/types";
import { passwordComplexityError, PASSWORD_COMPLEXITY_HINT } from "@/lib/passwordPolicy";

type Tab = "reports" | "account";

const STATUS_FILTERS: { label: string; value: ReportStatus | "ALL" }[] = [
  { label: "All",      value: "ALL" },
  { label: "Pending",  value: "PENDING" },
  { label: "Approved", value: "ACTIVE" },
  { label: "Hidden",   value: "HIDDEN" },
];

function MyPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<Tab>("reports");
  const [statusFilter, setStatusFilter] = useState<ReportStatus | "ALL">("ALL");

  const [user, setUser] = useState<User | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reportSubmitSuccess, setReportSubmitSuccess] = useState(false);

  // password change state
  const [showPwForm, setShowPwForm] = useState(false);
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwSuccess, setPwSuccess] = useState(false);
  const [pwSubmitting, setPwSubmitting] = useState(false);

  useEffect(() => {
    if (searchParams.get("reportSubmitted") === "1") {
      setReportSubmitSuccess(true);
      setTab("reports");
      router.replace("/my-page");
    }
  }, [searchParams, router]);

  useEffect(() => {
    Promise.all([api.me(), api.myReports()])
      .then(([u, r]) => { setUser(u); setReports(r); })
      .catch((e) => setLoadError(String(e)));
  }, []);

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    const complexityErr = passwordComplexityError(newPw);
    if (complexityErr) {
      setPwError(complexityErr);
      return;
    }
    setPwError(null);
    setPwSuccess(false);
    setPwSubmitting(true);
    try {
      await api.changePassword(currentPw, newPw);
      setPwSuccess(true);
      setCurrentPw("");
      setNewPw("");
      setShowPwForm(false);
    } catch (e) {
      setPwError(String(e));
    } finally {
      setPwSubmitting(false);
    }
  }

  if (loadError) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {loadError} — please <a href="/login" className="underline">sign in</a>.
      </div>
    );
  }

  if (!user) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-40 animate-pulse rounded-lg bg-slate-200" />
        <div className="h-24 w-full animate-pulse rounded-xl bg-slate-200" />
        <div className="h-32 w-full animate-pulse rounded-xl bg-slate-200" />
      </div>
    );
  }

  const filteredReports =
    statusFilter === "ALL"
      ? reports
      : reports.filter((r) => r.status === statusFilter);

  const countFor = (v: ReportStatus | "ALL") =>
    v === "ALL" ? reports.length : reports.filter((r) => r.status === v).length;

  return (
    <section className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">My Page</h1>
        <p className="mt-1 text-sm text-slate-500">Manage your information and reports</p>
      </div>

      {reportSubmitSuccess && (
        <div
          className="flex items-start justify-between gap-3 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800"
          role="status"
        >
          <p>Your fraud report was submitted successfully.</p>
          <button
            type="button"
            onClick={() => setReportSubmitSuccess(false)}
            className="shrink-0 text-xs font-medium text-green-700 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
        {(["reports", "account"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              tab === t
                ? "bg-slate-900 text-white"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {t === "reports" ? (
              <>
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                My Reports ({reports.length})
              </>
            ) : (
              <>
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                Account Information
              </>
            )}
          </button>
        ))}
      </div>

      {/* My Reports tab */}
      {tab === "reports" && (
        <div className="space-y-4">
          {/* Status filter pills */}
          <div className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setStatusFilter(f.value)}
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                  statusFilter === f.value
                    ? "bg-slate-900 text-white"
                    : "border border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                {f.label}
                <span className="ml-1.5 rounded-full bg-white/20 px-1.5 py-0.5 text-xs">
                  {countFor(f.value)}
                </span>
              </button>
            ))}
          </div>

          {/* Report list */}
          {filteredReports.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-white py-12 text-center text-sm text-slate-400 shadow-sm">
              No reports found.
            </div>
          ) : (
            <ul className="space-y-3">
              {filteredReports.map((r) => {
                const badge = statusBadge(r.status);
                return (
                  <li
                    key={r.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => setSelectedReport(r)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setSelectedReport(r);
                      }
                    }}
                    className="cursor-pointer rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-blue-200 hover:bg-blue-50/30"
                  >
                    <div className="flex items-center justify-between">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${badge.bg} ${badge.text}`}>
                        {badge.label}
                      </span>
                      <span className="text-xs text-slate-400">
                        {new Date(r.created_at).toLocaleDateString("en-US", {
                          year: "numeric", month: "short", day: "numeric",
                        })}
                      </span>
                    </div>
                    <p className="mt-2 text-sm font-semibold text-slate-800">
                      Report Type: {FRAUD_LABEL[r.fraud_type] ?? r.fraud_type}
                    </p>
                    {r.url && (
                      <p className="mt-1 truncate text-xs text-blue-600">{r.url}</p>
                    )}
                    {r.risk_score != null && (
                      <p className="mt-1 text-xs font-medium text-slate-600">
                        Risk score: {r.risk_score}
                        {r.risk_level ? ` (${r.risk_level})` : ""}
                      </p>
                    )}
                    <p className="mt-1 text-sm text-slate-600 line-clamp-2">{r.description}</p>
                    <p className="mt-2 text-xs text-slate-400">Click for details</p>
                    {(r.has_evidence || r.evidence_image_url) && (
                      <p className="mt-2 text-xs text-slate-500">Includes evidence image</p>
                    )}
                  </li>
                );
              })}
            </ul>
          )}

          {selectedReport && (
            <ReportDetailModal
              report={selectedReport}
              onClose={() => setSelectedReport(null)}
            />
          )}
        </div>
      )}

      {/* Account tab */}
      {tab === "account" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-700">Account Details</h2>
            <div className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-500">Email</label>
                <input
                  type="email"
                  readOnly
                  value={user.email}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-700"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500">Role</label>
                <input
                  type="text"
                  readOnly
                  value={user.role}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-700"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500">Account Status</label>
                <input
                  type="text"
                  readOnly
                  value={user.status}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-700"
                />
              </div>
            </div>
          </div>

          {/* Password change */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-700">Change Password</h2>
              <button
                onClick={() => { setShowPwForm(!showPwForm); setPwError(null); setPwSuccess(false); }}
                className="text-xs text-blue-600 hover:underline"
              >
                {showPwForm ? "Cancel" : "Change"}
              </button>
            </div>

            {pwSuccess && (
              <p className="mt-2 text-sm text-green-700">Password changed successfully.</p>
            )}

            {showPwForm && (
              <form onSubmit={changePassword} className="mt-4 space-y-3">
                <input
                  type="password"
                  required
                  placeholder="Current password"
                  value={currentPw}
                  onChange={(e) => setCurrentPw(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="New password (min. 8 chars, with numbers and special chars)"
                  value={newPw}
                  onChange={(e) => setNewPw(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
                <p className="text-xs text-slate-500">{PASSWORD_COMPLEXITY_HINT}</p>
                {pwError && <p className="text-sm text-red-600">{pwError}</p>}
                <button
                  type="submit"
                  disabled={pwSubmitting}
                  className="w-full rounded-xl bg-slate-900 py-2.5 text-sm font-semibold text-white disabled:bg-slate-300"
                >
                  {pwSubmitting ? "Saving…" : "Save New Password"}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

export default function MyPage() {
  return (
    <Suspense fallback={
      <div className="space-y-4">
        <div className="h-8 w-40 animate-pulse rounded-lg bg-slate-200" />
        <div className="h-24 w-full animate-pulse rounded-xl bg-slate-200" />
      </div>
    }>
      <MyPageContent />
    </Suspense>
  );
}
