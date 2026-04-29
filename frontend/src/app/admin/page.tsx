"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Report, ReportStatus } from "@/types";

const STATUSES: ReportStatus[] = ["ACTIVE", "PENDING", "HIDDEN"];

export default function AdminPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [error, setError] = useState<string | null>(null);

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

  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Admin Panel</h1>
        <p className="text-sm text-slate-600">Review and manage fraud reports</p>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">ID</th>
              <th className="px-3 py-2 text-left">Type</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Date</th>
              <th className="px-3 py-2 text-left">Action</th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr key={r.id} className="border-t border-slate-200">
                <td className="px-3 py-2 font-mono text-xs">{r.id.slice(0, 8)}…</td>
                <td className="px-3 py-2">{r.fraud_type}</td>
                <td className="px-3 py-2">{r.status}</td>
                <td className="px-3 py-2">{new Date(r.created_at).toLocaleDateString()}</td>
                <td className="px-3 py-2">
                  <select
                    value={r.status}
                    onChange={(e) => updateStatus(r.id, e.target.value as ReportStatus)}
                    className="rounded border border-slate-300 px-2 py-1 text-xs"
                  >
                    <option value={r.status}>{r.status}</option>
                    {STATUSES.filter((s) => s !== r.status).map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
