"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getToken, clearToken } from "@/lib/auth";

export default function Header() {
  const router = useRouter();
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(!!getToken());
  }, []);

  function logout() {
    clearToken();
    setLoggedIn(false);
    router.push("/");
  }

  return (
    <header className="border-b border-slate-200 bg-white shadow-sm">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 text-lg font-bold text-slate-900">
          <svg className="h-6 w-6 text-blue-600" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
          </svg>
          ShopGuard
        </Link>

        <nav className="flex items-center gap-1 text-sm font-medium">
          <Link
            href="/report"
            className="rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          >
            Report
          </Link>
          {loggedIn ? (
            <>
              <Link
                href="/my-page"
                className="rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              >
                My Page
              </Link>
              <button
                onClick={logout}
                className="rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              >
                Sign Out
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="ml-1 rounded-lg bg-slate-900 px-4 py-2 text-white hover:bg-slate-700"
            >
              Sign In
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
