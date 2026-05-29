"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearToken, notifyAuthChange } from "@/lib/auth";
import { api } from "@/lib/api";
import { useLoggedIn } from "@/hooks/useLoggedIn";

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const loggedIn = useLoggedIn();
  const [isAdmin, setIsAdmin] = useState(false);

  // Re-read token after navigation (fixes stale Sign In/My Page toggle).
  useEffect(() => {
    notifyAuthChange();
  }, [pathname]);

  // Fetch role from /users/me — the Supabase JWT no longer contains our
  // app-level role, so we load it asynchronously after login.
  useEffect(() => {
    if (loggedIn) {
      api.me()
        .then((u) => setIsAdmin(u.role === "ADMIN"))
        .catch(() => setIsAdmin(false));
    } else {
      setIsAdmin(false);
    }
  }, [loggedIn]);

  function logout() {
    clearToken();
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
          {loggedIn ? (
            <>
              <Link
                href="/report"
                className="rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              >
                Report
              </Link>
              <Link
                href="/my-page"
                className="ml-1 rounded-lg bg-slate-900 px-4 py-2 text-white hover:bg-slate-700"
              >
                My Page
              </Link>
              {isAdmin && (
                <Link
                  href="/admin"
                  className="rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                >
                  Admin
                </Link>
              )}
              <button
                type="button"
                onClick={logout}
                className="rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              >
                Sign Out
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-lg bg-slate-900 px-4 py-2 text-white hover:bg-slate-700"
            >
              Sign In
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
