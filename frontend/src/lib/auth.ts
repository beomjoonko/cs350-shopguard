/**
 * Auth helpers — post-Supabase migration.
 *
 * The public interface (getToken, clearToken, subscribeAuth,
 * getLoggedInSnapshot, getRoleSnapshot) is unchanged so all existing callers
 * (Header, api.ts, report/page, useLoggedIn) continue to work without changes.
 *
 * Token storage:
 *   Supabase persists the full session JSON in localStorage under
 *   "shopguard.supabase.session". getToken() reads that key synchronously and
 *   returns the access_token, which is sent as the Bearer header to FastAPI.
 *
 * Token refresh:
 *   @supabase/supabase-js refreshes the access_token automatically before it
 *   expires and writes the new session back to the same localStorage key.
 *   The onAuthStateChange subscription in subscribeAuth() fires on each
 *   refresh so UI components stay in sync.
 */

import { supabase } from "./supabase";

const SESSION_KEY = "shopguard.supabase.session";

/** Same-tab auth UI sync (Header, etc.) */
export const AUTH_CHANGE_EVENT = "shopguard:auth-change";

export function notifyAuthChange(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

/**
 * Get the current Supabase access token synchronously.
 * Returns null when no session is stored or on the server.
 */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const session = JSON.parse(raw) as { access_token?: string };
    return session?.access_token ?? null;
  } catch {
    return null;
  }
}

/**
 * Sign out from Supabase, clearing the session from localStorage.
 * The onAuthStateChange subscription fires after sign-out completes,
 * which in turn notifies all subscribeAuth listeners.
 */
export function clearToken(): void {
  // Fire-and-forget; onAuthStateChange will handle the rest.
  supabase.auth.signOut().then(() => notifyAuthChange());
}

/**
 * setToken is kept for backward compatibility but is now a no-op:
 * Supabase manages the session in localStorage automatically after
 * supabase.auth.signInWithPassword().
 */
export function setToken(_token: string): void {
  // Session is written by Supabase client — nothing to do here.
  notifyAuthChange();
}

/**
 * Subscribe to auth state changes.
 * Wires up both the custom shopguard:auth-change DOM event (for same-tab
 * sync from legacy code paths) and Supabase's onAuthStateChange (for login,
 * logout, and token-refresh events).
 *
 * Returns a cleanup function suitable for useEffect.
 */
export function subscribeAuth(onChange: () => void): () => void {
  if (typeof window === "undefined") return () => {};

  const run = () => onChange();
  window.addEventListener(AUTH_CHANGE_EVENT, run);
  window.addEventListener("storage", run);

  const {
    data: { subscription },
  } = supabase.auth.onAuthStateChange(() => {
    notifyAuthChange();
    onChange();
  });

  return () => {
    window.removeEventListener(AUTH_CHANGE_EVENT, run);
    window.removeEventListener("storage", run);
    subscription.unsubscribe();
  };
}

export function getLoggedInSnapshot(): boolean {
  return !!getToken();
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const [, payload] = token.split(".");
    if (!payload) return null;
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(normalized)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * getRoleSnapshot returns null after the Supabase migration.
 *
 * The `role` field in our local users table is NOT stored in the Supabase JWT
 * (the `role` claim in a Supabase JWT is always "authenticated", which is a
 * Supabase DB role, not our app role). Header.tsx now fetches role via
 * api.me() in a useEffect rather than calling this synchronously.
 */
export function getRoleSnapshot(): string | null {
  // Kept for backward compatibility — callers should migrate to async api.me()
  const token = getToken();
  if (!token) return null;
  // Try to read a custom `app_role` claim if we ever embed it via Supabase
  // custom claims / JWT hooks in the future.
  const payload = decodeJwtPayload(token);
  const appRole = payload?.app_role;
  return typeof appRole === "string" ? appRole : null;
}
