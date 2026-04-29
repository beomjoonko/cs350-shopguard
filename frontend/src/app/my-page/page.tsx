"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Report, User } from "@/types";

export default function MyPage() {
  const [user, setUser] = useState<User | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.me(), api.myReports()])
      .then(([u, r]) => { setUser(u); setReports(r); })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!user) return <p>Loading…</p>;

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">My Page</h1>
        <p className="text-sm text-slate-600">Manage your information and reports</p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm text-slate-500">Account</p>
        <p className="font-medium">{user.email}</p>
        <p className="text-xs text-slate-500">Role: {user.role}</p>
      </div>

      <div>
        <h2 className="text-lg font-semibold">My Reports ({reports.length})</h2>
        <ul className="mt-3 space-y-3">
          {reports.length === 0 && <li className="text-sm text-slate-500">No reports yet.</li>}
          {reports.map((r) => (
            <li key={r.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">{r.status}</span>
                <span className="text-xs text-slate-500">{new Date(r.created_at).toLocaleDateString()}</span>
              </div>
              <p className="mt-1 text-sm text-slate-600">Type: {r.fraud_type}</p>
              <p className="mt-2">{r.description}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
