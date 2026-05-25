"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { addRecentSearch, getRecentSearches } from "@/lib/recentSearches";
import type { PlatformStats } from "@/types";

const STAT_CARDS = [
  {
    key: "shops_analyzed" as const,
    icon: (
      <svg className="h-6 w-6" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
      </svg>
    ),
    label: "Shops Analyzed",
    color: "text-blue-600",
    bg: "bg-blue-50",
  },
  {
    key: "scam_sites_blocked" as const,
    icon: (
      <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
    label: "Scam Sites Blocked",
    color: "text-red-500",
    bg: "bg-red-50",
  },
  {
    key: "users_protected" as const,
    icon: (
      <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
    label: "Users Protected",
    color: "text-green-600",
    bg: "bg-green-50",
  },
];

function formatCount(n: number | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("en-US");
}

export default function HomePage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  useEffect(() => {
    function refresh() {
      setRecentSearches(getRecentSearches());
      api.getStats().then(setStats).catch(() => setStats(null));
    }
    refresh();
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, []);

  function goSearch(target: string) {
    const trimmed = target.trim();
    if (!trimmed) return;
    setRecentSearches(addRecentSearch(trimmed));
    router.push(`/search?url=${encodeURIComponent(trimmed)}`);
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    goSearch(url);
  }

  async function pasteFromClipboard() {
    try {
      const text = await navigator.clipboard.readText();
      if (text) setUrl(text);
    } catch {
      // permission denied
    }
  }

  return (
    <section className="flex flex-col items-center pt-10 text-center">
      {/* Hero */}
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-50">
        <svg className="h-9 w-9 text-blue-600" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
        </svg>
      </div>
      <h1 className="mt-4 text-4xl font-bold text-slate-900">
        Safe Shopping with{" "}
        <span className="text-blue-600">ShopGuard</span>
      </h1>
      <p className="mt-2 text-slate-500">Enter a product link to check fraud risk</p>

      <form onSubmit={onSubmit} className="mt-7 flex w-full max-w-2xl gap-2">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste product link here"
            className="w-full rounded-xl border border-slate-300 py-3 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>
        <button
          type="button"
          onClick={pasteFromClipboard}
          className="rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-600 hover:bg-slate-50"
        >
          Paste
        </button>
        <button
          type="submit"
          className="rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Search
        </button>
      </form>

      <div className="mt-10 grid w-full max-w-2xl grid-cols-3 gap-4">
        {STAT_CARDS.map((s) => (
          <div
            key={s.key}
            className="rounded-xl border border-slate-200 bg-white p-5 text-center shadow-sm"
          >
            <div className={`mx-auto flex h-10 w-10 items-center justify-center rounded-full ${s.bg} ${s.color}`}>
              {s.icon}
            </div>
            <div className="mt-2 text-2xl font-bold text-slate-900">
              {formatCount(stats?.[s.key])}
            </div>
            <div className="mt-0.5 text-xs text-slate-500">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="mt-6 w-full max-w-2xl rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm">
        <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-500">
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
            <polyline points="17 6 23 6 23 12" />
          </svg>
          Recent Searches
        </p>
        {recentSearches.length === 0 ? (
          <p className="px-3 py-4 text-sm text-slate-400">No recent searches yet. Try analyzing a URL above.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {recentSearches.map((r) => (
              <li key={r}>
                <button
                  type="button"
                  onClick={() => goSearch(r)}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-slate-600 hover:bg-slate-50"
                >
                  <svg className="h-3.5 w-3.5 shrink-0 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                  </svg>
                  <span className="truncate">{r}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
