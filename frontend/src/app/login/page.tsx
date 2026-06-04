"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { setToken } from "@/lib/auth";

function safeNext(next: string | null): string {
  if (!next) return "/my-page";
  const t = next.trim();
  if (!t.startsWith("/") || t.startsWith("//")) return "/my-page";
  return t;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const resetSuccess = searchParams.get("reset") === "1";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.login(email, password);
      setToken(res.access_token);
      router.push(safeNext(searchParams.get("next")));
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="mx-auto mt-8 max-w-sm">
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6 flex flex-col items-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50">
            <svg className="h-7 w-7 text-blue-600" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
            </svg>
          </div>
          <h1 className="mt-3 text-xl font-bold text-slate-900">Sign in to ShopGuard</h1>
          <p className="mt-1 text-sm text-slate-500">Welcome back</p>
        </div>

        {resetSuccess && (
          <div className="mb-4 rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-800">
            Password updated. Sign in with your new password.
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="mt-1.5 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1.5 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
            <p className="mt-2 text-right">
              <Link
                href="/forgot-password"
                className="text-sm font-medium text-blue-600 hover:text-blue-700 hover:underline"
              >
                Forgot password?
              </Link>
            </p>
          </div>

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-blue-600 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:bg-slate-300"
          >
            {submitting ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-slate-500">
          No account?{" "}
          <Link href="/register" className="font-medium text-blue-600 hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </section>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="mx-auto mt-8 h-64 max-w-sm animate-pulse rounded-2xl bg-slate-200" />}>
      <LoginForm />
    </Suspense>
  );
}
