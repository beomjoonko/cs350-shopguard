"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Report, ReportStatus } from "@/types";

const ALL_STATUSES: ReportStatus[] = ["ACTIVE", "PENDING", "HIDDEN", "UNDER_REVIEW", "VERIFIED", "BLINDED_DELETED"];

const STATUS_BADGE: Record<string, { label: string; bg: string; text: string }> = {
  PENDING:        { label: "Pending",      bg: "bg-amber-100",  text: "text-amber-800" },
  ACTIVE:         { label: "Approved",     bg: "bg-green-100",  text: "text-green-800" },
  UNDER_REVIEW:   { label: "Under Review", bg: "bg-purple-100", text: "text-purple-800" },
  VERIFIED:       { label: "Verified",     bg: "bg-green-100",  text: "text-green-800" },
  BLINDED_DELETED:{ label: "Removed",      bg: "bg-slate-100",  text: "text-slate-600" },
  HIDDEN:         { label: "Hidden",       bg: "bg-slate-100",  text: "text-slate-600" },
};

const FRAUD_LABEL: Record<string, string> = {
  NON_DELIVERY:          "Non-delivery",
  FALSE_ADVERTISING:     "False Advertising",
  REFUSAL_OF_REFUND:     "Refund Denial",
  DEFECTIVE_PRODUCTS:    "Defective Products",
  PERSONAL_DATA_LEAKAGE: "Data Leakage",
  OTHERS:                "Others",
};

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

export default function AdminPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<ReportStatus | "ALL">("ALL");
  const [blockingId, setBlockingId] = useState<string | null>(null);

  useEffect(() => {
    api.adminListReports().then(setReports).catch((e) => setError(String(e)));
  }, []);

  async function updateStatus(id: string, status: ReportStatus) {
    try {
      const updated = await api.adminUpdateReportStatus(id, status);
      setReports((prev) => prev.map((r) => (r.id === id ? updated : r)));
    } catch (e) {
      setError(String(e));
    }
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error} — make sure you are signed in as an administrator.
      </div>
    );
  }

  const countOf = (s: ReportStatus) => reports.filter((r) => r.status === s).length;
  const filtered =
    statusFilter === "ALL" ? reports : reports.filter((r) => r.status === statusFilter);

  return (
    <section className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Admin Panel</h1>
        <p className="mt-1 text-sm text-slate-500">Review and manage fraud reports</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Total Reports" value={reports.length}             color="text-slate-900" />
        <StatCard label="Pending"       value={countOf("PENDING")}         color="text-amber-600" />
        <StatCard label="Approved"      value={countOf("ACTIVE")}          color="text-green-600" />
        <StatCard label="Hidden"        value={countOf("HIDDEN")}          color="text-slate-500" />
      </div>

      {/* Report list */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        {/* Table header + filter */}
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <p className="text-sm font-semibold text-slate-700">Report List</p>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as ReportStatus | "ALL")}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="ALL">All</option>
              {ALL_STATUSES.map((s) => (
                <option key={s} value={s}>{STATUS_BADGE[s]?.label ?? s}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 text-left">ID</th>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Report Date</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-10 text-center text-slate-400">
                    No reports found.
                  </td>
                </tr>
              )}
              {filtered.map((r) => {
                const badge = STATUS_BADGE[r.status] ?? { label: r.status, bg: "bg-slate-100", text: "text-slate-600" };
                return (
                  <tr key={r.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">
                      {r.id.slice(0, 8)}…
                    </td>
                    <td className="px-4 py-3 text-slate-700">
                      {FRAUD_LABEL[r.fraud_type] ?? r.fraud_type}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${badge.bg} ${badge.text}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {new Date(r.created_at).toLocaleDateString("en-US", {
                        year: "numeric", month: "short", day: "numeric",
                      })}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {/* Approve */}
                        <button
                          onClick={() => updateStatus(r.id, "ACTIVE")}
                          disabled={r.status === "ACTIVE"}
                          title="Approve"
                          className="rounded-lg p-1.5 text-green-600 hover:bg-green-50 disabled:cursor-not-allowed disabled:opacity-30"
                        >
                          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </button>
                        {/* Pending */}
                        <button
                          onClick={() => updateStatus(r.id, "PENDING")}
                          disabled={r.status === "PENDING"}
                          title="Set Pending"
                          className="rounded-lg p-1.5 text-amber-600 hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-30"
                        >
                          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                            <polyline points="12 6 12 12 16 14" />
                          </svg>
                        </button>
                        {/* Hide */}
                        <button
                          onClick={() => updateStatus(r.id, "HIDDEN")}
                          disabled={r.status === "HIDDEN"}
                          title="Hide"
                          className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-30"
                        >
                          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                            <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                            <line x1="1" y1="1" x2="23" y2="23" />
                          </svg>
                        </button>
                        {/* Block user — opens dropdown */}
                        <select
                          value=""
                          onChange={(e) => {
                            if (e.target.value === "block") {
                              const reason = window.prompt("Reason for blocking this user:");
                              if (reason) {
                                api.adminBlockUser(r.url_id, reason).catch(() => {});
                                setBlockingId(r.id);
                              }
                            }
                            e.target.value = "";
                          }}
                          className="rounded-lg border border-slate-300 px-2 py-1 text-xs text-slate-600 focus:outline-none"
                        >
                          <option value="">More</option>
                          <option value="block">Block Reporter</option>
                        </select>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {blockingId && (
        <p className="text-sm text-green-700">User block action submitted for report {blockingId.slice(0, 8)}.</p>
      )}
    </section>
  );
}
